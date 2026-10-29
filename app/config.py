import os
import secrets

def settings():
    return {"SECRET_KEY": os.environ.get("AGLUREP_SECRET_KEY") or secrets.token_hex(32),
            "MAX_CONTENT_LENGTH": 2 * 1024 * 1024, "JSON_SORT_KEYS": False}
