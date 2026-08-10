# 🔒 安全策略 | Security Policy

## 报告漏洞 | Reporting a Vulnerability

发现安全漏洞（恶意 LaTeX 宏、脚本注入、供应链问题等）请**不要公开提交 issue**，直接：

- 私信 GitHub：[Security Advisories](https://github.com/yhbcode000/sustech-slides-template/security/advisories/new)（推荐，仅维护者可见）
- 或邮件：yhbcode000@foxmail.com

请附上：复现步骤、受影响版本（commit / tag）、影响范围描述。

## 处理承诺 | What to Expect

- 24 小时内确认收悉；
- 确认有效后优先修复，修复完成前不公开披露；
- 修复后发布 release 并在 Security Advisory 中致谢报告者（如同意署名）。

## 安全注意 | Operational Notes

- 编译他人提供的 `.tex` / `.sty` 前请审阅内容 —— LaTeX 宏可在编译期执行任意命令；
- `skills/` 子模块来自 [paper-share-skills](https://github.com/yhbcode000/paper-share-skills)，其安全问题请按其 SECURITY.md 报告。
