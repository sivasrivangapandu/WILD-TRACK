"""
Auth routes — register, login, me, profile update, password change, avatar upload.
"""
import os
import uuid
import shutil
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr, field_validator
from datetime import datetime, timezone

from database import get_db
from models.user_model import User
from auth import hash_password, verify_password, create_access_token, decode_access_token

router = APIRouter(prefix="/api/auth", tags=["auth"])

# ── Upload directory ──────────────────────────────────────────────
UPLOAD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "uploads", "avatars")
os.makedirs(UPLOAD_DIR, exist_ok=True)

ALLOWED_MIME = {"image/jpeg", "image/png", "image/webp", "image/gif"}
MAX_AVATAR_SIZE = 5 * 1024 * 1024  # 5 MB


# ── Schemas ───────────────────────────────────────────────────────
class RegisterRequest(BaseModel):
    name: str
    email: EmailStr
    password: str

    @field_validator("name")
    @classmethod
    def name_min(cls, v):
        if len(v.strip()) < 2:
            raise ValueError("Name must be at least 2 characters")
        return v.strip()

    @field_validator("password")
    @classmethod
    def password_strong(cls, v):
        if len(v) < 6:
            raise ValueError("Password must be at least 6 characters")
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UpdateProfileRequest(BaseModel):
    name: str | None = None


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def password_strong(cls, v):
        if len(v) < 6:
            raise ValueError("New password must be at least 6 characters")
        return v


class UpdateNotificationsRequest(BaseModel):
    notify_predictions: bool | None = None
    notify_updates: bool | None = None
    notify_emails: bool | None = None


# ── Helpers ───────────────────────────────────────────────────────
def _user_to_dict(u: User) -> dict:
    return {
        "id": u.id,
        "name": u.name,
        "email": u.email,
        "avatar": u.avatar_url or f"https://ui-avatars.com/api/?name={u.name}&background=f97316&color=fff",
        "role": u.role,
        "notifications": {
            "predictions": u.notify_predictions,
            "updates": u.notify_updates,
            "emails": u.notify_emails,
        },
        "created_at": u.created_at.isoformat() if u.created_at else None,
    }


def get_current_user(token: str, db: Session) -> User:
    """Validate Bearer token and return user."""
    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    user = db.query(User).filter(User.id == payload["sub"]).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account disabled")
    return user


# ── Routes ────────────────────────────────────────────────────────

@router.post("/register")
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    """Create a new account. Returns JWT token + user."""
    existing = db.query(User).filter(User.email == req.email).first()
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")

    user = User(
        id=str(uuid.uuid4()),
        name=req.name,
        email=req.email,
        hashed_password=hash_password(req.password),
        role="researcher",
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token({"sub": user.id})
    return {"token": token, "user": _user_to_dict(user)}


@router.post("/login")
def login(req: LoginRequest, db: Session = Depends(get_db)):
    """Authenticate with email + password. Returns JWT token + user."""
    user = db.query(User).filter(User.email == req.email).first()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if not verify_password(req.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account disabled")

    token = create_access_token({"sub": user.id})
    return {"token": token, "user": _user_to_dict(user)}


@router.get("/me")
def get_me(token: str = "", db: Session = Depends(get_db)):
    """Get current user from token (passed as query param ?token=...)."""
    user = get_current_user(token, db)
    return {"user": _user_to_dict(user)}


@router.put("/profile")
def update_profile(req: UpdateProfileRequest, token: str = "", db: Session = Depends(get_db)):
    """Update user name."""
    user = get_current_user(token, db)
    if req.name is not None:
        user.name = req.name.strip()
    user.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(user)
    return {"user": _user_to_dict(user)}


@router.put("/password")
def change_password(req: ChangePasswordRequest, token: str = "", db: Session = Depends(get_db)):
    """Change password. Requires current password."""
    user = get_current_user(token, db)
    if not verify_password(req.current_password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    user.hashed_password = hash_password(req.new_password)
    user.updated_at = datetime.now(timezone.utc)
    db.commit()
    return {"message": "Password updated"}


@router.post("/avatar")
async def upload_avatar(
    token: str = "",
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """Upload profile picture. Max 5 MB, image types only."""
    user = get_current_user(token, db)

    # Validate MIME
    if file.content_type not in ALLOWED_MIME:
        raise HTTPException(status_code=400, detail=f"Invalid image type: {file.content_type}. Allowed: JPEG, PNG, WebP, GIF")

    # Read + check size
    contents = await file.read()
    if len(contents) > MAX_AVATAR_SIZE:
        raise HTTPException(status_code=400, detail="Image must be under 5 MB")

    # Save file
    ext = file.filename.split(".")[-1] if "." in file.filename else "png"
    filename = f"{user.id}.{ext}"
    filepath = os.path.join(UPLOAD_DIR, filename)
    with open(filepath, "wb") as f:
        f.write(contents)

    # Update user record
    user.avatar_url = f"/uploads/avatars/{filename}"
    user.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(user)
    return {"user": _user_to_dict(user)}


@router.put("/notifications")
def update_notifications(req: UpdateNotificationsRequest, token: str = "", db: Session = Depends(get_db)):
    """Update notification preferences."""
    user = get_current_user(token, db)
    if req.notify_predictions is not None:
        user.notify_predictions = req.notify_predictions
    if req.notify_updates is not None:
        user.notify_updates = req.notify_updates
    if req.notify_emails is not None:
        user.notify_emails = req.notify_emails
    user.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(user)
    return {"user": _user_to_dict(user)}


@router.delete("/account")
def delete_account(token: str = "", db: Session = Depends(get_db)):
    """Permanently delete user account."""
    user = get_current_user(token, db)
    db.delete(user)
    db.commit()
    return {"message": "Account deleted"}
