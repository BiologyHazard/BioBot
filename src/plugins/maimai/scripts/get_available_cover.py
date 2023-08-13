from pathlib import Path
import requests
import aiohttp
import asyncio
import json


async def get(music_info):
    async with aiohttp.request('GET', f"https://www.diving-fish.com/covers/{int(music_info['id']):05d}.png") as response:
        if response.status != 200:
            print(f"{music_info['id']:<6s}{music_info['title']}")


async def main():
    data = json.loads(Path('data/maimai/music_data.json').read_text())
    tasks = []
    for music_info in data:
        tasks.append(get(music_info))
    await asyncio.gather(*tasks)


if __name__ == '__main__':
    asyncio.get_event_loop().run_until_complete(main())
