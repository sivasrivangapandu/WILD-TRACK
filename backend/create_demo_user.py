#!/usr/bin/env python3
"""
Quick fix: Create demo user for testing on Render
"""
import sys
sys.path.insert(0, "/opt/render/project/src/backend")

from database import SessionLocal, init_db
from models.user_model import User
from auth import hash_password

# Ensure database tables exist
init_db()

db = SessionLocal()
try:
    # Check if demo user exists
    demo = db.query(User).filter(User.email == "abhishekprathipati07@gmail.com").first()
    if demo:
        print(f"✅ Demo user exists: {demo.email}")
    else:
        # Create demo user
        demo_user = User(
            id="demo-001",
            name="Demo User",
            email="abhishekprathipati07@gmail.com",
            hashed_password=hash_password("password123"),
            is_active=True,
        )
        db.add(demo_user)
        db.commit()
        print(f"✅ Demo user created: abhishekprathipati07@gmail.com / password123")
finally:
    db.close()
