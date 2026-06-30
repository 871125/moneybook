"""하나은행 API 파싱 모듈 (스텁)"""
from datetime import date
from app.services.sync.base import BaseSyncer, BaseAssetSyncer

INSTITUTION = "하나은행"


class HanaBankTransactionSyncer(BaseSyncer):
    async def fetch_transactions(self, target_date: date) -> list[dict]:
        return []


class HanaBankAssetSyncer(BaseAssetSyncer):
    async def fetch_assets(self, snapshot_date: date) -> list[dict]:
        return []
