from pathlib import Path
import json
old_music_data_path = Path('data/maimai/music_data.json.dx2022')
new_music_data_path = Path('data/maimai/music_data.json')
old_aliases_json_path = Path('data/maimai/aliases.json.dx2022')
new_aliases_json_path = Path('data/maimai/aliases.json')

old_music_data = json.loads(old_music_data_path.read_text('utf-8'))
new_music_data = json.loads(new_music_data_path.read_text('utf-8'))
old_aliases = json.loads(old_aliases_json_path.read_text('utf-8'))

id_old_to_new: dict[str, str] = {}
for old_music_dict in old_music_data:
    for new_music_dict in new_music_data:
        if old_music_dict['title'] == new_music_dict['title'] and old_music_dict['type'] == new_music_dict['type']:
            id_old_to_new[old_music_dict['id']] = new_music_dict['id']
            break
    else:
        print(old_music_dict['id'], old_music_dict['title'])

new_aliases = {}
for old_id, alias_dict in old_aliases.items():
    if old_id in id_old_to_new:
        new_aliases[id_old_to_new[old_id]] = alias_dict

new_aliases_json_path.write_text(json.dumps(new_aliases, ensure_ascii=False, indent=4))
