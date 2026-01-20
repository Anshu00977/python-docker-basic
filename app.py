from fastapi import FastAPI, status, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import time
from loguru import logger

from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import sessionmaker, declarative_base


app = FastAPI()

# -------------------- DATABASE SETUP --------------------

DATABASE_URL = "sqlite:///./database.db"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)

# ✅ MOVED HERE (correct place)
Base.metadata.create_all(bind=engine)

# -------------------- ERROR HANDLING --------------------

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "success": False,
            "message": "Validation failed",
            "errors": exc.errors()
        },
    )

# -------------------- LOGGING MIDDLEWARE --------------------

@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()

    response = await call_next(request)

    duration = round((time.time() - start_time) * 1000, 2)

    logger.info(
        f"{request.method} {request.url.path} "
        f"→ {response.status_code} "
        f"({duration}ms)"
    )

    return response

# -------------------- ROUTES --------------------

@app.get("/")
def root():
    return {
        "success": True,
        "data": {"status": "ok"}
    }

# -------------------- REQUEST SCHEMA --------------------

class UserCreate(BaseModel):
    name: str
    email: str

# -------------------- CREATE USER --------------------

@app.post("/users", status_code=201)
def create_user(user: UserCreate):
    db = SessionLocal()

    # Business rule → 400
    if not user.email.endswith("@test.com"):
        db.close()
        raise HTTPException(
            status_code=400,
            detail="Email must be from @test.com domain"
        )

    # ✅ INSERT INTO DB
    new_user = User(
        name=user.name,
        email=user.email
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    db.close()

    return {
        "success": True,
        "data": {
            "name": new_user.name,
            "email": new_user.email
        }
    }
