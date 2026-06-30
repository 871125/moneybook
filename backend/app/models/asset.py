from pydantic import BaseModel, field_validator
from typing import Optional
from datetime import date


class MonthlyAsset(BaseModel):
    snapshot_date: date
    user: str
    institution: str
    asset_type: str    # 현금 | USDT | BTC | ETH | 주식 | ...
    balance_krw: int   # KRW 환산 잔액

    @field_validator("balance_krw")
    @classmethod
    def balance_non_negative(cls, v: int) -> int:
        if v < 0:
            raise ValueError("balance_krw는 0 이상이어야 합니다.")
        return v


class AssetFilter(BaseModel):
    user: Optional[str] = None        # None이면 전체(통합)
    year: Optional[int] = None
    month: Optional[int] = None
    institution: Optional[str] = None
    asset_type: Optional[str] = None
