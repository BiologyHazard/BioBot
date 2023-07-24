from pathlib import Path
import json
charts_path = Path('data/maimai/charts')
music_data_path = Path('data/maimai/music_data.json')
music_data_path.write_text(json.dumps(json.loads(music_data_path.read_text('utf-8')), ensure_ascii=False, indent=1), 'utf-8')
title_to_path: dict[str, Path] = {}
for path in charts_path.rglob('maidata.txt'):
    if path.name == 'maidata.txt':
        first_line: str = path.read_text('utf-8').splitlines()[0]
        assert first_line.startswith('&title')
        assert (path.parent / 'track.mp3').is_file()
        if first_line[7:] in title_to_path:
            print(first_line[7:])
        title_to_path[first_line[7:]] = path.parent / 'track.mp3'

music_data = json.loads(music_data_path.read_text('utf-8'))
id_to_path: dict[str, str] = {}
for music_info in music_data:
    title: str = f'{music_info["title"]}[{music_info["type"]}]'
    if title in title_to_path:
        path: Path = title_to_path[title]
        id_to_path[music_info['id']] = path.relative_to(charts_path).as_posix()
    else:
        print(music_info['id'], music_info['title'])
id_to_path['91'] = 'maimai/131_LINK1/track.mp3'
id_to_path['253'] = 'niconicoボーカロイド/383_LINK2/track.mp3'
print(id_to_path)

audio_path_path = Path('data/maimai/audio_path.json')
audio_path_path.write_text(json.dumps(id_to_path, ensure_ascii=False, indent=4))
