"""하나카드 API 파싱 모듈 (스텁)"""
from datetime import date
from app.services.sync.base import BaseSyncer

INSTITUTION = "하나카드"


class HanaCardSyncer(BaseSyncer):
    async def fetch_transactions(self, target_date: date) -> list[dict]:
        return []
