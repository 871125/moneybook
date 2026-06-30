"""
BingX Open API 연동 모듈

BingX API 문서: https://bingx-api.github.io/docs
인증: HMAC-SHA256(queryString, secret) → signature 파라미터 + X-BX-APIKEY 헤더
자산 범위: Spot 계좌 + Perpetual(영구선물) USDT-M 계좌
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

INSTITUTION = "BingX"
BASE_URL = "https://open-api.bingx.com"

_USD_STABLE = {"USDT", "USDC", "BUSD", "DAI", "FDUSD"}
_SKIP_ZERO_THRESHOLD = 0.01   # USDT 기준 0.01달러 미만 잔고 스킵


def _sign(secret: str, query_string: str) -> str:
    return hmac.new(secret.encode(), query_string.encode(), hashlib.sha256).hexdigest()


def _bx_headers(api_key: str) -> dict:
    return {
        "X-BX-APIKEY": api_key,
        "Content-Type": "application/json",
    }


async def _get_usdt_krw(client: httpx.AsyncClient) -> float:
    """Upbit 공개 API에서 USDT/KRW 환율 조회"""
    try:
        resp = await client.get(
            "https://api.upbit.com/v1/ticker",
            params={"markets": "KRW-USDT"},
            timeout=5,
        )
        resp.raise_for_status()
        return float(resp.json()[0]["trade_price"])
    except Exception as e:
        logger.warning("Upbit USDT/KRW 조회 실패, 기본값 1350 사용: %s", e)
        return 1350.0


async def _get_spot_prices_usdt(
    client: httpx.AsyncClient, coins: list[str]
) -> dict[str, float]:
    """BingX Spot 마켓에서 코인별 USDT 가격 조회"""
    if not coins:
        return {}
    try:
        resp = await client.get(
            f"{BASE_URL}/openApi/spot/v1/ticker/24hr",
            timeout=10,
        )
        resp.raise_for_status()
        body = resp.json()
        all_prices = {
            item["symbol"]: float(item["lastPrice"])
            for item in body.get("data", [])
            if item.get("lastPrice")
        }
    except Exception as e:
        logger.warning("BingX 가격 조회 실패: %s", e)
        return {}

    result: dict[str, float] = {}
    for coin in coins:
        if coin in _USD_STABLE:
            result[coin] = 1.0
            continue
        for quote in ("USDT", "USDC"):
            sym = f"{coin}-{quote}"
            if sym in all_prices:
                result[coin] = all_prices[sym]
                break
    return result


class BingXAssetSyncer(BaseAssetSyncer):
    """BingX 보유 자산 수집기 (Spot + Perpetual Futures → KRW 환산)"""

    def _signed_params(self, params: dict | None = None) -> dict:
        p = params or {}
        p["timestamp"] = int(time.time() * 1000)
        p["recvWindow"] = 5000
        query = urlencode(sorted(p.items()))
        p["signature"] = _sign(self.secret, query)
        return p

    async def _fetch_spot_balances(self, client: httpx.AsyncClient) -> list[dict]:
        """Spot 계좌 잔고"""
        params = self._signed_params()
        resp = await client.get(
            f"{BASE_URL}/openApi/spot/v1/account/balance",
            params=params,
            headers=_bx_headers(self.api_key),
            timeout=10,
        )
        resp.raise_for_status()
        body = resp.json()

        result = []
        for b in body.get("data", {}).get("balances", []):
            total = float(b.get("free", 0)) + float(b.get("locked", 0))
            if total > 0:
                result.append({"asset": b["asset"], "amount": total, "source": "Spot"})
        return result

    async def _fetch_perp_balance(self, client: httpx.AsyncClient) -> list[dict]:
        """Perpetual Futures(USDT-M) 계좌 잔고"""
        try:
            params = self._signed_params()
            resp = await client.get(
                f"{BASE_URL}/openApi/swap/v2/user/balance",
                params=params,
                headers=_bx_headers(self.api_key),
                timeout=10,
            )
            resp.raise_for_status()
            body = resp.json()

            result = []
            for b in body.get("data", {}).get("balance", []):
                # balance: 지갑잔고, unrealizedProfit: 미실현손익 포함한 총 가치
                equity = float(b.get("equity", b.get("balance", 0)))
                if equity > 0:
                    asset = b.get("asset", "USDT")
                    result.append({"asset": asset, "amount": equity, "source": "Perpetual"})
            return result
        except httpx.HTTPStatusError as e:
            if e.response.status_code in (400, 404):
                return []
            raise

    async def fetch_assets(self, snapshot_date: date) -> list[dict]:
        if not self.api_key or not self.secret:
            logger.warning("BingX API 키 미설정 (user=%s)", self.user)
            return []

        results: list[dict] = []
        try:
            async with httpx.AsyncClient() as client:
                usdt_krw = await _get_usdt_krw(client)

                spot = await self._fetch_spot_balances(client)
                perp = await self._fetch_perp_balance(client)

                # 코인별 합산 (Spot + Perp 구분해서 기록)
                entries: list[tuple[str, float, str]] = []
                for item in spot:
                    entries.append((item["asset"], item["amount"], item["source"]))
                for item in perp:
                    entries.append((item["asset"], item["amount"], item["source"]))

                # USDT 가격 조회
                coins = list({e[0] for e in entries})
                prices = await _get_spot_prices_usdt(client, coins)

                for asset, amount, source in entries:
                    usdt_price = prices.get(asset, 0.0)
                    usdt_value = amount * usdt_price
                    if usdt_value < _SKIP_ZERO_THRESHOLD:
                        continue
                    balance_krw = int(usdt_value * usdt_krw)
                    asset_type = f"{asset}({source})" if source == "Perpetual" else asset
                    results.append({
                        "snapshot_date": snapshot_date.isoformat(),
                        "user": self.user,
                        "institution": INSTITUTION,
                        "asset_type": asset_type,
                        "balance_krw": balance_krw,
                    })

                logger.info(
                    "BingX 자산 조회 완료 (user=%s, 코인=%d종, USDT/KRW=%.0f)",
                    self.user, len(results), usdt_krw,
                )
        except httpx.HTTPStatusError as e:
            logger.error(
                "BingX API 오류 (user=%s): %s %s",
                self.user, e.response.status_code, e.response.text,
            )
        except Exception as e:
            logger.error("BingX 오류 (user=%s): %s", self.user, e)

        return results
