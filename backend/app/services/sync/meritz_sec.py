"""메리츠증권 API 파싱 모듈 (스텁)"""
from datetime import date
from app.services.sync.base import BaseAssetSyncer

INSTITUTION = "메리츠"


class MeritzSecAssetSyncer(BaseAssetSyncer):
    async def fetch_assets(self, snapshot_date: date) -> list[dict]:
        return []
