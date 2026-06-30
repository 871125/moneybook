"""
Upbit Open API 연동 모듈

Upbit API 문서: https://docs.upbit.com
인증: JWT(HS256) — access_key + nonce → Authorization: Bearer {token}
     쿼리 파라미터 있을 시 SHA512(query_string) → query_hash 포함
자산 범위: KRW·BTC·USDT 마켓 보유 코인 전체 → KRW 평가금액
특징: 국내 거래소라 KRW 마켓 직접 조회 가능 (환율 불필요)
"""
import base64
import hashlib
import hmac
import json
import logging
import uuid
from datetime import date
from urllib.parse import urlencode

import httpx

from app.services.sync.base import BaseAssetSyncer

logger = logging.getLogger(__name__)

INSTITUTION = "Upbit"
BASE_URL = "https://api.upbit.com"

_SKIP_KRW_THRESHOLD = 100   # 100원 미만 먼지 잔고 스킵


# ── JWT 수동 구현 (PyJWT 의존성 없이) ───────────────────────────────
def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _make_jwt(access_key: str, secret_key: str, extra: dict | None = None) -> str:
    header = _b64url(json.dumps({"alg": "HS256", "typ": "JWT"}, separators=(",", ":")).encode())
    payload_dict = {"access_key": access_key, "nonce": str(uuid.uuid4())}
    if extra:
        payload_dict.update(extra)
    payload = _b64url(json.dumps(payload_dict, separators=(",", ":")).encode())
    signing_input = f"{header}.{payload}".encode()
    sig = hmac.new(secret_key.encode(), signing_input, hashlib.sha256).digest()
    return f"{header}.{payload}.{_b64url(sig)}"


def _make_query_hash(params: dict) -> dict:
    """쿼리 파라미터가 있는 요청에 필요한 query_hash 생성"""
    query_string = urlencode(params, doseq=True).encode()
    query_hash = hashlib.sha512(query_string).hexdigest()
    return {"query_hash": query_hash, "query_hash_alg": "SHA512"}


# ── 가격 조회 ─────────────────────────────────────────────────────────
async def _get_krw_prices(
    client: httpx.AsyncClient, markets: list[str]
) -> dict[str, float]:
    """KRW 마켓 티커 일괄 조회 → {마켓코드: 현재가}"""
    if not markets:
        return {}
    try:
        resp = await client.get(
            f"{BASE_URL}/v1/ticker",
            params={"markets": ",".join(markets)},
            timeout=10,
        )
        resp.raise_for_status()
        return {item["market"]: float(item["trade_price"]) for item in resp.json()}
    except Exception as e:
        logger.warning("Upbit 가격 조회 실패: %s", e)
        return {}


class UpbitAssetSyncer(BaseAssetSyncer):
    """Upbit 보유 자산 수집기 (KRW·BTC·USDT 마켓 → KRW 환산)"""

    def _auth_header(self, params: dict | None = None) -> dict:
        extra = _make_query_hash(params) if params else None
        token = _make_jwt(self.api_key, self.secret, extra)
        return {"Authorization": f"Bearer {token}"}

    async def _fetch_accounts(self, client: httpx.AsyncClient) -> list[dict]:
        """전체 계좌 잔고 조회"""
        resp = await client.get(
            f"{BASE_URL}/v1/accounts",
            headers=self._auth_header(),
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json()

    async def fetch_assets(self, snapshot_date: date) -> list[dict]:
        if not self.api_key or not self.secret:
            logger.warning("Upbit API 키 미설정 (user=%s)", self.user)
            return []

        results: list[dict] = []
        try:
            async with httpx.AsyncClient() as client:
                accounts = await self._fetch_accounts(client)

                # 1) KRW 잔고 직접 기록
                krw_balance = 0.0
                non_krw: list[dict] = []
                for acc in accounts:
                    currency = acc["currency"]
                    total = float(acc["balance"]) + float(acc["locked"])
                    if total <= 0:
                        continue
                    if currency == "KRW":
                        krw_balance += total
                    else:
                        non_krw.append({"currency": currency, "amount": total, "unit": acc.get("unit_currency", "KRW")})

                if krw_balance >= _SKIP_KRW_THRESHOLD:
                    results.append({
                        "snapshot_date": snapshot_date.isoformat(),
                        "user": self.user,
                        "institution": INSTITUTION,
                        "asset_type": "KRW",
                        "balance_krw": int(krw_balance),
                    })

                # 2) 코인별 KRW 평가금액 계산
                # 마켓별로 분류
                krw_markets = [f"KRW-{a['currency']}" for a in non_krw if a["unit"] == "KRW"]
                btc_markets = [f"BTC-{a['currency']}" for a in non_krw if a["unit"] == "BTC"]
                usdt_markets = [f"USDT-{a['currency']}" for a in non_krw if a["unit"] == "USDT"]

                # 가격 일괄 조회
                all_markets = list(set(krw_markets + btc_markets + usdt_markets))
                # BTC·USDT/KRW 기준가도 포함
                if btc_markets:
                    all_markets.append("KRW-BTC")
                if usdt_markets:
                    all_markets.append("KRW-USDT")

                prices = await _get_krw_prices(client, all_markets)
                btc_krw = prices.get("KRW-BTC", 0.0)
                usdt_krw = prices.get("KRW-USDT", 1350.0)

                for acc in non_krw:
                    currency = acc["currency"]
                    amount = acc["amount"]
                    unit = acc["unit"]

                    if unit == "KRW":
                        coin_krw = prices.get(f"KRW-{currency}", 0.0)
                    elif unit == "BTC":
                        coin_btc = prices.get(f"BTC-{currency}", 0.0)
                        coin_krw = coin_btc * btc_krw
                    elif unit == "USDT":
                        coin_usdt = prices.get(f"USDT-{currency}", 0.0)
                        coin_krw = coin_usdt * usdt_krw
                    else:
                        continue

                    balance_krw = int(amount * coin_krw)
                    if balance_krw < _SKIP_KRW_THRESHOLD:
                        continue

                    results.append({
                        "snapshot_date": snapshot_date.isoformat(),
                        "user": self.user,
                        "institution": INSTITUTION,
                        "asset_type": currency,
                        "balance_krw": balance_krw,
                    })

                logger.info(
                    "Upbit 자산 조회 완료 (user=%s, 코인=%d종)",
                    self.user, len(results),
                )
        except httpx.HTTPStatusError as e:
            logger.error(
                "Upbit API 오류 (user=%s): %s %s",
                self.user, e.response.status_code, e.response.text,
            )
        except Exception as e:
            logger.error("Upbit 오류 (user=%s): %s", self.user, e)

        return results
