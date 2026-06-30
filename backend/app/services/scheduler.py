"""
APScheduler 기반 배치 작업
- 매일 오전 2시: 모든 기관에서 전일 거래 내역 수집
- 매월 1일 오전 0시 10분: 월별 자산 스냅샷 수집
"""
import logging
from datetime import date, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.config import get_settings
from app.services import csv_store
from app.services.sync.woori_bank import WooriBankTransactionSyncer, WooriBankAssetSyncer
from app.services.sync.kakao_bank import KakaoBankTransactionSyncer, KakaoBankAssetSyncer
from app.services.sync.hana_bank import HanaBankTransactionSyncer, HanaBankAssetSyncer
from app.services.sync.saemaeul import SaemaeulTransactionSyncer, SaemaeulAssetSyncer
from app.services.sync.woori_card import WooriCardSyncer
from app.services.sync.hana_card import HanaCardSyncer
from app.services.sync.shinhan_card import ShinhanCardSyncer
from app.services.sync.lotte_card import LotteCardSyncer
from app.services.sync.samsung_card import SamsungCardSyncer
from app.services.sync.samsung_sec import SamsungSecAssetSyncer
from app.services.sync.mirae_sec import MiraeSecAssetSyncer
from app.services.sync.meritz_sec import MeritzSecAssetSyncer
from app.services.sync.nh_sec import NHSecAssetSyncer
from app.services.sync.binance import BinanceAssetSyncer
from app.services.sync.bingx import BingXAssetSyncer
from app.services.sync.upbit import UpbitAssetSyncer

logger = logging.getLogger(__name__)
scheduler = AsyncIOScheduler(timezone="Asia/Seoul")


def _build_transaction_syncers(settings) -> list:
    u1, u2 = settings.user1_name, settings.user2_name
    return [
        WooriBankTransactionSyncer(u1, settings.user1_woori_bank_app_key, settings.user1_woori_bank_app_secret, settings.user1_woori_bank_account),
        KakaoBankTransactionSyncer(u1, settings.user1_kakao_bank_app_key, settings.user1_kakao_bank_app_secret, settings.user1_kakao_bank_account),
        HanaBankTransactionSyncer(u1, settings.user1_hana_bank_app_key, settings.user1_hana_bank_app_secret, settings.user1_hana_bank_account),
        SaemaeulTransactionSyncer(u1, settings.user1_saemaeul_app_key, settings.user1_saemaeul_app_secret, settings.user1_saemaeul_branch, settings.user1_saemaeul_account),
        WooriCardSyncer(u1, settings.user1_woori_card_app_key, settings.user1_woori_card_app_secret, settings.user1_woori_card_no),
        HanaCardSyncer(u1, settings.user1_hana_card_app_key, settings.user1_hana_card_app_secret, settings.user1_hana_card_no),
        ShinhanCardSyncer(u1, settings.user1_shinhan_card_app_key, settings.user1_shinhan_card_app_secret, settings.user1_shinhan_card_no),
        LotteCardSyncer(u1, settings.user1_lotte_card_app_key, settings.user1_lotte_card_app_secret, settings.user1_lotte_card_no),
        SamsungCardSyncer(u1, settings.user1_samsung_card_app_key, settings.user1_samsung_card_app_secret, settings.user1_samsung_card_no),
        WooriBankTransactionSyncer(u2, settings.user2_woori_bank_app_key, settings.user2_woori_bank_app_secret, settings.user2_woori_bank_account),
        KakaoBankTransactionSyncer(u2, settings.user2_kakao_bank_app_key, settings.user2_kakao_bank_app_secret, settings.user2_kakao_bank_account),
        HanaBankTransactionSyncer(u2, settings.user2_hana_bank_app_key, settings.user2_hana_bank_app_secret, settings.user2_hana_bank_account),
        SaemaeulTransactionSyncer(u2, settings.user2_saemaeul_app_key, settings.user2_saemaeul_app_secret, settings.user2_saemaeul_branch, settings.user2_saemaeul_account),
        WooriCardSyncer(u2, settings.user2_woori_card_app_key, settings.user2_woori_card_app_secret, settings.user2_woori_card_no),
        HanaCardSyncer(u2, settings.user2_hana_card_app_key, settings.user2_hana_card_app_secret, settings.user2_hana_card_no),
        ShinhanCardSyncer(u2, settings.user2_shinhan_card_app_key, settings.user2_shinhan_card_app_secret, settings.user2_shinhan_card_no),
        LotteCardSyncer(u2, settings.user2_lotte_card_app_key, settings.user2_lotte_card_app_secret, settings.user2_lotte_card_no),
        SamsungCardSyncer(u2, settings.user2_samsung_card_app_key, settings.user2_samsung_card_app_secret, settings.user2_samsung_card_no),
    ]


