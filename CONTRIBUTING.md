# 🤝 贡献指南 | Contributing

感谢你愿意为模板贡献。本仓库是 **XMU Beamer 主题 + 幻灯片模板** 的源仓库，也是 `paper-share-skills` 技能包的宿主（`skills/` 子模块）。

## 改动范围

| 位置 | 说明 |
|:---|:---|
| `xmu-theme/*.sty` | 主题宏、配色、标题页 / 分节页 / TOC 版式 |
| `main_template*.tex` | 各场景起手模板（论文分享 / 实验室调研 / 海报） |
| `latexmkrc` | Windows / macOS 编译路径配置 |
| `README.md` | 中文优先的双语文档（emoji 分节 + 表格 + `<details>` 面板） |
| `skills/` | 技能包为子模块，改动请提交到 [paper-share-skills](https://github.com/yhbcode000/paper-share-skills) 后回来 bump 指针 |

## 提交前检查

```bash
# 编译验证（0 error）
latexmk -xelatex main_template.tex

# 主题改动需目视检查标题页 / 分节页 / TOC 渲染（pdftoppm + 截图）
pdftoppm -png -r 100 main_template.pdf preview
```

- 新配色注册为 `\xmuscheme{<name>}`；
- 新增宏需在 README「宏与环境」表格登记；
- 保持中文优先 + 英文对照的文档风格。

## 提交流程

1. Fork 本仓库，新建分支 `feat/<your-change>`。
2. 修改并跑完检查，附渲染截图（如有视觉改动）。
3. 提交并开 Pull Request。

## 补充许可说明

论文分享 / 组会汇报等**非分发**场合（内部汇报、课堂展示、个人学习）使用本模板，免于保留许可文本与署名义务 —— 见 [LICENSE](LICENSE) 补充许可条款。
