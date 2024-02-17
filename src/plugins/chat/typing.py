from typing import Any, Literal, TypedDict


class TextPart(TypedDict):
    role: Literal['system', 'user', 'assistant']
    content: str


Text = list[TextPart]


class Result(TypedDict):
    code: int
    message: str
    data: dict[str, Any]
