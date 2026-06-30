from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from datetime import date

from app.models.transaction import Transaction, TransactionUpdate
from app.services import csv_store

router = APIRouter(prefix="/transactions", tags=["transactions"])


def _apply_filters(
    rows: list[dict],
    user: Optional[str],
    date_from: Optional[date],
    date_to: Optional[date],
    tag_person: Optional[str],
    tag_category: Optional[str],
    institution: Optional[str],
) -> list[dict]:
    if user:
        rows = [r for r in rows if r["user"] == user]
    if date_from:
        rows = [r for r in rows if r["date"] >= str(date_from)]
    if date_to:
        rows = [r for r in rows if r["date"] <= str(date_to)]
    if tag_person:
        rows = [r for r in rows if r["tag_person"] == tag_person]
    if tag_category:
        rows = [r for r in rows if r["tag_category"] == tag_category]
    if institution:
        rows = [r for r in rows if r["institution"] == institution]
    return rows


@router.get("/")
async def list_transactions(
    user: Optional[str] = Query(None, description="사용자 필터 (없으면 전체)"),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    tag_person: Optional[str] = Query(None),
    tag_category: Optional[str] = Query(None),
    institution: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
):
    rows = csv_store.read_transactions()
    rows = _apply_filters(rows, user, date_from, date_to, tag_person, tag_category, institution)
    total = len(rows)
    return {"total": total, "data": rows[skip: skip + limit]}


@router.post("/", status_code=201)
async def create_transaction(tx: Transaction):
    row = tx.model_dump()
    row["date"] = str(row["date"])
    csv_store.append_transactions([row])
    return {"message": "추가 완료", "data": row}


@router.patch("/{index}")
async def update_tags(index: int, body: TransactionUpdate):
    ok = csv_store.update_transaction_tags(index, body.tag_person, body.tag_category)
    if not ok:
        raise HTTPException(status_code=404, detail=f"index {index} 에 해당하는 내역이 없습니다.")
    return {"message": "태그 수정 완료"}


@router.get("/summary/category")
async def summary_by_category(
    user: Optional[str] = Query(None),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
):
    """카테고리별 지출 합계"""
    rows = csv_store.read_transactions()
    rows = _apply_filters(rows, user, date_from, date_to, None, None, None)
    summary: dict[str, int] = {}
    for r in rows:
        key = r.get("tag_category") or "미분류"
        summary[key] = summary.get(key, 0) + int(r.get("amount", 0))
    return {"data": [{"category": k, "total": v} for k, v in sorted(summary.items())]}


@router.get("/summary/person")
async def summary_by_person(
    user: Optional[str] = Query(None),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
):
    """대분류(사람)별 지출 합계"""
    rows = csv_store.read_transactions()
    rows = _apply_filters(rows, user, date_from, date_to, None, None, None)
    summary: dict[str, int] = {}
    for r in rows:
        key = r.get("tag_person") or "미분류"
        summary[key] = summary.get(key, 0) + int(r.get("amount", 0))
    return {"data": [{"person": k, "total": v} for k, v in sorted(summary.items())]}
