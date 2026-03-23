"""Unified Gemini provider for WildTrackAI services.

Initializes Gemini once and exposes helper functions so callers do not
duplicate SDK setup logic.
"""

import os
from typing import Optional


GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-2.0-flash").strip()

_client = None
_init_error = None


if GEMINI_API_KEY:
    try:
        from google import genai

        _client = genai.Client(api_key=GEMINI_API_KEY)
        print(f"  [OK] Gemini AI initialized ({GEMINI_MODEL_NAME})")
    except Exception as exc:
        _init_error = exc
        _client = None
        print(f"  [WARN] Gemini init failed: {exc} -- falling back to local engine")
else:
    print("  [WARN] No GEMINI_API_KEY found -- using rule-based chat")


def is_gemini_available() -> bool:
    """Return whether Gemini client is ready to serve requests."""
    return _client is not None


def get_init_error() -> Optional[Exception]:
    """Expose init error for diagnostics if needed."""
    return _init_error


def generate_gemini_text(
    prompt: str,
    system_prompt: Optional[str] = None,
    temperature: float = 0.5,
    max_output_tokens: int = 800,
) -> Optional[str]:
    """Generate text with Gemini and return stripped response text.

    Returns None if Gemini is unavailable or response cannot be parsed.
    """
    if _client is None:
        return None

    full_prompt = prompt if not system_prompt else f"System instructions:\n{system_prompt}\n\nUser request:\n{prompt}"

    try:
        response = _client.models.generate_content(
            model=GEMINI_MODEL_NAME,
            contents=full_prompt,
            config={
                "temperature": float(temperature),
                "max_output_tokens": int(max_output_tokens),
            },
        )
        text = getattr(response, "text", None)
        return text.strip() if isinstance(text, str) and text.strip() else None
    except Exception:
        return None
