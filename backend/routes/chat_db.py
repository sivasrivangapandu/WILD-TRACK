"""Database CRUD operations for chat sessions."""

import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from database import get_db
from models import ChatSession, ChatMessage


# Pydantic schemas for request/response validation
class MessageCreate(BaseModel):
    """Schema for creating a new message."""
    id: str
    role: str  # "user" | "assistant"
    content: str
    token_count: Optional[int] = None
    duration_ms: Optional[int] = None


class MessageResponse(BaseModel):
    """Schema for message response."""
    id: str
    session_id: str
    role: str
    content: str
    token_count: Optional[int]
    duration_ms: Optional[int]
    created_at: datetime.datetime
    
    class Config:
        from_attributes = True  # Replaces orm_mode in Pydantic v2


class SessionCreate(BaseModel):
    """Schema for creating a new session."""
    id: str
    user_id: str  # MVP: trusted from client
    title: Optional[str] = "New Chat"


class SessionResponse(BaseModel):
    """Schema for session response without messages."""
    id: str
    user_id: str
    title: Optional[str]
    created_at: datetime.datetime
    updated_at: datetime.datetime
    message_count: int  # Computed field
    
    class Config:
        from_attributes = True


class SessionWithMessagesResponse(BaseModel):
    """Schema for session with full message history."""
    id: str
    user_id: str
    title: Optional[str]
    created_at: datetime.datetime
    updated_at: datetime.datetime
    messages: List[MessageResponse]
    
    class Config:
        from_attributes = True


# Router instance
router = APIRouter(prefix="/api/chat", tags=["chat-database"])


@router.post("/sessions", response_model=SessionResponse)
def create_session(session_data: SessionCreate, db: Session = Depends(get_db)):
    """
    Create a new chat session.
    
    MVP: user_id is trusted from client (no JWT verification yet).
    """
    # Check if session already exists
    existing = db.query(ChatSession).filter(ChatSession.id == session_data.id).first()
    if existing:
        raise HTTPException(status_code=400, detail="Session ID already exists")
    
    new_session = ChatSession(
        id=session_data.id,
        user_id=session_data.user_id,
        title=session_data.title
    )
    
    db.add(new_session)
    db.commit()
    db.refresh(new_session)
    
    return SessionResponse(
        id=new_session.id,
        user_id=new_session.user_id,
        title=new_session.title,
        created_at=new_session.created_at,
        updated_at=new_session.updated_at,
        message_count=0
    )


@router.get("/sessions", response_model=List[SessionResponse])
def list_sessions(user_id: str, db: Session = Depends(get_db)):
    """
    List all sessions for a user.
    
    MVP: user_id from query param (trusted from client).
    TODO: Extract from JWT token after auth implementation.
    """
    # Query sessions with message count
    sessions = db.query(
        ChatSession,
        func.count(ChatMessage.id).label('message_count')
    ).outerjoin(ChatMessage).filter(
        ChatSession.user_id == user_id
    ).group_by(ChatSession.id).order_by(
        ChatSession.updated_at.desc()
    ).all()
    
    return [
        SessionResponse(
            id=session.id,
            user_id=session.user_id,
            title=session.title,
            created_at=session.created_at,
            updated_at=session.updated_at,
            message_count=count
        )
        for session, count in sessions
    ]


@router.get("/sessions/{session_id}", response_model=SessionWithMessagesResponse)
def get_session(session_id: str, db: Session = Depends(get_db)):
    """
    Get a session with all messages.
    
    Returns 404 if session not found.
    """
    session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return session


@router.post("/sessions/{session_id}/messages", response_model=MessageResponse)
def add_message(session_id: str, message_data: MessageCreate, db: Session = Depends(get_db)):
    """
    Add a message to an existing session.
    
    Also updates session's updated_at timestamp.
    """
    # Verify session exists
    session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Check if message already exists
    existing = db.query(ChatMessage).filter(ChatMessage.id == message_data.id).first()
    if existing:
        raise HTTPException(status_code=400, detail="Message ID already exists")
    
    new_message = ChatMessage(
        id=message_data.id,
        session_id=session_id,
        role=message_data.role,
        content=message_data.content,
        token_count=message_data.token_count,
        duration_ms=message_data.duration_ms
    )
    
    db.add(new_message)
    
    # Update session timestamp
    session.updated_at = datetime.datetime.utcnow()
    
    db.commit()
    db.refresh(new_message)
    
    return new_message


@router.delete("/sessions/{session_id}")
def delete_session(session_id: str, db: Session = Depends(get_db)):
    """
    Delete a session and all its messages (cascade).
    
    Returns 404 if session not found.
    """
    session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    db.delete(session)
    db.commit()
    
    return {"message": "Session deleted", "session_id": session_id}


