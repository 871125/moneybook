"""
우리은행 Open API 연동 모듈

우리은행 오픈API 개발자센터: https://developer.wooribank.com
인증: App Key + App Secret → OAuth2 Client Credentials Access Token
계좌번호: 복수 계좌는 쉼표로 구분 (예: "1002-123-456789,1002-987-654321")
"""
import logging
import time
from datetime import date

import httpx

from app.services.sync.base import BaseSyncer, BaseAssetSyncer

logger = logging.getLogger(__name__)

INSTITUTION = "우리은행"
BASE_URL = "https://openapi.wooribank.com"

# 우리은행 거래구분 코드 → 내부 type
_TX_TYPE_MAP = {
    "1": "입금",
    "2": "출금",
    "11": "입금",   # 타행입금
    "12": "출금",   # 타행출금
    "21": "입금",   # 현금입금
    "22": "출금",   # 현금출금
    "31": "입금",   # 이자
    "41": "출금",   # 수수료
}


def _parse_amount(val) -> int:
    return int(str(val).replace(",", "") or "0")


class _WooriBankBase:
    """우리은행 공통 인증 로직"""

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
                "appkey": self.api_key,
                "appsecretkey": self.secret,
                "scope": "oob",
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
            "appkey": self.api_key,
            "appsecretkey": self.secret,
            "Content-Type": "application/json; charset=utf-8",
        }


class WooriBankTransactionSyncer(_WooriBankBase, BaseSyncer):
    """우리은행 일별 거래내역 수집기"""

    def __init__(self, user: str, api_key: str, secret: str = "", account: str = ""):
        _WooriBankBase.__init__(self, api_key, secret)
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
        next_page_yn = "N"
        tran_no = ""

        while True:
            params: dict = {
                "acno": account.replace("-", ""),
                "inqStrDt": date_str,
                "inqEndDt": date_str,
                "trnsDsnc": "A",        # 전체(입금+출금)
                "nextPageYn": next_page_yn,
                "tranNo": tran_no,
                "pwdChkYn": "N",
            }
            resp = await client.get(
                f"{BASE_URL}/v3/trans/acno/inquire-transaction-list",
                params=params,
                headers=self._auth_headers(token),
                timeout=10,
            )
            resp.raise_for_status()
            body = resp.json()

            items = body.get("output", body.get("tranList", []))
            for item in items:
                dbit_crdt = item.get("dbtCrdt", item.get("tranDsnc", ""))
                tx_type = "입금" if dbit_crdt in ("1", "C", "입금") else "출금"
                amount = _parse_amount(item.get("tranAmt", item.get("trnsAmt", 0)))
                if amount <= 0:
                    continue
                desc = item.get("tranRmrk", item.get("briefs", item.get("memo", "")))
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
            if body.get("nextPageYn", "N") != "Y":
                break
            next_page_yn = "Y"
            tran_no = body.get("tranNo", "")

        return rows

    async def fetch_transactions(self, target_date: date) -> list[dict]:
        if not self.api_key or not self.secret:
            logger.warning("우리은행 API 키 미설정 (user=%s)", self.user)
            return []
        if not self.accounts:
            logger.warning("우리은행 계좌번호 미설정 (user=%s)", self.user)
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
                "우리은행 거래내역 조회 완료 (user=%s, %s, %d건)",
                self.user, target_date, len(results),
            )
        except httpx.HTTPStatusError as e:
            logger.error(
                "우리은행 거래내역 API 오류 (user=%s): %s %s",
                self.user, e.response.status_code, e.response.text,
            )
        except Exception as e:
            logger.error("우리은행 거래내역 오류 (user=%s): %s", self.user, e)

        return results


class WooriBankAssetSyncer(_WooriBankBase, BaseAssetSyncer):
    """우리은행 계좌 잔고 수집기"""

    def __init__(self, user: str, api_key: str, secret: str = "", account: str = ""):
        _WooriBankBase.__init__(self, api_key, secret)
        BaseAssetSyncer.__init__(self, user, api_key, secret)
        self.accounts: list[str] = [a.strip() for a in account.split(",") if a.strip()]

    async def _fetch_balance(
        self, client: httpx.AsyncClient, token: str, account: str
    ) -> int:
        resp = await client.get(
            f"{BASE_URL}/v3/account/acno/inquire-balance",
            params={"acno": account.replace("-", ""), "pwdChkYn": "N"},
            headers=self._auth_headers(token),
            timeout=10,
        )
        resp.raise_for_status()
        body = resp.json()
        output = body.get("output", body.get("Output1", {}))
        amt_str = (
            output.get("acntBlncAmt")
            or output.get("aftBlncAmt")
            or output.get("blncAmt", "0")
        )
        return _parse_amount(amt_str)

    async def fetch_assets(self, snapshot_date: date) -> list[dict]:
        if not self.api_key or not self.secret:
            logger.warning("우리은행 API 키 미설정 (user=%s)", self.user)
            return []
        if not self.accounts:
            logger.warning("우리은행 계좌번호 미설정 (user=%s)", self.user)
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
                "우리은행 잔고 조회 완료 (user=%s, 계좌=%d개, 항목=%d건)",
                self.user, len(self.accounts), len(results),
            )
        except httpx.HTTPStatusError as e:
            logger.error(
                "우리은행 잔고 API 오류 (user=%s): %s %s",
                self.user, e.response.status_code, e.response.text,
            )
        except Exception as e:
            logger.error("우리은행 잔고 오류 (user=%s): %s", self.user, e)

        return results
