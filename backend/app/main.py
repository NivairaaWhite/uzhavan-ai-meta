from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.database import init_db, wait_for_db
from app.routers import users, crops, market, orders, logistics, post_harvest

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    wait_for_db()  # retries instead of crashing if Postgres is still starting
    if settings.DEBUG:
        init_db()  # dev convenience only — prod uses Alembic migrations
    yield


app = FastAPI(
    title=settings.APP_NAME,
    description="Backend API for Uzhavan.AI — offline crop grading, fair-price "
                 "marketplace, logistics pooling, and post-harvest advisory "
                 "(sell/store/process) for Tamil Nadu farmers.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.DEBUG else [],  # lock this down in prod
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(users.router)
app.include_router(crops.router)
app.include_router(market.router)
app.include_router(orders.router)
app.include_router(logistics.router)
app.include_router(post_harvest.router)


@app.get("/health", tags=["meta"])
def health():
    return {"status": "ok", "app": settings.APP_NAME, "env": settings.ENV}
