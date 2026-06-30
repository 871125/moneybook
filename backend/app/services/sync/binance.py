"""
Binance REST API 연동 모듈

Binance API 문서: https://binance-docs.github.io/apidocs/spot/en
인증: HMAC-SHA256(queryString, secret) → signature 파라미터 + X-MBX-APIKEY 헤더
KRW 환산: 각 코인 USDT 가치 × USDT/KRW 환율 (Upbit 공개 API 사용)
"""
import hashlib
import hmac
import logging
import time
from datetime import date
from urllib.parse import urlencode

import httpx

from app.services.sync.base import BaseAssetSyncer

logger = logging.getLogger(__name__)

INSTITUTION = "Binance"
BASE_URL = "https://api.binance.com"

# USDT·BUSD·USDC 등 스테이블코인은 1달러로 처리
_USD_STABLE = {"USDT", "BUSD", "USDC", "TUSD", "USDP", "DAI", "FDUSD"}

# KRW로 직접 표기할 코인 (바이낸스에 KRW 마켓 없어 USDT 환산 후 변환)
_SKIP_ZERO_THRESHOLD = 0.01   # USDT 기준 0.01달러 미만 잔고 스킵


def _sign(secret: str, query_string: str) -> str:
    return hmac.new(secret.encode(), query_string.encode(), hashlib.sha256).hexdigest()


def _mbx_headers(api_key: str) -> dict:
    return {
        "X-MBX-APIKEY": api_key,
        "Content-Type": "application/json",
    }


async def _get_usdt_krw(client: httpx.AsyncClient) -> float:
    """Upbit 공개 API에서 USDT/KRW 환율 조회 (인증 불필요)"""
    try:
        resp = await client.get(
            "https://api.upbit.com/v1/ticker",
            params={"markets": "KRW-USDT"},
            timeout=5,
        )
        resp.raise_for_status()
        data = resp.json()
        return float(data[0]["trade_price"])
    except Exception as e:
        logger.warning("Upbit USDT/KRW 조회 실패, 기본값 1350 사용: %s", e)
        return 1350.0


async def _get_prices_in_usdt(
    client: httpx.AsyncClient, symbols: list[str]
) -> dict[str, float]:
    """여러 코인의 USDT 가격을 한번에 조회"""
    if not symbols:
        return {}

    try:
        resp = await client.get(
            f"{BASE_URL}/api/v3/ticker/price",
            timeout=10,
        )
        resp.raise_for_status()
        all_prices = {item["symbol"]: float(item["price"]) for item in resp.json()}
    except Exception as e:
        logger.warning("Binance 가격 조회 실패: %s", e)
        return {}

    result: dict[str, float] = {}
    for coin in symbols:
        if coin in _USD_STABLE:
            result[coin] = 1.0
            continue
        # USDT 마켓 우선, 없으면 BUSD 마켓
        for quote in ("USDT", "BUSD", "BTC"):
            sym = coin + quote
            if sym in all_prices:
                price = all_prices[sym]
                if quote == "BTC":
                    price *= all_prices.get("BTCUSDT", 0)
                result[coin] = price
                break

    return result


class BinanceAssetSyncer(BaseAssetSyncer):
    """Binance 보유 자산 수집기 (Spot + Earn 잔고 → KRW 환산)"""

    async def _signed_get(
        self, client: httpx.AsyncClient, path: str, params: dict | None = None
    ) -> dict:
        p = params or {}
        p["timestamp"] = int(time.time() * 1000)
        query = urlencode(p)
        sig = _sign(self.secret, query)
        url = f"{BASE_URL}{path}?{query}&signature={sig}"
        resp = await client.get(url, headers=_mbx_headers(self.api_key), timeout=10)
        resp.raise_for_status()
        return resp.json()

    async def _fetch_spot_balances(self, client: httpx.AsyncClient) -> list[dict]:
        """Spot 계좌 잔고"""
        data = await self._signed_get(client, "/api/v3/account")
        result = []
        for b in data.get("balances", []):
            total = float(b["free"]) + float(b["locked"])
            if total > 0:
                result.append({"asset": b["asset"], "amount": total})
        return result

    async def _fetch_earn_balances(self, client: httpx.AsyncClient) -> list[dict]:
        """Simple Earn(유연·고정) 잔고"""
        result = []
        try:
            # Flexible Earn
            data = await self._signed_get(
                client, "/sapi/v1/simple-earn/flexible/position", {"size": 100}
            )
            for row in data.get("rows", []):
                amt = float(row.get("totalAmount", row.get("amount", 0)))
                if amt > 0:
                    result.append({"asset": row["asset"], "amount": amt})
        except httpx.HTTPStatusError:
            pass

        try:
            # Locked Earn
            data = await self._signed_get(
                client, "/sapi/v1/simple-earn/locked/position", {"size": 100}
            )
            for row in data.get("rows", []):
                amt = float(row.get("amount", 0))
                if amt > 0:
                    result.append({"asset": row["asset"], "amount": amt})
        except httpx.HTTPStatusError:
            pass

        return result

    async def fetch_assets(self, snapshot_date: date) -> list[dict]:
        if not self.api_key or not self.secret:
            logger.warning("Binance API 키 미설정 (user=%s)", self.user)
            return []

        results: list[dict] = []
        try:
            async with httpx.AsyncClient() as client:
                usdt_krw = await _get_usdt_krw(client)

                # Spot + Earn 잔고 합산
                spot = await self._fetch_spot_balances(client)
                earn = await self._fetch_earn_balances(client)

                # 코인별 합산
                totals: dict[str, float] = {}
                for item in spot + earn:
                    totals[item["asset"]] = totals.get(item["asset"], 0) + item["amount"]

                # USDT 가격 일괄 조회
                coins = list(totals.keys())
                prices = await _get_prices_in_usdt(client, coins)

                for coin, amount in totals.items():
                    usdt_price = prices.get(coin, 0.0)
                    usdt_value = amount * usdt_price
                    if usdt_value < _SKIP_ZERO_THRESHOLD:
                        continue
                    balance_krw = int(usdt_value * usdt_krw)
                    results.append({
                        "snapshot_date": snapshot_date.isoformat(),
                        "user": self.user,
                        "institution": INSTITUTION,
                        "asset_type": coin,
                        "balance_krw": balance_krw,
                    })

                logger.info(
                    "Binance 자산 조회 완료 (user=%s, 코인=%d종, USDT/KRW=%.0f)",
                    self.user, len(results), usdt_krw,
                )
        except httpx.HTTPStatusError as e:
            logger.error(
                "Binance API 오류 (user=%s): %s %s",
                self.user, e.response.status_code, e.response.text,
            )
        except Exception as e:
            logger.error("Binance 오류 (user=%s): %s", self.user, e)

        return results
