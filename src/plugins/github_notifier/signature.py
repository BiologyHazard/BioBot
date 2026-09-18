from githubkit.webhooks import verify


def verify_signature(body: bytes, secret: str, signature: str | None) -> bool:
    """使用 webhook secret 校验 GitHub 的 SHA-256 HMAC 签名。"""
    if not signature or not signature.startswith("sha256="):
        return False
    return verify(secret, body, signature)
