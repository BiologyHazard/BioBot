from pathlib import Path
import json
music_data_path = Path('data/maimai/music_data.json')
aliases_path = Path('data/maimai/aliases.json')

music_data = json.loads(music_data_path.read_text('utf-8'))
old_aliases = json.loads(aliases_path.read_text('utf-8'))

title_to_id = {music_info['title']: music_info['id'] for music_info in music_data}

new_aliases = {}
for _, alias_dict in old_aliases.items():
    new_aliases[title_to_id[alias_dict['title']]] = alias_dict
print(new_aliases)

aliases_path.write_text(json.dumps(new_aliases, ensure_ascii=False, indent=4))
