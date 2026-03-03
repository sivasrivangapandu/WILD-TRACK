import datetime
import time
from sqlalchemy.orm import Session

from models import ChatSession, ChatMessage


def save_chat_to_db(
    db: Session,
    session_id: str,
    user_id: str,
    user_message: str,
    assistant_message: str,
    token_count: int,
    duration_ms: int,
) -> str:
    session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if session is None:
        session = ChatSession(
            id=session_id,
            user_id=str(user_id),
            title="New Chat",
        )
        db.add(session)

    user_msg_id = f"msg_user_{int(time.time() * 1000)}"
    assistant_msg_id = f"msg_asst_{int(time.time() * 1000)}"

    db.add(
        ChatMessage(
            id=user_msg_id,
            session_id=session_id,
            role="user",
            content=user_message,
            token_count=None,
            duration_ms=None,
        )
    )

    db.add(
        ChatMessage(
            id=assistant_msg_id,
            session_id=session_id,
            role="assistant",
            content=assistant_message,
            token_count=token_count,
            duration_ms=duration_ms,
        )
    )

    if session.title in (None, "", "New Chat"):
        words = user_message.strip().split()
        session.title = " ".join(words[:5])[:30] or "New Chat"

    session.updated_at = datetime.datetime.utcnow()
    db.commit()
    return assistant_msg_id
