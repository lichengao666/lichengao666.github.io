const sourceLanguage = "zh-CN";
const languageSelect = document.querySelector("#language-select");

function expireGoogleTranslateCookie(domain) {
  const domainPart = domain ? `; domain=${domain}` : "";
  document.cookie = `googtrans=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/${domainPart}`;
}

function clearGoogleTranslateCookies() {
  expireGoogleTranslateCookie();

  if (location.hostname) {
    expireGoogleTranslateCookie(location.hostname);
    expireGoogleTranslateCookie(`.${location.hostname}`);
  }
}

function getCookieLanguage() {
  const match = document.cookie.match(/(?:^|; )googtrans=\/[^/]+\/([^;]+)/);
  return match ? decodeURIComponent(match[1]) : sourceLanguage;
}

function getStoredLanguage() {
  const storedLanguage = localStorage.getItem("homepage-language");
  const availableLanguages = Array.from(languageSelect.options).map((option) => option.value);

  if (storedLanguage && availableLanguages.includes(storedLanguage)) {
    return storedLanguage;
  }

  const cookieLanguage = getCookieLanguage();
  return availableLanguages.includes(cookieLanguage) ? cookieLanguage : sourceLanguage;
}

function applyGoogleTranslation(language, retries = 30) {
  const googleCombo = document.querySelector(".goog-te-combo");

  if (!googleCombo) {
    if (retries > 0) {
      window.setTimeout(() => applyGoogleTranslation(language, retries - 1), 250);
    }

    return;
  }

  googleCombo.value = language;
  googleCombo.dispatchEvent(new Event("change"));
}

function setLanguage(language) {
  localStorage.setItem("homepage-language", language);
  languageSelect.value = language;

  if (language === sourceLanguage) {
    clearGoogleTranslateCookies();
    window.location.reload();
    return;
  }

  applyGoogleTranslation(language);
}

languageSelect.value = getStoredLanguage();
languageSelect.addEventListener("change", (event) => setLanguage(event.target.value));

window.addEventListener("load", () => {
  document.body.classList.add("translation-ready");

  if (languageSelect.value !== sourceLanguage) {
    applyGoogleTranslation(languageSelect.value);
  }
});
