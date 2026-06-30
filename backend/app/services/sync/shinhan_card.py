"""
신한카드 Open API 연동 모듈

신한카드 오픈API 개발자센터: https://developers.shinhancard.com
인증: App Key + App Secret → OAuth2 Client Credentials Access Token
     카드번호 전송 시 RSA 공개키로 암호화 (신한카드 특유의 보안 방식)
카드번호: 복수 카드는 쉼표로 구분 (예: "1234-5678-9012-3456,9876-5432-1098-7654")
거래 유형: 승인(카드 결제) / 취소(취소·환불)
"""
import base64
import logging
import time
from datetime import date

import httpx

from app.services.sync.base import BaseSyncer

logger = logging.getLogger(__name__)

INSTITUTION = "신한카드"
BASE_URL = "https://openapi.shinhancard.com"

# 신한카드 승인구분코드 → 내부 type
_TX_TYPE_MAP = {
    "1": "승인",
    "2": "취소",
    "0": "승인",
    "9": "취소",
    "N": "승인",   # 일반승인
    "C": "취소",   # 취소
    "R": "취소",   # 환불
    "승인": "승인",
    "취소": "취소",
}


def _parse_amount(val) -> int:
    return int(str(val).replace(",", "") or "0")


def _encrypt_card_no(card_no: str, pub_key_b64: str) -> str:
    """
    신한카드 RSA 공개키로 카드번호 암호화.
    pub_key_b64: 신한카드 API에서 발급받은 Base64 인코딩 RSA 공개키.
    cryptography 패키지가 없으면 평문을 그대로 반환(개발/테스트용).
    """
    try:
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import padding

        pub_key_der = base64.b64decode(pub_key_b64)
        public_key = serialization.load_der_public_key(pub_key_der)
        encrypted = public_key.encrypt(
            card_no.replace("-", "").encode("utf-8"),
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None,
            ),
        )
        return base64.b64encode(encrypted).decode("utf-8")
    except ImportError:
        # cryptography 미설치 시 평문 전송 (테스트 환경용)
        logger.warning("cryptography 패키지 미설치 — 카드번호 평문 전송 (개발 모드)")
        return card_no.replace("-", "")


class ShinhanCardSyncer(BaseSyncer):
    """신한카드 일별 카드 승인·취소 내역 수집기"""

    def __init__(self, user: str, api_key: str, secret: str = "", card_no: str = ""):
        super().__init__(user, api_key, secret)
        self.card_nos: list[str] = [c.strip() for c in card_no.split(",") if c.strip()]
        self._token: str | None = None
        self._token_expires_at: float = 0.0
        self._pub_key_b64: str = ""   # 신한카드 RSA 공개키 (토큰 발급 시 함께 수신)

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
        # 신한카드는 토큰 응답에 RSA 공개키를 함께 제공
        self._pub_key_b64 = body.get("rsa_public_key", body.get("publicKey", ""))
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

        # 카드번호 암호화 (신한카드 보안 정책)
        encrypted_card_no = (
            _encrypt_card_no(card_no, self._pub_key_b64)
            if self._pub_key_b64
            else card_no.replace("-", "")
        )

        next_key = ""
        while True:
            params: dict = {
                "cardNo": encrypted_card_no,
                "inqStrDt": date_str,
                "inqEndDt": date_str,
                "pageRowCnt": "100",
            }
            if next_key:
                params["nextKey"] = next_key

            resp = await client.get(
                f"{BASE_URL}/v1/card/approval/list",
                params=params,
                headers=self._auth_headers(token),
                timeout=10,
            )
            resp.raise_for_status()
            body = resp.json()

            items = body.get("dataBody", body.get("output", body.get("data", [])))
            if isinstance(items, dict):
                items = items.get("apprList", items.get("list", []))

            for item in items:
                appr_dv = item.get("apprDvCd", item.get("approvalType", item.get("clssCd", "N")))
                tx_type = _TX_TYPE_MAP.get(str(appr_dv), "승인")
                amount = _parse_amount(
                    item.get("apprAmt", item.get("useAmt", item.get("amount", 0)))
                )
                if amount <= 0:
                    continue
                merchant = item.get("mrchNm", item.get("merchantName", item.get("usePlcNm", "")))
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

            # nextKey 기반 연속 조회
            next_key = body.get("nextKey", body.get("next_key", ""))
            if not next_key:
                break

        return rows

    async def fetch_transactions(self, target_date: date) -> list[dict]:
        if not self.api_key or not self.secret:
            logger.warning("신한카드 API 키 미설정 (user=%s)", self.user)
            return []
        if not self.card_nos:
            logger.warning("신한카드 카드번호 미설정 (user=%s)", self.user)
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
                "신한카드 승인내역 조회 완료 (user=%s, %s, %d건)",
                self.user, target_date, len(results),
            )
        except httpx.HTTPStatusError as e:
            logger.error(
                "신한카드 API 오류 (user=%s): %s %s",
                self.user, e.response.status_code, e.response.text,
            )
        except Exception as e:
            logger.error("신한카드 오류 (user=%s): %s", self.user, e)

        return results
