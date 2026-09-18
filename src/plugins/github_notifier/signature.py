from githubkit.webhooks import verify


def verify_signature(body: bytes, secret: str, signature: str | None) -> bool:
    if not signature or not signature.startswith("sha256="):
        return False
    return verify(secret, body, signature)
