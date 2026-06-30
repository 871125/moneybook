"""
롯데카드 Open API 연동 모듈

롯데카드 오픈API 개발자센터: https://developers.lottecard.co.kr
인증: App Key + App Secret → OAuth2 Client Credentials Access Token
카드번호: 복수 카드는 쉼표로 구분 (예: "1234-5678-9012-3456,9876-5432-1098-7654")
거래 유형: 승인(카드 결제) / 취소(취소·환불)
페이지네이션: offset 기반 (pageIndex + pageSize)
"""
import logging
import time
from datetime import date

import httpx

from app.services.sync.base import BaseSyncer

logger = logging.getLogger(__name__)

INSTITUTION = "롯데카드"
BASE_URL = "https://openapi.lottecard.co.kr"

# 롯데카드 승인구분코드 → 내부 type
_TX_TYPE_MAP = {
    "1": "승인",
    "2": "취소",
    "A": "승인",
    "C": "취소",
    "0": "승인",
    "9": "취소",
    "승인": "승인",
    "취소": "취소",
}


def _parse_amount(val) -> int:
    return int(str(val).replace(",", "") or "0")


class LotteCardSyncer(BaseSyncer):
    """롯데카드 일별 카드 승인·취소 내역 수집기"""

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
                "scope": "read",
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
            "X-Api-Key": self.api_key,
            "X-Timestamp": str(int(time.time() * 1000)),
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
        page_index = 1

        while True:
            resp = await client.get(
                f"{BASE_URL}/v1/card/approvals",
                params={
                    "cardNo": card_no.replace("-", ""),
                    "startDate": date_str,
                    "endDate": date_str,
                    "pageIndex": page_index,
                    "pageSize": 100,
                },
                headers=self._auth_headers(token),
                timeout=10,
            )
            resp.raise_for_status()
            body = resp.json()

            items = body.get("approvalList", body.get("data", body.get("list", [])))
            for item in items:
                appr_dv = item.get("approvalType", item.get("apprDvCd", item.get("dvCd", "1")))
                tx_type = _TX_TYPE_MAP.get(str(appr_dv), "승인")
                amount = _parse_amount(
                    item.get("approvalAmount", item.get("apprAmt", item.get("useAmt", 0)))
                )
                if amount <= 0:
                    continue
                merchant = item.get(
                    "merchantName", item.get("mrchNm", item.get("storeName", ""))
                )
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

            total_count = int(body.get("totalCount", body.get("totCnt", len(items))))
            if page_index * 100 >= total_count:
                break
            page_index += 1

        return rows

    async def fetch_transactions(self, target_date: date) -> list[dict]:
        if not self.api_key or not self.secret:
            logger.warning("롯데카드 API 키 미설정 (user=%s)", self.user)
            return []
        if not self.card_nos:
            logger.warning("롯데카드 카드번호 미설정 (user=%s)", self.user)
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
                "롯데카드 승인내역 조회 완료 (user=%s, %s, %d건)",
                self.user, target_date, len(results),
            )
        except httpx.HTTPStatusError as e:
            logger.error(
                "롯데카드 API 오류 (user=%s): %s %s",
                self.user, e.response.status_code, e.response.text,
            )
        except Exception as e:
            logger.error("롯데카드 오류 (user=%s): %s", self.user, e)

        return results
