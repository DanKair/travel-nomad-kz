import logging
import secrets
import hashlib
from sqladmin.authentication import AuthenticationBackend
from fastapi import Request
from app.core.config import settings
from app.models import AdminUser
from sqlalchemy.future import select
from passlib.context import CryptContext
from app.redis import get_redis_client
from app.core.auth import is_admin_ip
from app.core.database import SessionLocal
from redis import exceptions as redis_exceptions

logger = logging.getLogger(__name__)

# Hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class AdminAuth(AuthenticationBackend):
    async def login(self, request: Request) -> bool:
        """
        Handles admin login with multiple security layers.
        """
        logger.info("Admin login attempt started")
        
        # 1. IP Allowlisting
        if not is_admin_ip(request):
            logger.warning("Admin login REJECTED: IP not in allowlist")
            return False
            
        try:
            form = await request.form()
        except Exception as e:
            logger.error(f"Error parsing login form: {str(e)}")
            return False
            
        username, password = form.get("username"), form.get("password")
        
        if not username or not password:
            logger.warning("Admin login REJECTED: Missing username or password")
            return False

        logger.info(f"Attempting login for user: {username}")

        # 2. Brute-force protection via Redis
        redis = get_redis_client()
        client_ip = request.headers.get("X-Forwarded-For", request.client.host).split(",")[0].strip()
        attempts_key = f"admin_login_attempts:{client_ip}"
        
        try:
            # Check if already blocked (3 attempts within 2 mins)
            attempts = await redis.get(attempts_key)
            if attempts and int(attempts) >= 5: # Increased to 5 for dev
                logger.warning(f"Admin login BLOCKED: Too many attempts for IP {client_ip}")
                return False
        except (redis_exceptions.ConnectionError, redis_exceptions.TimeoutError):
            logger.warning("Redis is unavailable. Brute-force protection disabled.")
            
        # 3. Database Check
        async with SessionLocal() as db:
            # Pre-hash with SHA-256 to support passwords > 72 chars
            pwd_prehash = hashlib.sha256(password.encode()).hexdigest()
            
            result = await db.execute(select(AdminUser).filter(AdminUser.username == username))
            user = result.scalars().first()
            
            if not user:
                logger.warning(f"Admin login FAILED: User '{username}' not found")
                return False
                
            try:
                if not pwd_context.verify(pwd_prehash, user.hashed_password):
                    logger.warning(f"Admin login FAILED: Incorrect password for '{username}'")
                    # Increment failed attempts in Redis
                    try:
                        await redis.incr(attempts_key)
                        await redis.expire(attempts_key, 120)
                    except:
                        pass
                    return False
            except Exception as e:
                logger.error(f"Error during password verification for '{username}': {str(e)}")
                return False
                
        # 4. Success
        logger.info(f"Admin login SUCCESS for user: {username}")
        try:
            await redis.delete(attempts_key)
        except:
            pass
            
        request.session.update({"token": secrets.token_hex(32)})
        return True

    async def logout(self, request: Request) -> bool:
        request.session.clear()
        return True

    async def authenticate(self, request: Request) -> bool:
        return "token" in request.session

admin_auth = AdminAuth(secret_key=settings.SECRET_KEY)
