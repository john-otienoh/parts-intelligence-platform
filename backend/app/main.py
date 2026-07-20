"""FastAPI application factory."""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.routers import listings


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(
    title="BE FORWARD Parts Intelligence API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(listings.router, prefix="/api/v1/listings", tags=["listings"])


@app.get("/health")
def health_check():
    return {"status": "ok"}