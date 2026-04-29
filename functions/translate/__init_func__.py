"""
Translate a short text string into the 5 non-English UN languages using the
same Azure OpenAI deployment already used for AI vision scoring.

POST /api/v1/admin/translate
Body: { "text": "How deep is the flooding?", "context": "field label" }
Response: { "fr": "...", "ar": "...", "ru": "...", "es": "...", "zh": "..." }

Requires X-API-Key header (same export key used by the dashboard).
"""

import json
import logging
import os
import urllib.request
import urllib.error

import azure.functions as func

logger = logging.getLogger(__name__)

_CORS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type, X-API-Key",
}


def _json(data: dict, status: int = 200) -> func.HttpResponse:
    return func.HttpResponse(
        json.dumps(data),
        status_code=status,
        mimetype="application/json",
        headers=_CORS,
    )


def _check_api_key(req: func.HttpRequest) -> bool:
    expected = os.environ.get("EXPORT_API_KEY", "")
    if not expected:
        return True  # dev mode
    return req.headers.get("X-API-Key", "") == expected


def _translate(text: str, context: str) -> dict:
    """Call Azure OpenAI to translate text into 5 UN languages. Returns dict."""
    endpoint = os.environ.get("AOAI_ENDPOINT", "").rstrip("/")
    key      = os.environ.get("AOAI_KEY", "")
    deploy   = os.environ.get("AOAI_DEPLOYMENT", "gpt-5.4-mini")

    if not endpoint or not key:
        raise RuntimeError("AOAI_ENDPOINT or AOAI_KEY not configured")

    prompt = (
        f'Translate the following text into French, Arabic, Russian, Spanish, and Chinese.\n'
        f'Context: this is a {context} used in a humanitarian crisis damage reporting form.\n'
        f'Keep translations short, clear, and appropriate for field workers.\n'
        f'Text to translate: "{text}"\n'
        f'Respond with JSON only, exactly this shape: '
        f'{{"fr": "...", "ar": "...", "ru": "...", "es": "...", "zh": "..."}}'
    )

    payload = json.dumps({
        "messages": [{"role": "user", "content": prompt}],
        "max_completion_tokens": 300,
        "response_format": {"type": "json_object"},
        "temperature": 0,
    }).encode()

    url = f"{endpoint}/openai/deployments/{deploy}/chat/completions?api-version=2024-10-21"
    req = urllib.request.Request(
        url, data=payload,
        headers={"api-key": key, "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        result = json.loads(resp.read())

    content = result["choices"][0]["message"]["content"]
    translations = json.loads(content)

    # Ensure all 5 keys are present
    for lang in ("fr", "ar", "ru", "es", "zh"):
        if lang not in translations:
            translations[lang] = ""

    return translations


def main(req: func.HttpRequest) -> func.HttpResponse:
    # CORS preflight
    if req.method == "OPTIONS":
        return func.HttpResponse("", status_code=204, headers=_CORS)

    if not _check_api_key(req):
        return _json({"error": "forbidden"}, 403)

    try:
        body = req.get_json()
    except ValueError:
        return _json({"error": "Invalid JSON body"}, 400)

    text    = (body.get("text") or "").strip()
    context = (body.get("context") or "form label").strip()

    if not text:
        return _json({"error": "text is required"}, 400)
    if len(text) > 500:
        return _json({"error": "text too long (max 500 chars)"}, 400)

    logger.info("Translate request: %r (context: %r)", text[:80], context)

    try:
        translations = _translate(text, context)
    except urllib.error.HTTPError as exc:
        body_err = exc.read().decode()[:200]
        logger.error("AOAI translate HTTP %s: %s", exc.code, body_err)
        return _json({"error": f"AI service error ({exc.code})", "detail": body_err}, 502)
    except Exception as exc:
        logger.error("Translate failed: %s", exc, exc_info=True)
        return _json({"error": str(exc)}, 500)

    return _json(translations)
