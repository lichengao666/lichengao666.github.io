import json
import os
import re
import time
import urllib.parse
import urllib.request
from datetime import date, datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "scripts" / "paper_config.json"
OUTPUT_PATH = ROOT / "data" / "papers.json"
SERPAPI_ENDPOINT = "https://serpapi.com/search.json"


def normalize_text(value):
  return re.sub(r"\s+", " ", value or "").strip().casefold()


def compact_text(value):
  return re.sub(r"\s+", " ", value or "").strip()


def quote_query_term(term):
  return f'"{term}"' if re.search(r"\s|-", term) else term


def build_concept_query(concept):
  terms = " OR ".join(quote_query_term(term) for term in concept["terms"])
  return f"({terms})"


def normalize_for_match(value):
  return re.sub(r"[^a-z0-9]+", " ", normalize_text(value))


def build_group_query(group, concepts_by_label):
  concept_queries = [
    build_concept_query(concepts_by_label[label])
    for label in group["concepts"]
  ]
  return " ".join(concept_queries)


def scholar_request(api_key, params):
  query = urllib.parse.urlencode({
    "engine": "google_scholar",
    "api_key": api_key,
    "hl": "en",
    "as_vis": "1",
    **params
  })
  request = urllib.request.Request(f"{SERPAPI_ENDPOINT}?{query}")

  with urllib.request.urlopen(request, timeout=45) as response:
    return json.loads(response.read().decode("utf-8"))


def extract_year(result):
  summary = result.get("publication_info", {}).get("summary", "")
  match = re.search(r"\b(20\d{2}|19\d{2})\b", summary)
  return match.group(1) if match else ""


def author_names(result, limit=6):
  authors = result.get("publication_info", {}).get("authors", [])

  if authors:
    names = [compact_text(author.get("name", "")) for author in authors[:limit]]
    names = [name for name in names if name]

    if len(authors) > limit:
      names.append("et al.")

    return names

  summary = result.get("publication_info", {}).get("summary", "")
  head = summary.split(" - ")[0] if summary else ""
  return [compact_text(head)] if head else []


def result_text(result):
  text = normalize_text(" ".join([
    result.get("title", ""),
    result.get("snippet", ""),
    result.get("publication_info", {}).get("summary", "")
  ]))
  return text


def text_matches_concept(text, concept):
  normalized_text = normalize_for_match(text)
  context_terms = concept.get("context_terms", [])

  for term in concept["terms"]:
    normalized_term = normalize_for_match(term)

    if normalized_term not in normalized_text:
      continue

    if len(normalized_term) <= 3 and context_terms:
      if not any(normalize_for_match(context) in normalized_text for context in context_terms):
        continue

    return True

  return False


def result_matches_group(result, group, concepts_by_label):
  text = result_text(result)
  return all(
    text_matches_concept(text, concepts_by_label[label])
    for label in group["concepts"]
  )


def journal_names(journal):
  return [journal["name"], *journal.get("aliases", [])]


def result_matches_journal(result, journal):
  summary = normalize_text(result.get("publication_info", {}).get("summary", ""))
  normalized_summary = normalize_for_match(summary)

  return any(
    normalize_for_match(name) in normalized_summary
    for name in journal_names(journal)
  )


def find_matching_journal(result, journals):
  for journal in journals:
    if result_matches_journal(result, journal):
      return journal

  return None


def make_paper(result, journal, group):
  year = extract_year(result)
  result_id = result.get("result_id", "")
  venue_type = journal.get("venue_type", "journal")
  sci_quartile = journal.get("sci_quartile", journal["quartile"])
  cas_zone = journal.get("cas_zone") if venue_type == "preprint" else journal.get("cas_zone", "中科院待核验")

  return {
    "title": compact_text(result.get("title", "")),
    "authors": author_names(result),
    "journal": journal["name"],
    "quartile": sci_quartile,
    "sci_quartile": sci_quartile,
    "cas_zone": cas_zone,
    "cas_note": journal.get("cas_note", cas_zone),
    "rank_note": journal.get("rank_note", sci_quartile),
    "venue_type": venue_type,
    "published": f"{year}-01-01" if year else "",
    "year": year,
    "url": result.get("link", ""),
    "google_scholar_id": result_id,
    "cited_by": result.get("inline_links", {}).get("cited_by", {}).get("total"),
    "doi": "",
    "keywords": [group["label"]],
    "concepts": group["concepts"]
  }


