import datetime
import hashlib


def get_hash_value(id: int) -> int:
    encryptor = hashlib.sha256()
    encryptor.update(str(datetime.date.today()).encode())
    encryptor.update(str(id).encode())
    return int.from_bytes(encryptor.digest())
