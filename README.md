# 个人主页

这是一个可直接部署到 GitHub Pages 的静态个人主页模板，包含头像、姓名、邮箱、联系电话、个人经历、研究方向和项目成果等内容。

## 修改个人信息

打开 `index.html`，替换下面这些占位内容：

- `你的姓名`
- `你的学校 / 学院`
- `your.email@example.com`
- `+86 138 0000 0000`
- `中国 · 你的城市`
- 教育经历、科研经历、项目成果、研究方向

如果要换成真实头像，把图片放到 `assets` 文件夹中，例如 `assets/avatar.jpg`，然后把 `index.html` 中的 `assets/avatar.svg` 改成你的图片路径。

## 发布到 GitHub Pages

方式一：发布为个人主页，访问地址通常是：

`https://你的GitHub用户名.github.io`

1. 在 GitHub 新建仓库，仓库名必须是 `你的GitHub用户名.github.io`。
2. 把本文件夹中的所有文件上传到该仓库。
3. 进入仓库的 `Settings` -> `Pages`。
4. 在 `Build and deployment` 中选择 `Deploy from a branch`。
5. 分支选择 `main`，目录选择 `/root`，保存。

方式二：发布为普通项目主页，访问地址通常是：

`https://你的GitHub用户名.github.io/仓库名/`

1. 在 GitHub 新建任意仓库，例如 `personal-homepage`。
2. 上传本文件夹中的所有文件。
3. 进入仓库的 `Settings` -> `Pages`。
4. 分支选择 `main`，目录选择 `/root`，保存。

## 使用命令上传

如果你已经安装并登录 Git，可以在 `personal-homepage` 文件夹中运行：

```powershell
git init
git add .
git commit -m "Create personal homepage"
git branch -M main
git remote add origin https://github.com/你的GitHub用户名/你的仓库名.git
git push -u origin main
```

上传后，在 GitHub 仓库的 `Settings` -> `Pages` 开启 GitHub Pages 即可。
