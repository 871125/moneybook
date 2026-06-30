"""
하나은행 Open API 연동 모듈

하나은행 오픈API 개발자센터: https://developer.kebhana.com
인증: App Key + App Secret → OAuth2 Access Token
     요청 시 HMAC-SHA256 서명 헤더 추가 (apiSecret + timestamp)
계좌번호: 복수 계좌는 쉼표로 구분 (예: "123-456789-01234,123-111111-00000")
"""
import hashlib
import hmac
import logging
import time
from datetime import date

import httpx

from app.services.sync.base import BaseSyncer, BaseAssetSyncer

logger = logging.getLogger(__name__)

INSTITUTION = "하나은행"
BASE_URL = "https://openapi.kebhana.com"

# 하나은행 거래구분코드 → 내부 type
_TX_TYPE_MAP = {
    "1": "입금",
    "2": "출금",
    "D": "입금",
    "C": "출금",
    "IN": "입금",
    "OUT": "출금",
    "입금": "입금",
    "출금": "출금",
}


def _parse_amount(val) -> int:
    return int(str(val).replace(",", "") or "0")


def _hmac_signature(secret: str, timestamp: str) -> str:
    """HMAC-SHA256(secret + timestamp) → hex digest"""
    message = (secret + timestamp).encode("utf-8")
    return hmac.new(secret.encode("utf-8"), message, hashlib.sha256).hexdigest()


