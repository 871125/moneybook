"""
MG새마을금고 Open API 연동 모듈

MG새마을금고 오픈API: https://openapi.mgcredit.co.kr
인증: App Key + App Secret → OAuth2 Client Credentials Access Token
금고코드(branch): 거래 새마을금고 지점 4자리 코드 (예: "0001")
계좌번호: 복수 계좌는 쉼표로 구분 (예: "1234-56-789012,1234-56-000001")
"""
import logging
import time
from datetime import date

import httpx

from app.services.sync.base import BaseSyncer, BaseAssetSyncer

logger = logging.getLogger(__name__)

INSTITUTION = "새마을금고"
BASE_URL = "https://openapi.mgcredit.co.kr"

# 새마을금고 거래구분 → 내부 type
_TX_TYPE_MAP = {
    "1": "입금",
    "2": "출금",
    "I": "입금",
    "O": "출금",
    "IN": "입금",
    "OUT": "출금",
    "입금": "입금",
    "출금": "출금",
}

# 새마을금고 예금 상품 유형 → 내부 asset_type
_PRODUCT_TYPE_MAP = {
    "10": "자유출금예금",    # 보통예금 계열
    "20": "정기예탁금",     # 정기예금 계열
    "30": "자유적금",
    "40": "출자금",         # 새마을금고 특유의 출자금
    "50": "신탁",
    "60": "청약저축",
}


def _parse_amount(val) -> int:
    return int(str(val).replace(",", "") or "0")


class _SaemaeulBase:
    """새마을금고 공통 인증 로직"""

    def __init__(self, api_key: str, secret: str, branch: str):
        self.api_key = api_key
        self.secret = secret
        self.branch = branch          # 금고코드 4자리
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
            "apiKey": self.api_key,
            "branchCode": self.branch,
            "Content-Type": "application/json; charset=utf-8",
        }


class SaemaeulTransactionSyncer(_SaemaeulBase, BaseSyncer):
    """새마을금고 일별 거래내역 수집기"""

    def __init__(
        self, user: str, api_key: str, secret: str = "",
        branch: str = "", account: str = "",
    ):
        _SaemaeulBase.__init__(self, api_key, secret, branch)
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
            resp = await client.get(
                f"{BASE_URL}/v1/account/transaction-history",
                params={
                    "branchCode": self.branch,
                    "accountNo": account.replace("-", ""),
                    "fromDate": date_str,
                    "toDate": date_str,
                    "pageNo": page_no,
                    "pageSize": 100,
                },
                headers=self._auth_headers(token),
                timeout=10,
            )
            resp.raise_for_status()
            body = resp.json()

            items = body.get("tranList", body.get("transactions", body.get("data", [])))
            for item in items:
                dv_cd = item.get("inoutDvCd", item.get("tranDvCd", item.get("type", "")))
                tx_type = _TX_TYPE_MAP.get(str(dv_cd), "출금")
                amount = _parse_amount(
                    item.get("tranAmt", item.get("amount", item.get("trnsAmt", 0)))
                )
                if amount <= 0:
                    continue
                desc = item.get("tranRmk", item.get("memo", item.get("description", "")))
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

            total_pages = int(body.get("totalPage", body.get("totalPageCnt", 1)))
            if page_no >= total_pages:
                break
            page_no += 1

        return rows

    async def fetch_transactions(self, target_date: date) -> list[dict]:
        if not self.api_key or not self.secret:
            logger.warning("새마을금고 API 키 미설정 (user=%s)", self.user)
            return []
        if not self.branch:
            logger.warning("새마을금고 금고코드 미설정 (user=%s)", self.user)
            return []
        if not self.accounts:
            logger.warning("새마을금고 계좌번호 미설정 (user=%s)", self.user)
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
                "새마을금고 거래내역 조회 완료 (user=%s, %s, %d건)",
                self.user, target_date, len(results),
            )
        except httpx.HTTPStatusError as e:
            logger.error(
                "새마을금고 거래내역 API 오류 (user=%s): %s %s",
                self.user, e.response.status_code, e.response.text,
            )
        except Exception as e:
            logger.error("새마을금고 거래내역 오류 (user=%s): %s", self.user, e)

        return results


class SaemaeulAssetSyncer(_SaemaeulBase, BaseAssetSyncer):
    """새마을금고 계좌 잔고 수집기 (자유출금·정기예탁·출자금 포함)"""

    def __init__(
        self, user: str, api_key: str, secret: str = "",
        branch: str = "", account: str = "",
    ):
        _SaemaeulBase.__init__(self, api_key, secret, branch)
        BaseAssetSyncer.__init__(self, user, api_key, secret)
        self.accounts: list[str] = [a.strip() for a in account.split(",") if a.strip()]

    async def _fetch_balance(
        self, client: httpx.AsyncClient, token: str, account: str
    ) -> tuple[int, str]:
        """(잔액, asset_type) 반환"""
        resp = await client.get(
            f"{BASE_URL}/v1/account/balance",
            params={
                "branchCode": self.branch,
                "accountNo": account.replace("-", ""),
            },
            headers=self._auth_headers(token),
            timeout=10,
        )
        resp.raise_for_status()
        body = resp.json()
        output = body.get("data", body.get("output", body))
        balance = _parse_amount(
            output.get("blncAmt", output.get("balance", output.get("acntBlncAmt", 0)))
        )
        prd_tp = str(output.get("prdTypCd", output.get("productType", "10")))
        asset_type = _PRODUCT_TYPE_MAP.get(prd_tp, "자유출금예금")
        return balance, asset_type

    async def fetch_assets(self, snapshot_date: date) -> list[dict]:
        if not self.api_key or not self.secret:
            logger.warning("새마을금고 API 키 미설정 (user=%s)", self.user)
            return []
        if not self.branch:
            logger.warning("새마을금고 금고코드 미설정 (user=%s)", self.user)
            return []
        if not self.accounts:
            logger.warning("새마을금고 계좌번호 미설정 (user=%s)", self.user)
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
                "새마을금고 잔고 조회 완료 (user=%s, 계좌=%d개, 항목=%d건)",
                self.user, len(self.accounts), len(results),
            )
        except httpx.HTTPStatusError as e:
            logger.error(
                "새마을금고 잔고 API 오류 (user=%s): %s %s",
                self.user, e.response.status_code, e.response.text,
            )
        except Exception as e:
            logger.error("새마을금고 잔고 오류 (user=%s): %s", self.user, e)

        return results
