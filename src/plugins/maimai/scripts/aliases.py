from pathlib import Path
import json
music_data_path = Path('music_data.json')
aliases_json_path = Path('data/maimai/aliases.json')
aliases_csv_path = Path('data/maimai/aliases.csv')
maimaidx_alias_path = Path('maimaidx_alias.json')

music_data = json.loads(music_data_path.read_text())
name_to_id = {music['title']: music['id'] for music in music_data}
id_to_name = {music['id']: music['title'] for music in music_data}

aliases = {}
for line in aliases_csv_path.read_text('utf-8').splitlines():
    line = line.split('\t')
    name = line[0]
    if name not in name_to_id:
        print(name)
        continue
    id = name_to_id[name]
    aliases[id] = {
        'title': name,
        'aliases': {
            alias: {
                'group': 586134350,
                'qqid': 3546587262,
                'nickname': 'BioBot〇号机',
                'card': '初始自动添加',
                'role': 'admin',
                'time': 1683294094
            } for alias in line[1:]
        }
    }

for music in json.loads(maimaidx_alias_path.read_text('utf-8')):
    name = music['Name']
    id = str(music['ID'])
    if id not in id_to_name:
        print(id, name)
        continue
    # if name != id_to_name[id]:
    #     print(id, name)
    if id not in aliases:
        print(id, name)
        aliases[id] = {
            'title': id_to_name[id],
            'aliases': {}
        }
    for alias in music['Alias']:
        if alias == name:
            continue
        aliases[id]['aliases'][alias] = {
            'group': 586134350,
            'qqid': 3546587262,
            'nickname': 'BioBot〇号机',
            'card': '初始自动添加',
            'role': 'admin',
            'time': 1683294094
        }

aliases = {key: aliases[key] for key in aliases if aliases[key]['aliases']}
aliases_json_path.write_text(json.dumps(aliases, indent=4, ensure_ascii=False), 'utf-8')