class _HanaBankBase:
    """하나은행 공통 인증 로직"""

    def __init__(self, api_key: str, secret: str):
        self.api_key = api_key
        self.secret = secret
        self._token: str | None = None
        self._token_expires_at: float = 0.0

    async def _get_token(self, client: httpx.AsyncClient) -> str:
        if self._token and time.time() < self._token_expires_at - 60:
            return self._token

        resp = await client.post(
            f"{BASE_URL}/oauth2/token",
            data={
                "grant_type": "client_credentials",
                "client_id": self.api_key,
                "client_secret": self.secret,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=10,
        )
        resp.raise_for_status()
        body = resp.json()
        self._token = body["access_token"]
        self._token_expires_at = time.time() + int(body.get("expires_in", 86400))
        return self._token

    def _auth_headers(self, token: str) -> dict:
        timestamp = str(int(time.time() * 1000))
        signature = _hmac_signature(self.secret, timestamp)
        return {
            "Authorization": f"Bearer {token}",
            "apiKey": self.api_key,
            "timestamp": timestamp,
            "signature": signature,
            "Content-Type": "application/json; charset=utf-8",
        }


class HanaBankTransactionSyncer(_HanaBankBase, BaseSyncer):
    """하나은행 일별 거래내역 수집기"""

    def __init__(self, user: str, api_key: str, secret: str = "", account: str = ""):
        _HanaBankBase.__init__(self, api_key, secret)
        BaseSyncer.__init__(self, user, api_key, secret)
        self.accounts: list[str] = [a.strip() for a in account.split(",") if a.strip()]

    async def _fetch_transactions_for_account(
        self,
        client: httpx.AsyncClient,
        token: str,
        account: str,
        target_date: date,
    ) -> list[dict]:
        rows: list[dict] = []
        date_str = target_date.strftime("%Y%m%d")
        page_no = 1

        while True:
            resp = await client.post(
                f"{BASE_URL}/v2/trans/account/transactionList",
                json={
                    "dataHeader": {"apikey": self.api_key},
                    "dataBody": {
                        "acctNo": account.replace("-", ""),
                        "inqStrDt": date_str,
                        "inqEndDt": date_str,
                        "pageNo": str(page_no),
                        "pageRow": "100",
                    },
                },
                headers=self._auth_headers(token),
                timeout=10,
            )
            resp.raise_for_status()
            body = resp.json()

            data_body = body.get("dataBody", body)
            items = data_body.get("resTranList", data_body.get("tranList", []))

            for item in items:
                dv_cd = item.get("tranDvCd", item.get("dbtCrdt", item.get("inoutDvCd", "")))
                tx_type = _TX_TYPE_MAP.get(str(dv_cd), "출금")
                amount = _parse_amount(
                    item.get("tranAmt", item.get("trnsAmt", item.get("amount", 0)))
                )
                if amount <= 0:
                    continue
                desc = item.get("tranRmk", item.get("memo", item.get("briefs", "")))
                rows.append({
                    "date": target_date.isoformat(),
                    "user": self.user,
                    "institution": INSTITUTION,
                    "type": tx_type,
                    "amount": amount,
                    "description": str(desc).strip(),
                    "tag_person": "",
                    "tag_category": "",
                })

            # 다음 페이지 여부
            total_page = int(data_body.get("totalPageCnt", data_body.get("totPageCnt", 1)))
            if page_no >= total_page:
                break
            page_no += 1

        return rows

    async def fetch_transactions(self, target_date: date) -> list[dict]:
        if not self.api_key or not self.secret:
            logger.warning("하나은행 API 키 미설정 (user=%s)", self.user)
            return []
        if not self.accounts:
            logger.warning("하나은행 계좌번호 미설정 (user=%s)", self.user)
            return []

        results: list[dict] = []
        try:
            async with httpx.AsyncClient() as client:
                token = await self._get_token(client)
                for account in self.accounts:
                    rows = await self._fetch_transactions_for_account(
                        client, token, account, target_date
                    )
                    results.extend(rows)
            logger.info(
                "하나은행 거래내역 조회 완료 (user=%s, %s, %d건)",
                self.user, target_date, len(results),
            )
        except httpx.HTTPStatusError as e:
            logger.error(
                "하나은행 거래내역 API 오류 (user=%s): %s %s",
                self.user, e.response.status_code, e.response.text,
            )
        except Exception as e:
            logger.error("하나은행 거래내역 오류 (user=%s): %s", self.user, e)

        return results


class HanaBankAssetSyncer(_HanaBankBase, BaseAssetSyncer):
    """하나은행 계좌 잔고 수집기"""

    def __init__(self, user: str, api_key: str, secret: str = "", account: str = ""):
        _HanaBankBase.__init__(self, api_key, secret)
        BaseAssetSyncer.__init__(self, user, api_key, secret)
        self.accounts: list[str] = [a.strip() for a in account.split(",") if a.strip()]

    async def _fetch_balance(
        self, client: httpx.AsyncClient, token: str, account: str
    ) -> int:
        resp = await client.post(
            f"{BASE_URL}/v2/trans/account/inquireBalance",
            json={
                "dataHeader": {"apikey": self.api_key},
                "dataBody": {"acctNo": account.replace("-", "")},
            },
            headers=self._auth_headers(token),
            timeout=10,
        )
        resp.raise_for_status()
        body = resp.json()
        data_body = body.get("dataBody", body)
        amt_str = (
            data_body.get("acntBlncAmt")
            or data_body.get("blncAmt")
            or data_body.get("aftBlncAmt", "0")
        )
        return _parse_amount(amt_str)

    async def fetch_assets(self, snapshot_date: date) -> list[dict]:
        if not self.api_key or not self.secret:
            logger.warning("하나은행 API 키 미설정 (user=%s)", self.user)
            return []
        if not self.accounts:
            logger.warning("하나은행 계좌번호 미설정 (user=%s)", self.user)
            return []

        results: list[dict] = []
        try:
            async with httpx.AsyncClient() as client:
                token = await self._get_token(client)
                for account in self.accounts:
                    balance = await self._fetch_balance(client, token, account)
                    if balance > 0:
                        results.append({
                            "snapshot_date": snapshot_date.isoformat(),
                            "user": self.user,
                            "institution": INSTITUTION,
                            "asset_type": "현금",
                            "balance_krw": balance,
                        })
            logger.info(
                "하나은행 잔고 조회 완료 (user=%s, 계좌=%d개, 항목=%d건)",
                self.user, len(self.accounts), len(results),
            )
        except httpx.HTTPStatusError as e:
            logger.error(
                "하나은행 잔고 API 오류 (user=%s): %s %s",
                self.user, e.response.status_code, e.response.text,
            )
        except Exception as e:
            logger.error("하나은행 잔고 오류 (user=%s): %s", self.user, e)

        return results
