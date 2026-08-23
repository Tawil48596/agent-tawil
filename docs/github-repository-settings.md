# GitHub 仓库治理核验清单

本文件记录无法由本地代码变更完成的仓库管理员设置。执行前先确认目标仓库为
`Tawil48596/agent-tawil`，再在 GitHub 仓库设置中逐项启用。

## `main` 分支规则

- 要求通过 Pull Request 合并，至少一名审批者。
- 要求分支在合并前保持最新。
- 将 `Python 3.11`、`Python 3.12`、`Frontend quality`、`Browser smoke`、
  `Dependency review` 和两个 CodeQL 作业设为必需检查。
- 禁止绕过规则和强制推送，限制删除 `main`。

## 安全设置

- 在 Code security and analysis 中启用 Secret scanning 与 Push protection。
- 启用 Dependabot alerts、security updates 和 grouped security updates。
- 验证 `.github/dependabot.yml` 能为 uv、npm 和 GitHub Actions 创建更新请求。
- 验证 Actions 页面中的工作流仅使用提交 SHA 固定的第三方动作。

## 完成证据

完成后在发布说明中记录核验日期、操作者和规则集链接；不要记录令牌、密钥或仓库
Secret 的值。远端设置未经人工核验前，不应在路线图中标记为完成。
