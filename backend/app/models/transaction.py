from pydantic import BaseModel, field_validator
from typing import Optional
from datetime import date


class Transaction(BaseModel):
    date: date
    user: str
    institution: str
    type: str                        # 입금 | 출금 | 승인 | 취소
    amount: int
    description: str
    tag_person: Optional[str] = ""   # 본인 | 배우자 | 자녀 | 공동
    tag_category: Optional[str] = "" # 식비 | 주거비 | 차량유지비 | ...

    @field_validator("amount")
    @classmethod
    def amount_positive(cls, v: int) -> int:
        if v < 0:
            raise ValueError("amount는 0 이상이어야 합니다.")
        return v


class TransactionUpdate(BaseModel):
    """태그 수정용 — 변경할 필드만 전달"""
    tag_person: Optional[str] = None
    tag_category: Optional[str] = None


class TransactionFilter(BaseModel):
    user: Optional[str] = None          # None이면 전체(통합)
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    tag_person: Optional[str] = None
    tag_category: Optional[str] = None
    institution: Optional[str] = None
