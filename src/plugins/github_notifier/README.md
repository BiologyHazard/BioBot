# GitHub Webhook 通知

订阅 GitHub 仓库后，机器人通过 Webhook 接收事件，并将通知发送到 QQ 群或私聊。每条订阅关联一个仓库和一个 QQ 目标；同一仓库的通知会按时间窗汇总，以合并转发消息发送。

## 部署

为机器人配置以下环境变量：

| 变量 | 说明 |
| --- | --- |
| `GITHUB_NOTIFIER_WEBHOOK_PAYLOAD_URL` | 必填。GitHub 可访问的 HTTP(S) 基础地址，例如 `https://example.com/github/webhook`。地址不能包含查询参数或片段。 |
| `GITHUB_NOTIFIER_BATCH_WINDOW_SECONDS` | 汇总时间窗，单位为秒，必须大于 0；默认 60。 |
| `GITHUB_NOTIFIER_FILTER_CONFIG` | 可选。过滤配置 TOML 文件的路径；相对路径从机器人工作目录解析。修改文件后需重启机器人。 |

插件会在基础地址后追加订阅专属的 token，例如 `https://example.com/github/webhook/<token>`。如果使用反向代理，需要将包含 token 的完整路径转发给机器人。项目的 `bot.py` 已加载本插件；运行时需使用支持 ASGI 的 FastAPI 驱动器，以接收 GitHub 的 HTTP 请求。

订阅和投递记录保存在 `nonebot-plugin-orm` 数据库中。首次使用时，请通过项目的 Alembic 流程创建并应用对应表，或在全新数据库上设置 `ALEMBIC_STARTUP_CHECK=false`，由 ORM 在启动时同步表结构。沿用旧版“每仓库一个 secret”数据的部署，需要先迁移数据库和 GitHub Webhook，再建立当前的目标订阅。

机器人连接的 OneBot 实现需要支持群聊和私聊的合并转发 API。

## 订阅仓库

在 QQ 中发送：

```text
ghn subscribe owner/repo
ghn list
ghn unsubscribe owner/repo
```

群聊中的 `subscribe` 和 `unsubscribe` 由群主、群管理员或机器人超级管理员执行；群成员均可使用 `list`。私聊命令管理发送者自己的订阅。超级管理员可以用可重复的 `--group 群号` 和 `--private QQ号` 指定目标，例如：

```text
ghn subscribe owner/repo --group 123456 --private 654321
ghn list --group 123456
```

`subscribe` 为新增目标生成一组 Payload URL 和 secret，并回复 GitHub 仓库的 Webhook 创建页面。打开页面后，按回复填写：

1. **Payload URL**：使用回复中的完整地址，包含末尾 token。
2. **Content type**：选择 `application/json`。
3. **Secret**：填写回复中的 secret。
4. **Events**：选择机器人回复中列出的事件类型，然后创建 Webhook。

一次命令指定多个新目标时，这些目标共用该次生成的 Webhook。已订阅的目标不会重复创建订阅。取消订阅后，如果命令回复列出了待删除的 Webhook URL，还需在 GitHub 仓库设置中删除对应 Webhook。

## 通知范围与过滤配置

版本化默认规则见 `default_filters.toml`。默认推送 Issue 和 PR 的开启、关闭、重新开启，已合并 PR、失败的 GitHub Actions 工作流、新增 Star，以及全部 Release 动作。工作流只有 `completed` 且 `conclusion=failure` 才归为 `workflow_run.failure`；取消和超时可分别配置。关闭且已合并的 PR 归为 `pull_request.merged`，未合并的关闭归为 `pull_request.closed`。

通过 `GITHUB_NOTIFIER_FILTER_CONFIG` 指定自己的 TOML 文件。`[default]` 可整体替换版本化默认规则；每个 `[repositories."owner/repo"]` 又可整体替换该仓库的有效规则。省略的部分沿用默认规则，`events = []` 表示该仓库不推送。示例：

```toml
[repositories."bio/project"]
events = ["issues.opened", "pull_request.merged", "star.created", "release"]
```

事件名可写 GitHub 的 Webhook 类型（如 `release`，匹配该类型的全部动作），或 `类型.动作`（如 `issues.opened`）。动作名按 GitHub Webhook schema 校验。`pull_request.merged` 和 `workflow_run.<结果>` 是 BioBot 从 GitHub payload 字段派生的过滤分类。无效事件名会在启动时报错。QQ 命令只管理订阅，过滤规则由配置文件管理。

GitHub Webhook 必须勾选有效规则所需的原始事件类型。新订阅的命令回复会列出这些类型；已有 Webhook 若此前未勾选 `star` 或其他新增类型，需要在 GitHub 仓库设置中手动更新。过滤文件只决定已收到的事件是否发送到 QQ。推送消息包含事件摘要和相关链接；包含多个提交的 Push 最多展示前 8 条提交。

## 发送方式

同一仓库收到第一条待推送事件时开始计时。时间窗结束后，机器人按订阅目标分别发送一条合并转发消息；时间窗内只有一个事件时，仍发送单节点合并转发。不同仓库分别计时。

插件按 Webhook 投递 ID 和订阅目标记录已成功发送的消息，避免重复投递产生重复通知。发送失败的投递不会记为已送达。