def _build_asset_syncers(settings) -> list:
    u1, u2 = settings.user1_name, settings.user2_name
    return [
        WooriBankAssetSyncer(u1, settings.user1_woori_bank_app_key, settings.user1_woori_bank_app_secret, settings.user1_woori_bank_account),
        KakaoBankAssetSyncer(u1, settings.user1_kakao_bank_app_key, settings.user1_kakao_bank_app_secret, settings.user1_kakao_bank_account),
        HanaBankAssetSyncer(u1, settings.user1_hana_bank_app_key, settings.user1_hana_bank_app_secret, settings.user1_hana_bank_account),
        SaemaeulAssetSyncer(u1, settings.user1_saemaeul_app_key, settings.user1_saemaeul_app_secret, settings.user1_saemaeul_branch, settings.user1_saemaeul_account),
        SamsungSecAssetSyncer(u1, settings.user1_samsung_sec_app_key, settings.user1_samsung_sec_app_secret, settings.user1_samsung_sec_account),
        MiraeSecAssetSyncer(u1, settings.user1_mirae_sec_app_key, settings.user1_mirae_sec_app_secret, settings.user1_mirae_sec_account),
        MeritzSecAssetSyncer(u1, settings.user1_meritz_sec_app_key, settings.user1_meritz_sec_app_secret, settings.user1_meritz_sec_account),
        NHSecAssetSyncer(u1, settings.user1_nh_sec_app_key, settings.user1_nh_sec_app_secret, settings.user1_nh_sec_account),
        BinanceAssetSyncer(u1, settings.user1_binance_api_key, settings.user1_binance_secret),
        UpbitAssetSyncer(u1, settings.user1_upbit_access_key, settings.user1_upbit_secret_key),
        WooriBankAssetSyncer(u2, settings.user2_woori_bank_app_key, settings.user2_woori_bank_app_secret, settings.user2_woori_bank_account),
        KakaoBankAssetSyncer(u2, settings.user2_kakao_bank_app_key, settings.user2_kakao_bank_app_secret, settings.user2_kakao_bank_account),
        HanaBankAssetSyncer(u2, settings.user2_hana_bank_app_key, settings.user2_hana_bank_app_secret, settings.user2_hana_bank_account),
        SaemaeulAssetSyncer(u2, settings.user2_saemaeul_app_key, settings.user2_saemaeul_app_secret, settings.user2_saemaeul_branch, settings.user2_saemaeul_account),
        SamsungSecAssetSyncer(u2, settings.user2_samsung_sec_app_key, settings.user2_samsung_sec_app_secret, settings.user2_samsung_sec_account),
        MiraeSecAssetSyncer(u2, settings.user2_mirae_sec_app_key, settings.user2_mirae_sec_app_secret, settings.user2_mirae_sec_account),
        MeritzSecAssetSyncer(u2, settings.user2_meritz_sec_app_key, settings.user2_meritz_sec_app_secret, settings.user2_meritz_sec_account),
        NHSecAssetSyncer(u2, settings.user2_nh_sec_app_key, settings.user2_nh_sec_app_secret, settings.user2_nh_sec_account),
        BingXAssetSyncer(u2, settings.user2_bingx_api_key, settings.user2_bingx_secret),
        UpbitAssetSyncer(u2, settings.user2_upbit_access_key, settings.user2_upbit_secret_key),
    ]


async def _daily_transaction_sync():
    """전일 거래 내역 수집 (매일 오전 2시)"""
    settings = get_settings()
    target_date = date.today() - timedelta(days=1)
    logger.info("거래 내역 동기화 시작: %s", target_date)

    all_rows: list[dict] = []
    for syncer in _build_transaction_syncers(settings):
        try:
            rows = await syncer.fetch_transactions(target_date)
            all_rows.extend(rows)
        except Exception as e:
            logger.error("%s 동기화 실패: %s", type(syncer).__name__, e)

    if all_rows:
        csv_store.append_transactions(all_rows)
        logger.info("거래 내역 %d건 저장 완료", len(all_rows))


async def _monthly_asset_snapshot():
    """월별 자산 스냅샷 수집 (매월 1일 오전 0시 10분)"""
    settings = get_settings()
    snapshot_date = date.today()
    logger.info("자산 스냅샷 수집 시작: %s", snapshot_date)

    all_rows: list[dict] = []
    for syncer in _build_asset_syncers(settings):
        try:
            rows = await syncer.fetch_assets(snapshot_date)
            all_rows.extend(rows)
        except Exception as e:
            logger.error("%s 자산 수집 실패: %s", type(syncer).__name__, e)

    if all_rows:
        csv_store.append_assets(all_rows)
        logger.info("자산 스냅샷 %d건 저장 완료", len(all_rows))


def start_scheduler():
    scheduler.add_job(
        _daily_transaction_sync,
        CronTrigger(hour=2, minute=0, timezone="Asia/Seoul"),
        id="daily_tx_sync",
        replace_existing=True,
    )
    scheduler.add_job(
        _monthly_asset_snapshot,
        CronTrigger(day=1, hour=0, minute=10, timezone="Asia/Seoul"),
        id="monthly_asset_snapshot",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("스케줄러 시작 완료")


def stop_scheduler():
    scheduler.shutdown()
