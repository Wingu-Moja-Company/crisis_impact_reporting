import os
from azure.keyvault.secrets import SecretClient
from azure.identity import DefaultAzureCredential

UN_LANGUAGES = {"ar", "zh", "en", "fr", "ru", "es"}

_secret_cache: dict[str, str] = {}


def detect_un_language(telegram_lang_code: str | None) -> str:
    """Map a Telegram language_code to the nearest UN language. Default: en."""
    if not telegram_lang_code:
        return "en"
    base = telegram_lang_code[:2].lower()
    return base if base in UN_LANGUAGES else "en"


def get_secret(name: str) -> str:
    """Fetch a secret from Azure Key Vault, with in-process caching."""
    if name in _secret_cache:
        return _secret_cache[name]

    # In local dev the secret can be set as an env var directly
    env_val = os.environ.get(name)
    if env_val:
        _secret_cache[name] = env_val
        return env_val

    vault_url = os.environ["KEY_VAULT_URL"]
    client = SecretClient(vault_url=vault_url, credential=DefaultAzureCredential())
    value = client.get_secret(name).value
    _secret_cache[name] = value
    return value
