"""Upbit API 파싱 모듈 (스텁)"""
from datetime import date
from app.services.sync.base import BaseAssetSyncer

INSTITUTION = "Upbit"


class UpbitAssetSyncer(BaseAssetSyncer):
    async def fetch_assets(self, snapshot_date: date) -> list[dict]:
        return []
