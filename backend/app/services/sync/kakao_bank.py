"""
카카오뱅크 Open API 연동 모듈

카카오뱅크 오픈API 개발자센터: https://developers.kakaobank.com
인증: App Key + App Secret → OAuth2 Client Credentials Access Token
계좌번호: 복수 계좌는 쉼표로 구분 (예: "3333-01-1234567,3333-02-9876543")
"""
import logging
import time
from datetime import date

import httpx

from app.services.sync.base import BaseSyncer, BaseAssetSyncer

logger = logging.getLogger(__name__)

INSTITUTION = "카카오뱅크"
BASE_URL = "https://openapi.kakaobank.com"

# 카카오뱅크 거래 유형 → 내부 type
_TX_TYPE_MAP = {
    "DEPOSIT": "입금",
    "WITHDRAWAL": "출금",
    "TRANSFER_IN": "입금",
    "TRANSFER_OUT": "출금",
    "INTEREST": "입금",
    "FEE": "출금",
    "입금": "입금",
    "출금": "출금",
}


def _parse_amount(val) -> int:
    return int(str(val).replace(",", "") or "0")


class _KakaoBankBase:
    """카카오뱅크 공통 인증 로직"""

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
                "app_key": self.api_key,
                "app_secret": self.secret,
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
        return {
            "Authorization": f"Bearer {token}",
            "App-Key": self.api_key,
            "Content-Type": "application/json; charset=utf-8",
        }


class KakaoBankTransactionSyncer(_KakaoBankBase, BaseSyncer):
    """카카오뱅크 일별 거래내역 수집기"""

    def __init__(self, user: str, api_key: str, secret: str = "", account: str = ""):
        _KakaoBankBase.__init__(self, api_key, secret)
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
        # 카카오뱅크는 cursor 기반 페이지네이션
        cursor: str | None = None

        while True:
            params: dict = {
                "account_number": account.replace("-", ""),
                "from_date": date_str,
                "to_date": date_str,
                "limit": 100,
            }
            if cursor:
                params["cursor"] = cursor

            resp = await client.get(
                f"{BASE_URL}/v2/account/transaction-list",
                params=params,
                headers=self._auth_headers(token),
                timeout=10,
            )
            resp.raise_for_status()
            body = resp.json()

            for item in body.get("transactions", body.get("data", [])):
                tx_type_raw = item.get("transaction_type", item.get("tranType", "출금"))
                tx_type = _TX_TYPE_MAP.get(tx_type_raw, "출금")
                amount = _parse_amount(item.get("amount", item.get("tranAmt", 0)))
                if amount <= 0:
                    continue
                desc = item.get("description", item.get("memo", item.get("tranMemo", "")))
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

            # cursor 기반 다음 페이지
            next_cursor = body.get("next_cursor", body.get("cursor", {}).get("next"))
            if not next_cursor:
                break
            cursor = next_cursor

        return rows

    async def fetch_transactions(self, target_date: date) -> list[dict]:
        if not self.api_key or not self.secret:
            logger.warning("카카오뱅크 API 키 미설정 (user=%s)", self.user)
            return []
        if not self.accounts:
            logger.warning("카카오뱅크 계좌번호 미설정 (user=%s)", self.user)
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
                "카카오뱅크 거래내역 조회 완료 (user=%s, %s, %d건)",
                self.user, target_date, len(results),
            )
        except httpx.HTTPStatusError as e:
            logger.error(
                "카카오뱅크 거래내역 API 오류 (user=%s): %s %s",
                self.user, e.response.status_code, e.response.text,
            )
        except Exception as e:
            logger.error("카카오뱅크 거래내역 오류 (user=%s): %s", self.user, e)

        return results


class KakaoBankAssetSyncer(_KakaoBankBase, BaseAssetSyncer):
    """카카오뱅크 계좌 잔고 수집기"""

    def __init__(self, user: str, api_key: str, secret: str = "", account: str = ""):
        _KakaoBankBase.__init__(self, api_key, secret)
        BaseAssetSyncer.__init__(self, user, api_key, secret)
        self.accounts: list[str] = [a.strip() for a in account.split(",") if a.strip()]

    async def _fetch_balance(
        self, client: httpx.AsyncClient, token: str, account: str
    ) -> tuple[int, str]:
        """(잔액, 계좌유형) 반환"""
        resp = await client.get(
            f"{BASE_URL}/v2/account/balance",
            params={"account_number": account.replace("-", "")},
            headers=self._auth_headers(token),
            timeout=10,
        )
        resp.raise_for_status()
        body = resp.json()
        output = body.get("data", body.get("output", {}))
        balance = _parse_amount(
            output.get("balance", output.get("available_balance", output.get("blncAmt", 0)))
        )
        # 계좌 유형 (입출금, 저축, 모임통장 등)
        acct_type_raw = output.get("account_type", output.get("acntTyp", ""))
        asset_type = {
            "CHECKING": "현금",
            "SAVINGS": "저축",
            "GROUP": "모임통장",
        }.get(acct_type_raw, "현금")
        return balance, asset_type

    async def fetch_assets(self, snapshot_date: date) -> list[dict]:
        if not self.api_key or not self.secret:
            logger.warning("카카오뱅크 API 키 미설정 (user=%s)", self.user)
            return []
        if not self.accounts:
            logger.warning("카카오뱅크 계좌번호 미설정 (user=%s)", self.user)
            return []

        results: list[dict] = []
        try:
            async with httpx.AsyncClient() as client:
                token = await self._get_token(client)
                for account in self.accounts:
                    balance, asset_type = await self._fetch_balance(client, token, account)
                    if balance > 0:
                        results.append({
                            "snapshot_date": snapshot_date.isoformat(),
                            "user": self.user,
                            "institution": INSTITUTION,
                            "asset_type": asset_type,
                            "balance_krw": balance,
                        })
            logger.info(
                "카카오뱅크 잔고 조회 완료 (user=%s, 계좌=%d개, 항목=%d건)",
                self.user, len(self.accounts), len(results),
            )
        except httpx.HTTPStatusError as e:
            logger.error(
                "카카오뱅크 잔고 API 오류 (user=%s): %s %s",
                self.user, e.response.status_code, e.response.text,
            )
        except Exception as e:
            logger.error("카카오뱅크 잔고 오류 (user=%s): %s", self.user, e)

        return results
