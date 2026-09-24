# GitHub 仓库查询

通过 GitHub REST API 查询仓库中未关闭的 PR 和 Issue。插件只执行读取请求，
不修改 GitHub 数据，也不保存查询结果。

## 命令

```text
/gh list owner/repo
/gh pr list owner/repo
/gh issue list owner/repo
/gh list https://github.com/owner/repo --limit 20
```

`gh list` 同时查询 PR 和 Issue。结果按最近更新时间倒序排列。普通用户可以查询
公开仓库；私有仓库仅限机器人超级用户查询，并且需要 Token 拥有访问权限。

## 配置

```dotenv
# 可选。未配置时仍可查询公开仓库，但 GitHub 的请求配额较低。
GITHUB_QUERY_GITHUB_TOKEN=

GITHUB_QUERY_DEFAULT_LIMIT=10
GITHUB_QUERY_MAX_LIMIT=30
GITHUB_QUERY_MAX_PAGES=10
GITHUB_QUERY_REQUEST_TIMEOUT=15
```
