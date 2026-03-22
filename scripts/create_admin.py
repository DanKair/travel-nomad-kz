"""
Utility script to create an initial admin user.
"""

import asyncio
import getpass
import hashlib
from sqlalchemy.future import select
from passlib.context import CryptContext

import sys
from pathlib import Path

# Add parent directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.database import SessionLocal
from app.models import AdminUser

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

async def create_admin():
    username = input("Enter admin username: ")
    password = getpass.getpass("Enter admin password: ")
    confirm_password = getpass.getpass("Confirm password: ")

    if password != confirm_password:
        print("❌ Passwords do not match!")
        return

    # Pre-hash with SHA-256 to support passwords > 72 chars
    pwd_prehash = hashlib.sha256(password.encode()).hexdigest()
    hashed_password = pwd_context.hash(pwd_prehash)

    async with SessionLocal() as db:
        # Check if username exists
        result = await db.execute(select(AdminUser).filter(AdminUser.username == username))
        existing_user = result.scalars().first()
        
        if existing_user:
            print(f"❌ User '{username}' already exists.")
            return

        new_user = AdminUser(
            username=username,
            hashed_password=hashed_password
        )
        db.add(new_user)
        await db.commit()
        print(f"✅ Admin user '{username}' created successfully!")

if __name__ == "__main__":
    asyncio.run(create_admin())
