# XMU Beamer Slides Template

**面向论文分享与组会汇报的厦门大学风格 LaTeX Beamer 模板。**
**主要用途：与Skill结合完成Agent论文解读全流程。**

本项目基于 Madrid 主题和
[yhbcode000/sustech-slides-template](https://github.com/yhbcode000/sustech-slides-template)
改造，使用厦门大学深蓝与金色配色、XMU 校徽和中文学术汇报版式。

> 当前重点只有一件事：把 arXiv 论文制作成中文讲解型 Beamer PDF。
>
> 原仓库下其他输入格式和视频发布流程尚未接入，不在当前支持范围内。

## 能力预览

| 能力 | 状态 | 说明 |
|:---|:---:|:---|
| XMU Beamer 模板 | ✅ | 可独立编辑和编译 |
| arXiv → 中文讲解 PDF | ✅ | 优先下载并读取 arXiv TeX 源码 |
| PDF → MinerU → 幻灯片 | ❌ | 尚未接入和验证 |
| PPTX / PowerPoint 输出 | ❌ | 当前只生成 LaTeX Beamer PDF |
| 配音、视频与 B 站发布 | ❌ | 尚未实现 |

这里的“arXiv → 中文讲解 PDF”不是把论文逐页转换成幻灯片，而是读取论文源码，重新组织研究背景、问题、方法、实验、结果、贡献与局限，生成适合组会讲解的中文演示文稿。

## 效果预览

完整模板预览见 [`main_template.pdf`](main_template.pdf)。

## 主题特点

- 厦门大学深蓝与金色学术配色
- 标题页默认使用 XMU 校徽
- 16:10 演示比例，适合笔记本与常见投影设备
- 支持中文、英文、公式、表格与论文插图
- 提供统一的强调、指标、图注、Callout 和章节分隔页组件
- 去除标题页推广文字

## 仓库结构

```text
.
├── main_template.tex                 # 可直接修改的示例模板
├── main_template.pdf                 # 编译后的预览 PDF
├── latexmkrc                         # XeLaTeX 与主题搜索路径配置
└── xmu-theme/
    ├── beamerthemexmu.sty            # 主主题与标题页布局
    ├── beamercolorthemexmu.sty       # XMU 配色
    ├── beamerthemexmu-elements.sty   # 排版宏与章节分隔页
    └── assets/
        └── xmu_logo.png              # 标题页校徽
```

## 在 Codex 中制作 arXiv 论文讲解 PDF

### Skill 来源与本仓库的关系

本仓库通过 `.gitmodules` 记录了原始技能仓库
[yhbcode000/paper-share-skills](https://github.com/yhbcode000/paper-share-skills)，
路径为 `skills/`。因此访问本仓库的人能够知道 Skill 的上游来源；但普通的
`git clone` 不会下载子模块，需要使用：

```bash
git clone --recurse-submodules https://github.com/lktlktlkt1/xmu-slides-template.git
```

需要特别区分：上游 `paper-share-skills` 提供的是原始 SUSTech 工作流；本项目当前使用的 XMU 版 `paper-to-beamer` 是在作者本地修改并接到本仓库的版本，尚未发布到该上游仓库。因此，**只安装上游 Skill 不能保证生成本 README 展示的 XMU 效果**。

后续建议将 XMU 版 Skill 单独发布为 `lktlktlkt1/paper-share-skills`，再把本仓库的 `skills` 子模块改为指向该 Fork。届时其他用户可以一次克隆模板与匹配的 Skill。另一种做法是直接把 Skill 放进本仓库，但会造成模板与 Skill 仓库重复维护。

### 一次性安装与加载 Skill

仅克隆本仓库会获得 XMU Beamer 模板，**不会自动安装 Codex Skill**。作者当前使用的电脑已经配置完成，无需重复安装；Codex 会在新任务中自动发现个人 Skill。

在另一台电脑上使用时，需要先把下面两个完整的 Skill 文件夹复制到个人 Skill 目录：

```text
~/.codex/skills/
├── paper-download-arxiv-paper-source/
│   ├── SKILL.md
│   └── scripts/
└── paper-to-beamer/
    ├── SKILL.md
    ├── scripts/
    └── templates/xmu/
```

同时将本仓库克隆到用户主目录，使 `paper-to-beamer` 能找到最新模板：

```bash
git clone https://github.com/lktlktlkt1/xmu-slides-template.git ~/xmu-slides-template
```

复制完成后，重新打开 Codex 或新建一个任务。Codex 会读取各 Skill 的 `SKILL.md`；无需把 Skill 内容粘贴进对话。若要明确指定流程，在提示词中写 `$paper-to-beamer` 即可。

> 当前仓库只发布模板，尚未单独发布上述 XMU 版 Skill 文件夹。因此其他电脑还需要从已配置的电脑复制这两个文件夹；待 Skill 单独发布后，这里会补充公开安装地址。

### 开始制作

在新对话中发送：

```text
使用 $paper-to-beamer，把这篇论文制作成 XMU 风格的中文组会讲解 PDF，
最终 PDF 放到桌面：
https://arxiv.org/abs/xxxx.xxxxx
```

当前流程为：

```text
arXiv 链接
    ↓
下载论文 TeX 源码
    ↓
读取正文、公式、表格与图片
    ↓
组织中文论文讲解结构
    ↓
套用 XMU Beamer 主题
    ↓
XeLaTeX 编译与版面检查
    ↓
讲解 PDF
```

### 在本地Agent工作流使用本模板

仅克隆本仓库会获得 XMU Beamer 模板，不会自动安装本地的 Codex 工作流。结合 Agent 至少需要知道以下约定：

1. 从 arXiv 下载论文 TeX 源码配合使用。
2. 使用本仓库的 `main_template.tex`、`latexmkrc` 和 `xmu-theme/`。
3. 生成文稿时使用 `\usetheme{xmu}`。
4. 使用 XeLaTeX 编译，并检查文字溢出、缺图和公式错误。

## 手动使用模板

克隆仓库：

```bash
git clone https://github.com/lktlktlkt1/xmu-slides-template.git
cd xmu-slides-template
```

复制模板并开始编辑：

```bash
cp main_template.tex main.tex
latexmk -xelatex main.tex
```

最小示例：

```latex
\documentclass[aspectratio=1610,10pt]{ctexbeamer}
\usetheme{xmu}

\title[短标题]{中文主标题}
\subtitle{English Paper Title}
\author[作者简称]{论文作者}
\institute[机构简称]{作者单位}
\setsource{会议或期刊}{年份}
\setpresenter{汇报人姓名}
\setvenue{汇报地点}
\date{YYYY-MM-DD}

\begin{document}

\begin{frame}[plain]
  \titlepage
\end{frame}

\begin{frame}{研究背景}
  \begin{itemize}
    \item 在这里填写论文背景与研究问题。
  \end{itemize}
\end{frame}

\end{document}
```

在其他目录使用时，请同时复制 `xmu-theme/` 和 `latexmkrc`，并在文档中使用：

```latex
\usetheme{xmu}
```



## 常用命令

```latex
\shl{重点}                              % 强调文字
\keyword{关键词}                        % 关键词
\hlbox{关键数字}                        % 金色高亮
\metric{95\%}{成功率}                  % 大数字指标
\fitfigure{figures/result.pdf}          % 限制宽高的论文插图
\figcap{1}{实验结果}                    % 图注
\begin{callout}[核心结论] ... \end{callout}
```

标题页校徽默认为 `xmu-theme/assets/xmu_logo.png`。需要临时替换或隐藏时：

```latex
\setlogo{my_logo}
\setlogo[0.22\paperheight]{my_logo}
\setlogo{}
```

## 编译依赖

- XeLaTeX
- `latexmk`
- TeX Live 或 MiKTeX
- `beamer`、`ctex`、`booktabs`、`colortbl`、`graphicx`、`amsmath`

编译命令：

```bash
latexmk -xelatex main.tex
```

清理中间文件：

```bash
latexmk -c
```

## 已知限制

- 当前自动化入口仅有 arXiv TeX 源码路径。
- 没有 TeX 源码的 PDF 暂未接入 MinerU。
- 自动生成的内容仍应由汇报人核对论文结论、数字、图注和引用。

## 致谢与许可

原始主题由杨昊波（Haobo Yang）开发；本仓库由李坤泰（lktlktlkt1）改造为 XMU 主题。

项目遵循 [Apache License 2.0](LICENSE)。本模板主要面向科研和学术汇报场景。
