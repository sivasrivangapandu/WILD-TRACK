"""Unified Gemini provider for WildTrackAI services (FIXED - Lazy loading).

Initializes Gemini once and exposes helper functions so callers do not
duplicate SDK setup logic.

CRITICAL: The google.genai SDK import hangs on some Windows systems with
application control policies. This is deferred to first use, not module load.
"""

import os
from typing import Optional


GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-2.0-flash").strip()

_client = None
_init_error = None
_gemini_initialized = False

# Print config at module import time, but defer SDK init
if GEMINI_API_KEY:
    print(f"  [OK] Gemini API key configured ({GEMINI_MODEL_NAME})")
else:
    print("  [WARN] No GEMINI_API_KEY found -- using rule-based chat")


def _ensure_gemini_loaded():
    """Lazy-load Gemini SDK only when first needed (deferred from module import)."""
    global _client, _init_error, _gemini_initialized
    
    if _gemini_initialized:
        return
    
    _gemini_initialized = True
    
    if not GEMINI_API_KEY:
        return
    
    try:
        # Import is deferred to first use to avoid Windows application control hang
        from google import genai

        _client = genai.Client(api_key=GEMINI_API_KEY)
        print(f"  [OK] Gemini client ready (lazy-loaded)")
    except Exception as exc:
        _init_error = exc
        _client = None
        print(f"  [WARN] Gemini init failed: {exc} -- falling back to local engine")


def is_gemini_available() -> bool:
    """Return whether Gemini client is ready to serve requests."""
    _ensure_gemini_loaded()
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
    _ensure_gemini_loaded()
    
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


def generate_gemini_multimodal(
    prompt: str,
    image_b64: str,
    mime_type: str = "image/jpeg",
    timeout: int = 10,
) -> Optional[str]:
    """Analyze an image using Gemini (Multimodal) with timeout.

    Args:
        prompt: Text prompt for analysis
        image_b64: Base64-encoded image string
        mime_type: MIME type of the image
        timeout: API call timeout in seconds

    Useful for OOD detection (e.g., 'Is this a footprint?').
    Returns None if API fails or times out.
    """
    _ensure_gemini_loaded()
    
    if _client is None:
        return None

    try:
        import signal

        def call_gemini():
            try:
                response = _client.models.generate_content(
                    model=GEMINI_MODEL_NAME,
                    contents=[
                        {
                            "inline_data": {
                                "data": image_b64,
                                "mime_type": mime_type
                            }
                        },
                        {
                            "text": prompt
                        }
                    ],
                    generation_config={
                        "temperature": 0.1,
                        "max_output_tokens": 10,
                    },
                )
                text = getattr(response, "text", None)
                return text.strip().upper() if isinstance(text, str) and text.strip() else None
            except Exception as e:
                print(f"  [DEBUG] Gemini API error: {e}")
                return None

        # Call Gemini with a timeout
        import threading
        result = [None]

        def target():
            result[0] = call_gemini()

        thread = threading.Thread(target=target, daemon=True)
        thread.start()
        thread.join(timeout=timeout)

        if thread.is_alive():
            print(f"  [DEBUG] Gemini call timed out after {timeout}s")
            return None

        return result[0]

    except Exception as e:
        print(f"  [DEBUG] Gemini Multimodal wrapper error: {e}")
        return None
