import os
import secrets

def settings():
    production = os.environ.get("AGLUREP_ENV", "development").lower() == "production"
    secret = os.environ.get("AGLUREP_SECRET_KEY")
    if production and (not secret or len(secret.strip()) < 32):
        raise RuntimeError("En produccion, defina AGLUREP_SECRET_KEY con al menos 32 caracteres.")
    return {"SECRET_KEY": secret or secrets.token_hex(32),
            "BEHIND_PROXY": os.environ.get("AGLUREP_BEHIND_PROXY") == "1",
            "MAX_CONTENT_LENGTH": 2 * 1024 * 1024, "JSON_SORT_KEYS": False}
