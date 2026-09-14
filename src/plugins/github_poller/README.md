# GitHub Poller

通过 GitHub REST API 的资源专用端点轮询仓库变化，并向 OneBot V11 QQ 群或私聊发送合并通知。插件不会调用仓库 Activity Events API。

## 配置

```dotenv
# 可选；未配置时只能访问公开仓库，通常限制为 60 请求/小时
GITHUB_POLLER_GITHUB_TOKEN=

GITHUB_POLLER_POLL_INTERVAL=300
GITHUB_POLLER_USER_AGENT=BioBot
GITHUB_POLLER_PER_PAGE=100
GITHUB_POLLER_MAX_PAGES=10
GITHUB_POLLER_MAX_EVENTS_PER_MESSAGE=10
GITHUB_POLLER_MAX_MESSAGE_LENGTH=3500
GITHUB_POLLER_DELIVERY_MAX_ATTEMPTS=8
GITHUB_POLLER_REQUEST_TIMEOUT=30
```

GitHubKit 自行管理 HTTP 缓存和条件请求，插件不保存 ETag 等 HTTP 状态。仓库、订阅、业务游标、资源快照、事件和投递状态由 `nonebot-plugin-orm` 持久化。

## 命令

插件只注册 `ghp` 根命令，不提供别名；所有命令仅限 NoneBot 超级用户。

```text
/ghp subscribe <owner/repo|URL> [事件...] [--branch 模式...] [目标...]
/ghp unsubscribe <owner/repo> [目标...]
/ghp list [目标...]
/ghp show <owner/repo> [目标...]
/ghp event list [类别]
/ghp event add|remove|set <owner/repo> <事件...> [目标...]
/ghp branch add|remove <owner/repo> <分支模式...> [目标...]
/ghp branch reset <owner/repo> [目标...]
/ghp pause|resume <owner/repo> [目标...]
/ghp poll [owner/repo]
/ghp status
/ghp help
```

`--group` 和 `--private` 可以重复。群聊不写目标时默认当前群；私聊必须显式指定目标。

```text
/ghp subscribe owner/repo
/ghp subscribe owner/repo commit pr.merged release action.failed
/ghp subscribe owner/repo all --branch main --branch "release/*"
/ghp subscribe owner/repo default --group 114514 --group 1919810 --private 325799
```

未指定事件时使用低噪声的 `default` 预设；`all` 表示全部事件；`pr` 等大类会展开成该类别的全部原子事件。首次轮询只建立基线，不推送历史内容。
