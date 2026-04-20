import os
import uuid
import urllib.request
import json


TRANSLATOR_ENDPOINT = "https://api.cognitive.microsofttranslator.com"
UN_LANGUAGES = {"ar", "zh", "en", "fr", "ru", "es"}


def detect_and_translate(text: str) -> tuple[str, str]:
    """
    Detect the language of text and translate it to English.
    Returns (detected_language_code, english_translation).
    If the text is already English, returns ("en", text) without an API call.
    """
    key = os.environ["TRANSLATOR_KEY"]
    headers = {
        "Ocp-Apim-Subscription-Key": key,
        "Ocp-Apim-Subscription-Region": os.environ.get("AZURE_LOCATION", "eastus"),
        "Content-Type": "application/json",
        "X-ClientTraceId": str(uuid.uuid4()),
    }
    body = json.dumps([{"text": text}]).encode()

    # Detect language first
    detect_url = f"{TRANSLATOR_ENDPOINT}/detect?api-version=3.0"
    req = urllib.request.Request(detect_url, data=body, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=10) as resp:
        detected = json.loads(resp.read())[0]["language"]

    if detected == "en":
        return "en", text

    # Translate to English
    translate_url = f"{TRANSLATOR_ENDPOINT}/translate?api-version=3.0&to=en"
    req = urllib.request.Request(translate_url, data=body, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=10) as resp:
        result = json.loads(resp.read())

    translation = result[0]["translations"][0]["text"]
    return detected, translation
