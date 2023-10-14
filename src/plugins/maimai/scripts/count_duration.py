from pydub import AudioSegment
from pydub.utils import mediainfo
from pathlib import Path
import os
import json


def get_duration(file, format='mp3') -> float:
    # audio_file: AudioSegment = AudioSegment.from_file(file, format)
    # return audio_file.frame_count() / audio_file.frame_rate  # type: ignore
    return float(mediainfo(file)['duration'])


if __name__ == '__main__':
    track_path_path = Path('data/maimai/track_path.json')
    track_path = json.loads(track_path_path.read_text('utf-8'))
    music_data_path = Path('data/maimai/music_data.json')
    music_data = json.loads(music_data_path.read_text('utf-8'))
    chart_path = Path('data/maimai/charts')
    output_path = Path('data/maimai/music_durations.txt')
    with open(output_path, 'w', encoding='utf-8') as fp:
        for music_info in music_data:
            music_id = music_info['id']
            if music_id not in track_path:
                continue
            mp3_path = track_path[music_id]
            print(music_id, music_info['title'], music_info['type'], get_duration(chart_path / mp3_path), sep='\t', file=fp)
