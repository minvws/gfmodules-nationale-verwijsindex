import base64
import json


def decode_url_safe_token(token: str) -> dict[str, str]:
    encoded_token = token + ("=" * (4 - (len(token) % 4)))
    decoded_token = base64.urlsafe_b64decode(encoded_token)
    data: dict[str, str] = json.loads(decoded_token)
    return data
