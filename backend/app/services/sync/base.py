"""
기관별 파싱 모듈의 공통 인터페이스
각 기관 모듈은 BaseSyncer를 상속하여 fetch_transactions / fetch_assets를 구현합니다.
"""
from abc import ABC, abstractmethod
from datetime import date


class BaseSyncer(ABC):
    """거래 내역 수집기 기본 클래스"""

    def __init__(self, user: str, api_key: str, secret: str = ""):
        self.user = user
        self.api_key = api_key
        self.secret = secret

    @abstractmethod
    async def fetch_transactions(self, target_date: date) -> list[dict]:
        """
        지정 날짜의 거래 내역을 가져와 표준 포맷으로 반환합니다.
        반환 형식:
        [
            {
                "date": "YYYY-MM-DD",
                "user": str,
                "institution": str,
                "type": str,       # 입금 | 출금 | 승인 | 취소
                "amount": int,     # 원화 기준 양수
                "description": str,
                "tag_person": "",
                "tag_category": "",
            },
            ...
        ]
        """
        ...


class BaseAssetSyncer(ABC):
    """자산 현황 수집기 기본 클래스"""

    def __init__(self, user: str, api_key: str, secret: str = ""):
        self.user = user
        self.api_key = api_key
        self.secret = secret

    @abstractmethod
    async def fetch_assets(self, snapshot_date: date) -> list[dict]:
        """
        지정 날짜 기준 자산 현황을 가져와 표준 포맷으로 반환합니다.
        반환 형식:
        [
            {
                "snapshot_date": "YYYY-MM-DD",
                "user": str,
                "institution": str,
                "asset_type": str,   # 현금 | USDT | BTC | ...
                "balance_krw": int,
            },
            ...
        ]
        """
        ...
