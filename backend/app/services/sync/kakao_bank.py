"""카카오뱅크 API 파싱 모듈 (스텁)"""
from datetime import date
from app.services.sync.base import BaseSyncer, BaseAssetSyncer

INSTITUTION = "카카오뱅크"


class KakaoBankTransactionSyncer(BaseSyncer):
    async def fetch_transactions(self, target_date: date) -> list[dict]:
        return []


class KakaoBankAssetSyncer(BaseAssetSyncer):
    async def fetch_assets(self, snapshot_date: date) -> list[dict]:
        return []
