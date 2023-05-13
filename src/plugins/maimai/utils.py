import datetime
import hashlib
import time


def get_hash_value(id: int) -> int:
    encryptor = hashlib.sha256()
    encryptor.update(str(datetime.date.today()).encode())
    encryptor.update(str(id).encode())
    return int.from_bytes(encryptor.digest())


def strftime(event_time: int) -> str:
    return time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(event_time))
