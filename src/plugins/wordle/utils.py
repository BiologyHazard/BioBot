import json
import random
from io import BytesIO
from pathlib import Path

import enchant
from PIL import ImageFont
from PIL.Image import Image as IMG
from PIL.ImageFont import FreeTypeFont

data_dir: Path = Path(__file__).parent / 'resources'
fonts_dir: Path = data_dir / 'fonts'
words_dir: Path = data_dir / 'words'

dict_list: list[str] = [f.stem for f in words_dir.iterdir() if f.suffix == '.json' and f.stem != 'legal_words']

legal_words: list[list[str]] = json.loads((words_dir / 'legal_words.json').read_text(encoding='utf-8'))
T_dict = dict[str, dict[str, str]]
dicts: dict[str, T_dict] = {}
spell = enchant.Dict('en-US')


def is_legal_word(word: str) -> bool:
    return word in legal_words[len(word)] or bool(spell.check(word))


def random_word(dict_name: str = 'CET4', word_length: int = 5) -> tuple[str, dict[str, str]]:
    if dict_name not in dict_list:
        raise ValueError(f"dict name '{dict_name}' not in dic_list")
    if dict_name not in dicts:
        dicts[dict_name] = json.loads((words_dir / f'{dict_name}.json').read_text(encoding='utf-8'))

    word: str = random.choice(list(word for word in dicts[dict_name] if len(word) == word_length))
    meaning: dict[str, str] = dicts[dict_name][word]
    return word, meaning


def save_png(frame: IMG) -> BytesIO:
    output = BytesIO()
    frame = frame.convert('RGBA')
    frame.save(output, format='png')
    return output


def load_font(name: str, fontsize: int) -> FreeTypeFont:
    return ImageFont.truetype(str(fonts_dir / name), fontsize, encoding='utf-8')
