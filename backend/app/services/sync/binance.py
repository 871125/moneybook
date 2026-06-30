"""
Binance API 파싱 모듈 (스텁)
실제 연동 시 python-binance 또는 httpx로 REST API 호출.
"""
from datetime import date
from app.services.sync.base import BaseAssetSyncer

INSTITUTION = "Binance"


class BinanceAssetSyncer(BaseAssetSyncer):
    async def fetch_assets(self, snapshot_date: date) -> list[dict]:
        # TODO: GET /api/v3/account → balances 필터링 → KRW 환산
        return []
