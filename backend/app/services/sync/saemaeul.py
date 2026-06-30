"""새마을금고 API 파싱 모듈 (스텁)"""
from datetime import date
from app.services.sync.base import BaseSyncer, BaseAssetSyncer

INSTITUTION = "새마을금고"


class SaemaeulTransactionSyncer(BaseSyncer):
    async def fetch_transactions(self, target_date: date) -> list[dict]:
        return []


class SaemaeulAssetSyncer(BaseAssetSyncer):
    async def fetch_assets(self, snapshot_date: date) -> list[dict]:
        return []
