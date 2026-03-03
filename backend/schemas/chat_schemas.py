"""
Chat streaming schemas.

Type-safe Pydantic models for:
- Stream requests
- Message structure
- Session metadata
- Stream event types (for type hints)
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, Literal
from datetime import datetime


# ═══════════════════════════════════════════════════════════
# Request/Response Models
# ═══════════════════════════════════════════════════════════

class ContextData(BaseModel):
    """Optional context for the chat request."""
    elevation: Optional[float] = None
    habitat: Optional[str] = None
    timestamp: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    class Config:
        """Allow None fields."""
        extra = "allow"


class ChatStreamRequest(BaseModel):
    """
    Request to stream a chat response.
    
    Attributes:
        message: The user's message
        session_id: Unique session identifier
        context: Optional context (elevation, habitat, etc.)
    """
    message: str = Field(..., description="User message", min_length=1, max_length=2000)
    session_id: str = Field(..., description="Unique session ID", min_length=1)
    context: Optional[ContextData] = Field(default=None, description="Optional request context")

    class Config:
        """Validation settings."""
        str_strip_whitespace = True
        json_schema_extra = {
            "example": {
                "message": "What species is this?",
                "session_id": "sess_abc123",
                "context": {
                    "elevation": 1200,
                    "habitat": "forest"
                }
            }
        }


class SaveChatRequest(BaseModel):
    """
    Request to save a completed chat message.
    Only called after stream finishes successfully.
    """
    session_id: str = Field(..., description="Session ID")
    user_id: str = Field(..., description="User ID")
    user_message: str = Field(..., description="Original user message")
    assistant_response: str = Field(..., description="Complete assistant response")
    token_count: int = Field(..., description="Number of tokens in response", ge=0)
    duration_ms: int = Field(..., description="Time elapsed in milliseconds", ge=0)

    class Config:
        """Validation settings."""
        json_schema_extra = {
            "example": {
                "session_id": "sess_abc123",
                "user_id": "42",
                "user_message": "What species is this?",
                "assistant_response": "Lion is a large feline...",
                "token_count": 45,
                "duration_ms": 2340
            }
        }


# ═══════════════════════════════════════════════════════════
# Message Models
# ═══════════════════════════════════════════════════════════

class ChatMessage(BaseModel):
    """
    A single chat message.
    
    Attributes:
        session_id: Session identifier
        role: "user" or "assistant"
        content: Message text
        token_count: Number of tokens (optional)
        timestamp: ISO format datetime
    """
    session_id: str = Field(..., description="Session ID")
    role: Literal["user", "assistant"] = Field(..., description="Message role")
    content: str = Field(..., description="Message content")
    token_count: Optional[int] = Field(default=None, description="Token count")
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

    class Config:
        """Allow extra fields."""
        extra = "allow"


class ChatSession(BaseModel):
    """
    A chat session with message history.
    
    Attributes:
        session_id: Unique session identifier
        messages: List of messages in conversation
        created_at: When session was created
        updated_at: Last update timestamp
        metadata: Additional session data
    """
    session_id: str = Field(..., description="Unique session ID")
    messages: list[ChatMessage] = Field(default_factory=list, description="Messages in session")
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    metadata: Optional[Dict[str, Any]] = Field(default=None)

    class Config:
        """Allow extra fields."""
        extra = "allow"


# ═══════════════════════════════════════════════════════════
# Stream Event Models (For Type Safety)
# ═══════════════════════════════════════════════════════════

class StreamEventStart(BaseModel):
    """Start of stream marker."""
    type: Literal["start"] = "start"


class StreamEventToken(BaseModel):
    """Single token from stream."""
    type: Literal["token"] = "token"
    content: str = Field(..., description="Token content")


class StreamEventComplete(BaseModel):
    """Successful stream completion."""
    type: Literal["complete"] = "complete"


class StreamEventError(BaseModel):
    """Stream error marker."""
    type: Literal["error"] = "error"
    message: str = Field(..., description="Error message")


# Union type for type hints
StreamEvent = StreamEventStart | StreamEventToken | StreamEventComplete | StreamEventError


# ═══════════════════════════════════════════════════════════
# Response Models
# ═══════════════════════════════════════════════════════════

class SaveChatResponse(BaseModel):
    """Response from save endpoint."""
    success: bool = Field(..., description="Whether save was successful")
    message_id: Optional[str] = Field(default=None, description="ID of saved message")
    session_id: str = Field(..., description="Session ID")

    class Config:
        """Validation settings."""
        json_schema_extra = {
            "example": {
                "success": True,
                "message_id": "msg_xyz789",
                "session_id": "sess_abc123"
            }
        }


class SessionResponse(BaseModel):
    """Response with session data."""
    session: ChatSession = Field(..., description="Session data")
    message_count: int = Field(..., description="Total messages in session")


# ═══════════════════════════════════════════════════════════
# Validation/Helper Types
# ═══════════════════════════════════════════════════════════

class StreamConfig(BaseModel):
    """Configuration for stream generation."""
    max_tokens: int = Field(default=1000, description="Max tokens to generate", ge=1)
    timeout_ms: int = Field(default=30000, description="Timeout in milliseconds", ge=1000)
    token_delay_ms: tuple[float, float] = Field(
        default=(50, 150),
        description="Min/max ms delay between tokens (for simulation)"
    )

    class Config:
        """Allow extra fields."""
        extra = "allow"
