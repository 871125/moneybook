import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import transactions, assets
from app.services.scheduler import start_scheduler, stop_scheduler, _daily_transaction_sync, _monthly_asset_snapshot

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")


@asynccontextmanager
async def lifespan(app: FastAPI):
    start_scheduler()
    yield
    stop_scheduler()


app = FastAPI(
    title="MoneyBook API",
    description="통합 가계부 및 자산 관리 대시보드 API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(transactions.router, prefix="/api/v1")
app.include_router(assets.router, prefix="/api/v1")


@app.get("/health", tags=["system"])
async def health():
    return {"status": "ok"}


@app.post("/api/v1/sync/transactions", tags=["system"])
async def manual_transaction_sync():
    """거래 내역 즉시 동기화 (테스트/수동 실행용)"""
    await _daily_transaction_sync()
    return {"message": "거래 내역 동기화 완료"}


@app.post("/api/v1/sync/assets", tags=["system"])
async def manual_asset_snapshot():
    """자산 스냅샷 즉시 수집 (테스트/수동 실행용)"""
    await _monthly_asset_snapshot()
    return {"message": "자산 스냅샷 수집 완료"}
