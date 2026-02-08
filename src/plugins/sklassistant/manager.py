import json
import time
from collections.abc import Generator
from pathlib import Path
from typing import Any, Literal, Self, overload

from .config import plugin_config

file_path = plugin_config.skl_tokens_file_path


class Manager(list[dict[str, Any]]):
    default_factory = list

    @classmethod
    def load_from_file(cls, file_path: Path = file_path) -> Self:
        if not file_path.is_file():
            return cls()
        return cls(json.loads(file_path.read_text("utf-8")))

    def has_token(self, token: str) -> bool:
        return any(token == data["token"] for data in self)

    def add_item(self, qq: int, email: str, token: str, strict: bool = False) -> bool:
        if self.has_token(token):
            if strict:
                raise ValueError("Token already exists.")
            return False
        self.append(
            {
                "qq": qq,
                "email": email,
                "token": token,
                "enabled": True,
                "remind": True,
                "time": time.time(),
            }
        )
        self.save_to_file()
        return True

    # def remove_token(self, token: str, strict: bool = False) -> bool:
    #     if not self.has_token(token):
    #         if strict:
    #             raise ValueError('Token does not exist.')
    #         return False
    #     for i in range(len(self)):
    #         if self[i]['token'] == token:
    #             del self[i]
    #         break
    #     self.save_to_file()
    #     return True

    # def remove_qq(self, qq: int) -> int:
    #     count = 0
    #     for i in range(len(self)):
    #         if self[i]['qq'] == qq:
    #             del self[i]
    #             count += 1
    #     return count

    # def remove_email(self, email: str) -> int:
    #     count = 0
    #     for i in range(len(self)):
    #         if self[i]['email'] == email:
    #             del self[i]
    #             count += 1
    #     return count

    # @overload
    # def remove_user(self, *, qq: int, email: None = None) -> None: ...

    # @overload
    # def remove_user(self, *, qq: None = None, email: str) -> None: ...

    # def remove_user(self, *, qq: int | None = None, email: str | None = None) -> None:
    #     if qq is not None:
    #         self.remove_qq(qq)
    #     elif email is not None:
    #         self.remove_email(email)
    #     else:
    #         raise ValueError

    def remove_item(self, key: Literal["qq", "email", "token"], value: Any) -> int:
        count = 0
        for i in range(len(self)):
            if self[i][key] == value:
                del self[i]
                count += 1
        self.save_to_file()
        return count

    def set_enable_state(
        self, key: Literal["qq", "email", "token"], value: Any, enable=True
    ) -> int:
        count = 0
        for data in self:
            if data[key] == value:
                data["enabled"] = enable
                count += 1
        self.save_to_file()
        return count

    def set_remind_state(
        self, key: Literal["qq", "email", "token"], value: Any, remind=True
    ) -> int:
        count = 0
        for data in self:
            if data[key] == value:
                data["remind"] = remind
                count += 1
        self.save_to_file()
        return count

    def filter(
        self,
        qq: int | None = None,
        email: str | None = None,
        token: str | None = None,
        enabled: bool | None = None,
    ) -> "Manager":
        result = self.__class__()
        for data in self:
            if qq is not None and data["qq"] != qq:
                continue
            if email is not None and data["email"] != email:
                continue
            if token is not None and data["token"] != token:
                continue
            if enabled is not None and data["enabled"] != enabled:
                continue
            result.append(data)
        return result

    # def all_tokens(self) -> Generator[str, None, None]:
    #     return (data['token'] for data in self)

    # def all_enabled_tokens(self) -> Generator[str, None, None]:
    #     return (data['token'] for data in self if data['enabled'])

    def save_to_file(self, path: Path = file_path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self, ensure_ascii=False, indent=4), "utf-8")


tokens: Manager = Manager.load_from_file(file_path)