def collect_papers(config, api_key):
  today = date.today()
  from_year = today.year - int(config["window_years"]) + 1
  to_year = today.year
  allowed_quartiles = set(config.get("allowed_quartiles", ["Q1", "Q2", "Q3"]))
  allowed_cas_zones = set(config.get("allowed_cas_zones", ["1区", "2区", "3区"]))
  include_preprints = bool(config.get("include_preprints", False))
  journals = [
    journal
    for journal in config["journals"]
    if journal.get("sci_quartile", journal.get("quartile")) in allowed_quartiles
    or journal.get("cas_zone") in allowed_cas_zones
    or (include_preprints and journal.get("venue_type") == "preprint")
  ]
  concepts_by_label = {
    concept["label"]: concept
    for concept in config["concepts"]
  }
  papers_by_key = {}

  for group in config["query_groups"]:
    scholar_query = build_group_query(group, concepts_by_label)
    params = {
      "q": scholar_query,
      "as_ylo": from_year,
      "as_yhi": to_year,
      "num": int(config["max_results_per_query"])
    }

    try:
      data = scholar_request(api_key, params)
    except Exception as exc:
      print(f"Google Scholar request failed: {group['label']} / {exc}")
      continue

    for result in data.get("organic_results", []):
      if not result.get("title"):
        continue

      if not result_matches_group(result, group, concepts_by_label):
        continue

      journal = find_matching_journal(result, journals)

      if not journal:
        continue

      key = normalize_text(result.get("result_id") or result.get("link") or result.get("title"))
      paper = papers_by_key.get(key) or make_paper(result, journal, group)
      keywords = set(paper["keywords"])
      keywords.add(group["label"])
      paper["keywords"] = sorted(keywords)
      paper["concepts"] = sorted(set(paper.get("concepts", []) + group["concepts"]))
      papers_by_key[key] = paper

    time.sleep(0.25)

  return sorted(
    papers_by_key.values(),
    key=lambda paper: paper.get("published") or "",
    reverse=True
  )


def main():
  api_key = os.getenv("SERPAPI_KEY")

  if not api_key:
    raise SystemExit(
      "Missing SERPAPI_KEY. Add it as a GitHub Actions secret to fetch Google Scholar results."
    )

  with CONFIG_PATH.open("r", encoding="utf-8") as file:
    config = json.load(file)

  papers = collect_papers(config, api_key)
  output = {
    "generated_at": datetime.now(timezone.utc).isoformat(),
    "status": "ok",
    "message": "Paper radar data generated successfully.",
    "source": "Google Scholar",
    "access_method": "SerpApi Google Scholar API",
    "window_years": config["window_years"],
    "keywords": [
      {
        "label": concept["label"],
        "abbreviation": concept.get("abbreviation", concept["label"]),
        "full_name": concept.get("full_name", concept["meaning"]),
        "meaning": concept["meaning"]
      }
      for concept in config["concepts"]
    ],
    "query_groups": [
      {
        "label": group["label"],
        "concepts": group["concepts"]
      }
      for group in config["query_groups"]
    ],
    "quartile_system": config.get("quartile_system", "SCI/JCR"),
    "quartile_systems": config.get("quartile_systems", ["SCI/JCR", "CAS"]),
    "allowed_quartiles": config.get("allowed_quartiles", ["Q1", "Q2", "Q3"]),
    "allowed_cas_zones": config.get("allowed_cas_zones", ["1区", "2区", "3区"]),
    "include_preprints": config.get("include_preprints", False),
    "journal_filter": "Curated venues include SCI/JCR Q1/Q2/Q3 journals, CAS 1/2/3-zone journals, and arXiv preprints in scripts/paper_config.json",
    "papers": papers
  }

  OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
  with OUTPUT_PATH.open("w", encoding="utf-8") as file:
    json.dump(output, file, ensure_ascii=False, indent=2)
    file.write("\n")

  print(f"Wrote {len(papers)} Google Scholar papers to {OUTPUT_PATH}")


if __name__ == "__main__":
  main()
