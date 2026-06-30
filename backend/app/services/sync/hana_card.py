"""
하나카드 Open API 연동 모듈

하나카드 오픈API 개발자센터: https://developers.hanacard.co.kr
인증: App Key + App Secret → OAuth2 Client Credentials Access Token
     요청 시 HMAC-SHA256 서명 헤더 추가 (하나은행과 동일 방식)
카드번호: 복수 카드는 쉼표로 구분 (예: "1234-5678-9012-3456,9876-5432-1098-7654")
거래 유형: 승인(카드 결제) / 취소(취소·환불)
"""
import hashlib
import hmac
import logging
import time
from datetime import date

import httpx

from app.services.sync.base import BaseSyncer

logger = logging.getLogger(__name__)

INSTITUTION = "하나카드"
BASE_URL = "https://openapi.hanacard.co.kr"

# 하나카드 승인구분코드 → 내부 type
_TX_TYPE_MAP = {
    "1": "승인",
    "2": "취소",
    "A": "승인",
    "C": "취소",
    "00": "승인",
    "01": "취소",
    "승인": "승인",
    "취소": "취소",
}


def _parse_amount(val) -> int:
    return int(str(val).replace(",", "") or "0")


def _hmac_signature(secret: str, timestamp: str) -> str:
    """HMAC-SHA256(secret + timestamp) → hex digest (하나은행 계열 공통)"""
    message = (secret + timestamp).encode("utf-8")
    return hmac.new(secret.encode("utf-8"), message, hashlib.sha256).hexdigest()


class HanaCardSyncer(BaseSyncer):
    """하나카드 일별 카드 승인·취소 내역 수집기"""

    def __init__(self, user: str, api_key: str, secret: str = "", card_no: str = ""):
        super().__init__(user, api_key, secret)
        self.card_nos: list[str] = [c.strip() for c in card_no.split(",") if c.strip()]
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

    async def _fetch_approvals_for_card(
        self,
        client: httpx.AsyncClient,
        token: str,
        card_no: str,
        target_date: date,
    ) -> list[dict]:
        rows: list[dict] = []
        date_str = target_date.strftime("%Y%m%d")
        page_no = 1

        while True:
            resp = await client.post(
                f"{BASE_URL}/v2/card/approvalList",
                json={
                    "dataHeader": {"apikey": self.api_key},
                    "dataBody": {
                        "cardNo": card_no.replace("-", ""),
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
            items = data_body.get("apprList", data_body.get("approvalList", data_body.get("data", [])))
            for item in items:
                appr_dv = item.get("apprDvCd", item.get("approvalType", item.get("dvCd", "1")))
                tx_type = _TX_TYPE_MAP.get(str(appr_dv), "승인")
                amount = _parse_amount(
                    item.get("apprAmt", item.get("useAmt", item.get("amount", 0)))
                )
                if amount <= 0:
                    continue
                merchant = item.get("mrchNm", item.get("merchantName", item.get("storeName", "")))
                rows.append({
                    "date": target_date.isoformat(),
                    "user": self.user,
                    "institution": INSTITUTION,
                    "type": tx_type,
                    "amount": amount,
                    "description": str(merchant).strip(),
                    "tag_person": "",
                    "tag_category": "",
                })

            total_pages = int(data_body.get("totalPageCnt", data_body.get("totPageCnt", 1)))
            if page_no >= total_pages:
                break
            page_no += 1

        return rows

    async def fetch_transactions(self, target_date: date) -> list[dict]:
        if not self.api_key or not self.secret:
            logger.warning("하나카드 API 키 미설정 (user=%s)", self.user)
            return []
        if not self.card_nos:
            logger.warning("하나카드 카드번호 미설정 (user=%s)", self.user)
            return []

        results: list[dict] = []
        try:
            async with httpx.AsyncClient() as client:
                token = await self._get_token(client)
                for card_no in self.card_nos:
                    rows = await self._fetch_approvals_for_card(
                        client, token, card_no, target_date
                    )
                    results.extend(rows)
            logger.info(
                "하나카드 승인내역 조회 완료 (user=%s, %s, %d건)",
                self.user, target_date, len(results),
            )
        except httpx.HTTPStatusError as e:
            logger.error(
                "하나카드 API 오류 (user=%s): %s %s",
                self.user, e.response.status_code, e.response.text,
            )
        except Exception as e:
            logger.error("하나카드 오류 (user=%s): %s", self.user, e)

        return results
