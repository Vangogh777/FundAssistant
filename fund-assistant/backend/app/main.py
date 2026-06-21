from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import init_db
from app.routers import auth, funds, portfolio, market, analysis, drip, ocr


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(
    title="基金智能助手 API",
    description="管理基金持仓、实时估值、AI 分析、市场行情",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(auth.router)
app.include_router(funds.router)
app.include_router(portfolio.router)
app.include_router(market.router)
app.include_router(analysis.router)
app.include_router(drip.router)
app.include_router(ocr.router)


@app.get("/api/health")
async def health():
    return {"status": "ok", "version": "1.0.0"}
