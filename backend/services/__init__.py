"""
Services module - Lazy imports to prevent circular dependency deadlock on Windows.
"""

# Lazy imports - do NOT import at module load time to prevent Windows import hangs
# Each service is imported on-demand by the consuming code

__all__ = [
    "get_model_tokens",
    "get_model_tokens_real",
    "ModelMetrics",
    "metrics",
    "save_chat_to_db",
    "preprocess_image",
    "detect_blur",
    "generate_quality_warning",
    "load_model",
    "predict_single",
    "upload_to_cloudinary",
    "generate_chat_response",
]


# Lazy loaders - import on first access
def __getattr__(name: str):
    """Lazy import pattern to avoid circular imports on Windows."""
    if name == "get_model_tokens":
        from .model_service import get_model_tokens
        return get_model_tokens
    elif name == "get_model_tokens_real":
        from .model_service import get_model_tokens_real
        return get_model_tokens_real
    elif name == "ModelMetrics":
        from .model_service import ModelMetrics
        return ModelMetrics
    elif name == "metrics":
        from .model_service import metrics
        return metrics
    elif name == "save_chat_to_db":
        from .chat_persistence import save_chat_to_db
        return save_chat_to_db
    elif name == "preprocess_image":
        from .image_processing import preprocess_image
        return preprocess_image
    elif name == "detect_blur":
        from .image_processing import detect_blur
        return detect_blur
    elif name == "generate_quality_warning":
        from .image_processing import generate_quality_warning
        return generate_quality_warning
    elif name == "load_model":
        from .prediction_service import load_model
        return load_model
    elif name == "predict_single":
        from .prediction_service import predict_single
        return predict_single
    elif name == "upload_to_cloudinary":
        from .prediction_service import upload_to_cloudinary
        return upload_to_cloudinary
    elif name == "generate_chat_response":
        from .chat_service import generate_chat_response
        return generate_chat_response
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
