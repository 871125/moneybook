"""
우리은행 API 파싱 모듈 (스텁)
실제 API 연동 시 fetch_transactions / fetch_assets 내부를 구현합니다.
"""
import httpx
from datetime import date

from app.services.sync.base import BaseSyncer, BaseAssetSyncer

INSTITUTION = "우리은행"


class WooriBankTransactionSyncer(BaseSyncer):
    async def fetch_transactions(self, target_date: date) -> list[dict]:
        # TODO: 우리은행 오픈뱅킹 API 호출 후 표준 포맷 변환
        return []


class WooriBankAssetSyncer(BaseAssetSyncer):
    async def fetch_assets(self, snapshot_date: date) -> list[dict]:
        # TODO: 우리은행 계좌 잔고 조회 후 표준 포맷 변환
        return []
