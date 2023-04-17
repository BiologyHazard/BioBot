import datetime
import hashlib


def get_hash_value(id: int) -> int:
    encryptor = hashlib.sha256(usedforsecurity=False)
    encryptor.update(str(datetime.date.today()).encode())
    encryptor.update(bytes(id))
    return int.from_bytes(encryptor.digest())
