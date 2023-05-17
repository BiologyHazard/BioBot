import json
import random
from io import BytesIO
from pathlib import Path

from PIL import ImageFont
from PIL.Image import Image as IMG
from PIL.ImageFont import FreeTypeFont
import enchant

data_dir: Path = Path(__file__).parent / "resources"
fonts_dir: Path = data_dir / "fonts"
words_dir: Path = data_dir / "words"

dict_list: list[str] = [f.stem for f in words_dir.iterdir() if f.suffix == ".json"]
dict_list.remove('legal_words')

legal_words: list[list[str]] = json.loads((words_dir / 'legal_words.json').read_text(encoding='utf-8'))
T_dict = dict[str, dict[str, str]]
dicts: dict[str, T_dict] = {}
spell = enchant.Dict('en-US')


def is_legal_word(word: str) -> bool:
    return word in legal_words[len(word)] or bool(spell.check(word))


def random_word(dic_name: str = "CET4", word_length: int = 5) -> tuple[str, dict[str, str]]:
    if dic_name not in dict_list:
        raise ValueError(f"dict name '{dic_name}' not in dic_list")
    if dic_name not in dicts:
        dicts[dic_name] = json.loads((words_dir / f"{dic_name}.json").read_text(encoding='utf-8'))

    word: str = random.choice(list(word for word in dicts[dic_name] if len(word) == word_length))
    meaning: dict[str, str] = dicts[dic_name][word]
    return word, meaning


def save_png(frame: IMG) -> BytesIO:
    output = BytesIO()
    frame = frame.convert("RGBA")
    frame.save(output, format="png")
    return output


def load_font(name: str, fontsize: int) -> FreeTypeFont:
    return ImageFont.truetype(str(fonts_dir / name), fontsize, encoding="utf-8")
