"""
CSV 기반 데이터 저장소 — File Lock으로 동시 쓰기 충돌 방지
"""
import csv
import os
from pathlib import Path
from typing import Any
from filelock import FileLock

from app.config import get_settings

settings = get_settings()

TRANSACTIONS_FILE = Path(settings.data_dir) / "transactions.csv"
ASSETS_FILE = Path(settings.data_dir) / "monthly_assets.csv"

TRANSACTION_FIELDS = [
    "date", "user", "institution", "type",
    "amount", "description", "tag_person", "tag_category",
]
ASSET_FIELDS = [
    "snapshot_date", "user", "institution", "asset_type", "balance_krw",
]


def _lock_path(csv_path: Path) -> Path:
    return csv_path.with_suffix(".lock")


def _ensure_file(csv_path: Path, fieldnames: list[str]) -> None:
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    if not csv_path.exists():
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()


def read_csv(csv_path: Path, fieldnames: list[str]) -> list[dict[str, Any]]:
    _ensure_file(csv_path, fieldnames)
    with FileLock(_lock_path(csv_path)):
        with open(csv_path, "r", newline="", encoding="utf-8") as f:
            return list(csv.DictReader(f))


def append_rows(csv_path: Path, fieldnames: list[str], rows: list[dict[str, Any]]) -> None:
    _ensure_file(csv_path, fieldnames)
    with FileLock(_lock_path(csv_path)):
        with open(csv_path, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
            writer.writerows(rows)


def rewrite_csv(csv_path: Path, fieldnames: list[str], rows: list[dict[str, Any]]) -> None:
    """전체 파일 덮어쓰기 — 태그 수정 등 업데이트 시 사용"""
    _ensure_file(csv_path, fieldnames)
    with FileLock(_lock_path(csv_path)):
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)


# ── 거래 내역 ────────────────────────────────────────────

def read_transactions() -> list[dict[str, Any]]:
    return read_csv(TRANSACTIONS_FILE, TRANSACTION_FIELDS)


def append_transactions(rows: list[dict[str, Any]]) -> None:
    append_rows(TRANSACTIONS_FILE, TRANSACTION_FIELDS, rows)


def update_transaction_tags(index: int, tag_person: str | None, tag_category: str | None) -> bool:
    """0-based index 행의 태그를 수정합니다."""
    rows = read_csv(TRANSACTIONS_FILE, TRANSACTION_FIELDS)
    if index < 0 or index >= len(rows):
        return False
    if tag_person is not None:
        rows[index]["tag_person"] = tag_person
    if tag_category is not None:
        rows[index]["tag_category"] = tag_category
    rewrite_csv(TRANSACTIONS_FILE, TRANSACTION_FIELDS, rows)
    return True


# ── 월별 자산 ────────────────────────────────────────────

def read_assets() -> list[dict[str, Any]]:
    return read_csv(ASSETS_FILE, ASSET_FIELDS)


def append_assets(rows: list[dict[str, Any]]) -> None:
    append_rows(ASSETS_FILE, ASSET_FIELDS, rows)
