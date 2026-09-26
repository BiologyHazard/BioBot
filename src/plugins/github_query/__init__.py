"""Read-only GitHub repository queries."""

from nonebot.plugin import PluginMetadata

from . import commands as commands
from .config import Config

USAGE = """查询 GitHub 仓库中未关闭的 PR 和 Issue：
/gh list <owner/repo|URL> [--limit N]
/gh pr list <owner/repo|URL> [--limit N]
/gh issue list <owner/repo|URL> [--limit N]"""

__plugin_meta__ = PluginMetadata(
    name="GitHub 仓库查询",
    description="查询仓库中未关闭的 PR 和 Issue",
    usage=USAGE,
    type="application",
    config=Config,
)
