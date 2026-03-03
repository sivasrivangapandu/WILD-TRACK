"""Chat streaming routes."""

import asyncio
import json
import logging
import time
from typing import AsyncGenerator, Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from database import get_db
from schemas import ChatStreamRequest, SaveChatRequest, SaveChatResponse
from services import get_model_tokens, metrics, save_chat_to_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat", tags=["chat"])


def event_to_json(event_type: str, **kwargs) -> str:
    event = {"type": event_type}
    event.update(kwargs)
    return json.dumps(event) + "\n"


async def stream_with_metrics(
    message: str,
    context: Optional[Dict[str, Any]] = None,
) -> AsyncGenerator[str, None]:
    metrics.total_requests += 1
    start_time = time.time()
    token_count = 0

    try:
        yield event_to_json("start")
        async for token in get_model_tokens(message, context):
            yield event_to_json("token", content=token)
            token_count += 1
        yield event_to_json("complete")

        elapsed_ms = (time.time() - start_time) * 1000
        metrics.record_completion(token_count, elapsed_ms)

    except asyncio.CancelledError:
        metrics.record_failure()
        raise
    except Exception as exc:
        metrics.record_failure()
        logger.error("Stream error: %s", exc)
        yield event_to_json("error", message=str(exc))


@router.post("/stream")
async def chat_stream(request: ChatStreamRequest):
    if not request.message.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Message cannot be empty",
        )
    if not request.session_id.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Session ID is required",
        )

    context_payload = request.context.model_dump() if request.context else None

    return StreamingResponse(
        stream_with_metrics(request.message, context_payload),
        media_type="text/plain",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/save")
async def save_chat(request: SaveChatRequest, db: Session = Depends(get_db)) -> SaveChatResponse:
    if not request.session_id or not request.user_message or not request.assistant_response:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing required fields",
        )

    try:
        message_id = save_chat_to_db(
            db=db,
            session_id=request.session_id,
            user_id=request.user_id,
            user_message=request.user_message,
            assistant_message=request.assistant_response,
            token_count=request.token_count,
            duration_ms=request.duration_ms,
        )
        return SaveChatResponse(
            success=True,
            message_id=message_id,
            session_id=request.session_id,
        )
    except Exception as exc:
        logger.error("Save endpoint error: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save message",
        )


@router.get("/metrics")
async def get_metrics() -> Dict[str, Any]:
    return metrics.get_summary()


@router.get("/health")
async def health_check() -> Dict[str, str]:
    return {"status": "healthy", "service": "chat-streaming"}
