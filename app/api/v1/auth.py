"""OAuth2 password flow, JWT bearer tokens, RBAC (admin/pro/free)."""
from datetime import datetime, timedelta, timezone
import hashlib, secrets
from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.database import get_db
from app.models.orm import User

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])
pwd = CryptContext(schemes=["bcrypt"])
oauth = OAuth2PasswordBearer("/api/v1/auth/login", auto_error=False)

class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=10, max_length=128)

def make_token(uid: int) -> str:
    return jwt.encode({"sub": str(uid), "exp": datetime.now(timezone.utc) + timedelta(hours=12)}, settings.jwt_secret, "HS256")

async def optional_user(tok: str | None = Depends(oauth), key: str | None = Header(None, alias="X-API-Key"), db: AsyncSession = Depends(get_db)) -> User | None:
    if key:  # API-key auth: only the SHA-256 digest is stored
        return (await db.execute(select(User).where(User.api_key == hashlib.sha256(key.encode()).hexdigest()))).scalar()
    if not tok:
        return None
    try:
        uid = int(jwt.decode(tok, settings.jwt_secret, ["HS256"])["sub"])
    except (JWTError, ValueError):
        raise HTTPException(401, "Invalid token")
    return await db.get(User, uid)

async def current_user(u: User | None = Depends(optional_user)) -> User:
    if not u:
        raise HTTPException(401, "Login required")
    return u

def require_role(*roles: str):
    async def dep(u: User = Depends(current_user)) -> User:
        if u.role not in roles:
            raise HTTPException(403, "Insufficient role")
        return u
    return dep

@router.post("/register", status_code=201)
async def register(b: RegisterIn, db: AsyncSession = Depends(get_db)) -> dict:
    if (await db.execute(select(User).where(User.email == b.email))).scalar():
        raise HTTPException(409, "Email taken")
    u = User(email=b.email, hashed_password=pwd.hash(b.password))
    db.add(u); await db.commit()
    return {"id": u.id, "role": u.role}

@router.post("/login")
async def login(f: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)) -> dict:
    u = (await db.execute(select(User).where(User.email == f.username))).scalar()
    if not u or not pwd.verify(f.password, u.hashed_password):
        raise HTTPException(401, "Bad credentials")
    return {"access_token": make_token(u.id), "token_type": "bearer"}

@router.post("/apikey")
async def new_key(u: User = Depends(current_user), db: AsyncSession = Depends(get_db)) -> dict:
    """Issue a fresh API key (shown once; rotating invalidates the old one)."""
    raw = "ls_" + secrets.token_urlsafe(32)
    u.api_key = hashlib.sha256(raw.encode()).hexdigest()
    db.add(u); await db.commit()
    return {"api_key": raw}
