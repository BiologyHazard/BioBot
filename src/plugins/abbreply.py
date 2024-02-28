import aiohttp
from nonebot.plugin import PluginMetadata, on_command
from nonebot.params import CommandArg
from nonebot.adapters import Message

__plugin_meta__ = PluginMetadata(
    name='缩写查询器',
    description='输入拼音首字母，猜测文字',
    usage=(
        "NoneBot 短句回复 查看插件"
    ),
    extra={
        'menu_template': 'default',
        'menu_data': [
            {
                'func': '缩写查询器',
                'trigger_method': 'on_cmd',
                'trigger_condition': 'sx lsp',
                'brief_des': '查缩写',
                'detail_des': '查缩写'
            },
            {
                'func': '缩写查询器',
                'trigger_method': 'on_cmd',
                'trigger_condition': '缩写 lsp',
                'brief_des': '查缩写',
                'detail_des': '查缩写'
            },
        ],
    }
)


async def get_sx(word: str):
    url = "https://lab.magiconch.com/api/nbnhhsh/guess"

    headers = {
        'origin': 'https://lab.magiconch.com',
        'referer': 'https://lab.magiconch.com/nbnhhsh/',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.163 Safari/537.36',
    }
    data = {
        "text": word
    }
    async with aiohttp.request('POST', url, headers=headers, data=data) as response:
        msg = await response.json()
    return msg


sx = on_command('缩写', aliases={'sx'}, priority=5, block=False)


@sx.handle()
async def sx_func(message: Message = CommandArg()):
    data = await get_sx(message.extract_plain_text())
    result = ""
    try:
        data = data[0]
        name = data['name']
        try:
            content = data['trans']
            result += '、'.join(content)
        except KeyError:
            pass
        try:
            inputs = data['inputting']
            result += '、'.join(inputs)
        except KeyError:
            pass
    except Exception as e:
        await sx.finish(message=f"出错啦")

    if result:
        await sx.finish(message=name + "可能解释为：\n" + result)
    await sx.finish(message=f"没有找到缩写 {message} 的可能释义")
