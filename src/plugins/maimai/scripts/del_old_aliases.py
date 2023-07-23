from pathlib import Path
import json
music_data_path = Path('data/maimai/music_data.json')
aliases_json_path = Path('data/maimai/aliases.json')
aliases_from_api_path = Path('data/maimai/aliases_from_yuzuai_api.json')
music_data = json.loads(music_data_path.read_text())
aliases = json.loads(aliases_json_path.read_text())
aliases_from_api = json.loads(aliases_from_api_path.read_text())
for music_id, aliases_dict in aliases.items():
    aliases_dict['aliases'] = {
        alias: alias_info
        for alias, alias_info in aliases_dict['aliases'].items()
        if alias_info != {
            "group": 586134350,
            "qqid": 3546587262,
            "nickname": "BioBot〇号机",
            "card": "初始自动添加",
            "role": "admin",
            "time": 1683294094}
        and alias not in aliases_from_api[music_id]['Alias']
    }
aliases = {music_id: aliases_dict for music_id, aliases_dict in aliases.items() if aliases_dict['aliases']}
aliases_json_path.write_text(json.dumps(aliases, indent=4, ensure_ascii=False))
