# GitHub Webhook 通知

设置环境变量 `GITHUB_NOTIFIER_WEBHOOK_PAYLOAD_URL` 为 GitHub 可访问的完整 HTTP(S) 基础地址，例如 `https://example.com/github/webhook`。机器人会在该路径下为每次新建的订阅批次生成独立 URL，形式为 `https://example.com/github/webhook/<token>`；如果使用反向代理，请转发整个路径前缀。`bot.py` 启动 FastAPI 与 WebSocket 组合驱动。

新 ORM 表需要在首次启动时创建。当前插件未提供 Alembic 迁移文件；全新数据库可设置 `ALEMBIC_STARTUP_CHECK=false`，让 nonebot-plugin-orm 同步表结构。若保留启动迁移检查，则需先为新模型生成并应用迁移。

如果数据库已经保存过旧版 `github_notifier` 的“每仓库一个 secret”订阅，旧表结构和 GitHub webhook 需要单独迁移；不能把旧 secret 自动当作新订阅凭据。迁移后，每个普通目标需按新回复配置自己的 webhook。

在 QQ 中使用：

```text
ghn subscribe owner/repo
ghn unsubscribe owner/repo
ghn list
```

群主和群管理员可管理本群订阅，任何群员可查看本群订阅；私聊时管理自己的订阅。超级管理员可在以上命令中添加可重复的 `--group 群号` 或 `--private QQ号`，指定其他目标。

订阅回复包含专属 Webhook URL 和明文 secret。请在 GitHub 仓库 Settings → Webhooks 添加 webhook，Content type 选 `application/json`，事件选择 `push`、`pull_request`、`issues`，并填写回复中的 secret。普通用户只能为自己或当前群创建单目标订阅，因此各目标使用独立 URL 和 secret；超级管理员在一条命令里指定多个目标时，这批目标共用一组 URL 和 secret。只有通过该组 secret 验签的事件才会发给这批目标。重复订阅已有目标不会重新生成或显示凭据；取消最后一个目标后，需要在 GitHub 删除对应 webhook。

Webhook 签名和 payload 解析使用 `githubkit.webhooks` 提供的 GitHubKit/Pydantic 模型；GitHubKit 会按事件类型严格校验完整 payload。
