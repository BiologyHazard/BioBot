import nonebot
import nonebot.plugin
from nonebot import on_command
from nonebot.adapters import Event, Message
from nonebot.matcher import Matcher
from nonebot.params import CommandArg
from nonebot.plugin import Plugin, PluginMetadata

config = nonebot.get_driver().config
default_start = list(config.command_start)[0]

__plugin_meta__ = PluginMetadata(
    name='help',
    description='BioBot 帮助菜单',
    usage=f"""欢迎使用 BioBot 帮助菜单
支持的命令前缀：{', '.join(f'"{x}"' if x else '[空]' for x in config.command_start)}

· {default_start}help  # 获取全局帮助
· {default_start}help <插件名>  # 获取特定插件的帮助
""",
    type="application",
    extra={}
)

helper = on_command("help", priority=1, aliases={"帮助", "菜单", "功能", "功能列表"})
# Matcher level info registering, still active in-use
helper.__help_name__ = 'help'
helper.__help_info__ = f'''· {default_start}help  # 获取全局帮助
· {default_start}help <插件名>  # 获取特定插件的帮助'''


def get_list_text() -> str:
    plugin_set: set[Plugin] = nonebot.plugin.get_loaded_plugins()
    lines: list[str] = []
    for plugin in plugin_set:
        parts: list[str] = []
        # plugin name
        parts.append(plugin.name)
        # PluginMetadata
        if plugin.metadata:
            # name
            if plugin.metadata.name:
                parts.append(plugin.metadata.name)
            # version
            if "version" in plugin.metadata.extra and isinstance(plugin.metadata.extra["version"], str) and plugin.metadata.extra["version"]:
                parts.append(f"版本：{plugin.metadata.extra['version']}")
            # description
            if plugin.metadata.description:
                parts.append(plugin.metadata.description)
        lines.append(f"· {" | ".join(parts)}")
    lines.sort()
    return "\n".join(lines)


@helper.handle()
async def handle_first_receive(args: Message = CommandArg()):
    arg_str = args.extract_plain_text().strip()
    if not arg_str or arg_str == "list":  # help or help list
        result = f"""欢迎使用 BioBot 帮助菜单
支持的命令前缀：{', '.join(f'"{x}"' if x else '[空]' for x in config.command_start)}

已加载的插件列表：
{get_list_text()}

全局帮助命令：
· {default_start}help  # 获取全局帮助
· {default_start}help <插件名称>  # 获取特定插件的帮助
例如：{default_start}help help  # 获取本插件帮助"""
        await helper.send(result, at_sender=True)

    else:  # help <plugin_name>
        # package name
        plugin = nonebot.plugin.get_plugin(arg_str)
        # try nickname/helpname
        if plugin is None:
            plugin_set = nonebot.plugin.get_loaded_plugins()
            for temp_plugin in plugin_set:
                if temp_plugin.metadata and temp_plugin.metadata.name == arg_str:
                    plugin = temp_plugin
        # not found
        if plugin is None:
            await helper.send(f'{arg_str} 不存在或未加载，请使用 "{default_start}help" 查看已加载的插件列表')
        else:
            lines: list[str] = []
            lines.append(plugin.name)
            lines.append("__________")
            if plugin.metadata:
                if plugin.metadata.name:
                    lines.append(f"名称：{plugin.metadata.name}")
                if plugin.metadata.description:
                    lines.append(f"描述：{plugin.metadata.description}")
                if "version" in plugin.metadata.extra and isinstance(plugin.metadata.extra["version"], str) and plugin.metadata.extra["version"]:
                    lines.append(f"版本：{plugin.metadata.extra['version']}")
                if plugin.metadata.usage:
                    lines.append("")
                    lines.append("使用方法：")
                    lines.append(plugin.metadata.usage)
            # Matcher level help, still legacy since nb2 has no Matcher metadata
            matchers = plugin.matcher
            infos = {}
            index = 1
            for matcher in matchers:
                try:
                    name = matcher.__help_name__
                except AttributeError:
                    name = None
                try:
                    help_info = matcher.__help_info__
                except AttributeError:
                    help_info = matcher.__doc__
                if name and help_info:
                    infos[f'{index}. {name}'] = help_info
                    index += 1
            if index > 1:
                lines.extend(["", "序号. 命令名: 命令用途"])
                lines.extend(
                    [f'{key}: {value}' for key, value in infos.items()
                     if key and value]
                )
            result = '\n'.join(lines)
            await helper.send(result, at_sender=True)
