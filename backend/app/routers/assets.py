from fastapi import APIRouter, Query
from typing import Optional

from app.models.asset import MonthlyAsset
from app.services import csv_store

router = APIRouter(prefix="/assets", tags=["assets"])


def _apply_filters(
    rows: list[dict],
    user: Optional[str],
    year: Optional[int],
    month: Optional[int],
    institution: Optional[str],
    asset_type: Optional[str],
) -> list[dict]:
    if user:
        rows = [r for r in rows if r["user"] == user]
    if year:
        rows = [r for r in rows if r["snapshot_date"].startswith(str(year))]
    if month:
        month_str = f"{year or ''}-{month:02d}" if year else f"-{month:02d}"
        rows = [r for r in rows if month_str in r["snapshot_date"]]
    if institution:
        rows = [r for r in rows if r["institution"] == institution]
    if asset_type:
        rows = [r for r in rows if r["asset_type"] == asset_type]
    return rows


@router.get("/")
async def list_assets(
    user: Optional[str] = Query(None, description="사용자 필터 (없으면 전체)"),
    year: Optional[int] = Query(None),
    month: Optional[int] = Query(None, ge=1, le=12),
    institution: Optional[str] = Query(None),
    asset_type: Optional[str] = Query(None),
):
    rows = csv_store.read_assets()
    rows = _apply_filters(rows, user, year, month, institution, asset_type)
    return {"total": len(rows), "data": rows}


@router.post("/", status_code=201)
async def create_asset(asset: MonthlyAsset):
    row = asset.model_dump()
    row["snapshot_date"] = str(row["snapshot_date"])
    csv_store.append_assets([row])
    return {"message": "추가 완료", "data": row}


@router.get("/summary/portfolio")
async def portfolio_summary(
    user: Optional[str] = Query(None),
    year: Optional[int] = Query(None),
    month: Optional[int] = Query(None, ge=1, le=12),
):
    """자산 유형별 합계 (포트폴리오 파이차트용)"""
    rows = csv_store.read_assets()
    rows = _apply_filters(rows, user, year, month, None, None)
    summary: dict[str, int] = {}
    for r in rows:
        key = r.get("asset_type") or "기타"
        summary[key] = summary.get(key, 0) + int(r.get("balance_krw", 0))
    total = sum(summary.values())
    return {
        "total_krw": total,
        "data": [
            {"asset_type": k, "balance_krw": v, "ratio": round(v / total * 100, 2) if total else 0}
            for k, v in sorted(summary.items(), key=lambda x: -x[1])
        ],
    }


@router.get("/summary/monthly-trend")
async def monthly_trend(
    user: Optional[str] = Query(None),
    year: Optional[int] = Query(None),
):
    """월별 총자산 추이"""
    rows = csv_store.read_assets()
    if user:
        rows = [r for r in rows if r["user"] == user]
    if year:
        rows = [r for r in rows if r["snapshot_date"].startswith(str(year))]

    trend: dict[str, int] = {}
    for r in rows:
        key = r["snapshot_date"][:7]  # YYYY-MM
        trend[key] = trend.get(key, 0) + int(r.get("balance_krw", 0))
    return {"data": [{"month": k, "total_krw": v} for k, v in sorted(trend.items())]}
