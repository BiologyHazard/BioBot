import datetime
import time
from io import BytesIO
from random import Random
import random

from pydub import AudioSegment


def get_random_inst(qq: int) -> Random:
    return Random(str(qq) + str(datetime.date.today()))


def strftime(event_time: int) -> str:
    return time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(event_time))


def random_audio_clip(file, format='mp3', duration: float = 1.0) -> BytesIO:
    audio_file: AudioSegment = AudioSegment.from_file(file, format)
    length: float = audio_file.frame_count() / audio_file.frame_rate  # type: ignore
    start: float = random.random() * (length - duration)
    bytesio = BytesIO()
    audio_file[start * 1000: (start + duration) * 1000].export(bytesio, format)  # type: ignore
    return bytesio
