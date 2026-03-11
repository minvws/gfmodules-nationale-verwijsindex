import base64
import json
from typing import Dict


def decode_url_safe_token(token: str) -> Dict[str, str]:
    encoded_token = token + ("=" * (4 - (len(token) % 4)))
    decoded_token = base64.urlsafe_b64decode(encoded_token)
    data: Dict[str, str] = json.loads(decoded_token)
    return data
