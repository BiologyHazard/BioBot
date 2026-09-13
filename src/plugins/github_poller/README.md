# GitHub 轮询通知

这是一个独立于 `github_notifier` 的 NoneBot2 插件。它通过 `githubkit` 调用 GitHub REST API 定时轮询仓库，发送纯文本通知，不使用 Webhook、HTML 渲染或图片生成。

## 加载

插件已经在项目的 `bot.py` 中加载。也可以单独加载：

```python
nonebot.load_plugin("src.plugins.github_poller")
```

## 配置

```dotenv
# 私有仓库或提高公开仓库 API 额度时填写
GITHUB_TOKEN=

# 轮询间隔，最小 30 秒，默认 300 秒
GITHUB_POLL_INTERVAL=300

# 数据文件和每个接口的查询数量
GITHUB_POLLER_DATA_PATH=data/github_poller/data.json
GITHUB_POLLER_PER_PAGE=30
```

数据文件与原 `data/github_notifier/data.json` 完全分离。首次添加或首次启动时只建立当前状态基线，不发送已有历史动态。

## 动态类型

默认监控：

- commit
- issue（会排除 GitHub API `/issues` 返回的 PR）
- pull request
- release
- issue/PR comment

## 指令

```text
/repo.add owner/repo [group_id]
/repo.delete owner/repo
/repo.show
/repo.refresh
/check_api_usage
```

仓库配置和状态保存在 `data/github_poller/data.json`。配置仓库需要群管理员或超级用户权限；`/repo.info` 等完整配置指令后续可以继续扩展。

## 设计限制

- 轮询不是实时推送，通知延迟取决于轮询间隔。
- 每次轮询会调用 GitHub REST API，需要注意 API 限流。
- 目前只发送纯文本，不依赖 `nonebot-plugin-htmlrender` 和 Pillow。
- 为避免刷屏，每个仓库首次同步不会发送历史事件。
