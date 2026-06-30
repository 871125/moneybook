"""
삼성증권 Open API 연동 모듈

삼성증권 오픈API 개발자센터: https://openapi.samsungsecurities.com
인증: App Key + App Secret → OAuth2 Client Credentials Access Token
"""
import logging
import time
from datetime import date

import httpx

from app.services.sync.base import BaseAssetSyncer

logger = logging.getLogger(__name__)

INSTITUTION = "삼성증권"
BASE_URL = "https://openapi.samsungsecurities.com"

# 자산 유형 매핑 (삼성증권 응답의 prd_tp → 내부 asset_type)
_ASSET_TYPE_MAP = {
    "01": "국내주식",
    "02": "펀드",
    "03": "채권",
    "04": "ELS/DLS",
    "05": "ETF",
    "06": "ELW",
    "07": "선물옵션",
    "10": "해외주식",
    "20": "현금",
}


class SamsungSecAssetSyncer(BaseAssetSyncer):
    """삼성증권 자산 현황 수집기 (App Key + App Secret 인증)"""

    def __init__(self, user: str, api_key: str, secret: str = "", account: str = ""):
        super().__init__(user, api_key, secret)
        self.account = account  # 계좌번호 (예: "1234567890")
        self._token: str | None = None
        self._token_expires_at: float = 0.0

    async def _get_token(self, client: httpx.AsyncClient) -> str:
        """Access Token 발급 (만료 시 자동 재발급)"""
        if self._token and time.time() < self._token_expires_at - 60:
            return self._token

        resp = await client.post(
            f"{BASE_URL}/oauth2/Prod/token",
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

    async def _fetch_deposit(self, client: httpx.AsyncClient, token: str) -> int:
        """예수금(현금) 잔고 조회"""
        resp = await client.get(
            f"{BASE_URL}/acc/v1/accno/deposit",
            params={"cano": self.account[:8], "acnt_prdt_cd": self.account[8:] if len(self.account) > 8 else "01"},
            headers=self._auth_headers(token),
            timeout=10,
        )
        resp.raise_for_status()
        body = resp.json()
        # 응답 필드명 확인 후 조정 필요: 예수금_총액 또는 dpst_amt
        output = body.get("output", body.get("Output1", {}))
        amount_str = (
            output.get("dpst_amt")
            or output.get("nxdy_excc_amt")
            or output.get("dnca_tot_amt", "0")
        )
        return int(str(amount_str).replace(",", "") or "0")

    async def _fetch_holdings(
        self, client: httpx.AsyncClient, token: str
    ) -> list[dict]:
        """주식·펀드 등 보유 종목 잔고 조회"""
        rows: list[dict] = []
        ctx_area_fk100 = ""
        ctx_area_nk100 = ""

        while True:
            params: dict = {
                "cano": self.account[:8],
                "acnt_prdt_cd": self.account[8:] if len(self.account) > 8 else "01",
                "afhr_flpr_yn": "N",
                "ofl_yn": "",
                "inqr_dvsn": "02",
                "unpr_dvsn": "01",
                "fund_sttl_icld_yn": "N",
                "fncg_amt_auto_rdpt_yn": "N",
                "prcs_dvsn": "01",
                "ctx_area_fk100": ctx_area_fk100,
                "ctx_area_nk100": ctx_area_nk100,
            }
            resp = await client.get(
                f"{BASE_URL}/acc/v1/accno/stocks",
                params=params,
                headers=self._auth_headers(token),
                timeout=10,
            )
            resp.raise_for_status()
            body = resp.json()

            output2 = body.get("output2", body.get("Output2", []))
            for item in output2:
                hldg_qty = int(str(item.get("hldg_qty", "0")).replace(",", "") or "0")
                if hldg_qty <= 0:
                    continue
                evlu_amt = int(
                    str(item.get("evlu_amt", item.get("pchs_amt", "0"))).replace(",", "") or "0"
                )
                prd_tp = item.get("prd_tp", "01")
                asset_type = _ASSET_TYPE_MAP.get(prd_tp, "국내주식")
                prdt_name = item.get("prdt_name", item.get("prdt_abrv_name", asset_type))
                rows.append({"asset_type": f"{asset_type}({prdt_name})", "balance_krw": evlu_amt})

            # 연속 조회 여부 확인
            tr_cont = body.get("tr_cont", "")
            if tr_cont not in ("F", "M"):
                break
            ctx_area_fk100 = body.get("ctx_area_fk100", "")
            ctx_area_nk100 = body.get("ctx_area_nk100", "")

        return rows

    async def fetch_assets(self, snapshot_date: date) -> list[dict]:
        if not self.api_key or not self.secret:
            logger.warning("삼성증권 API 키 미설정 (user=%s)", self.user)
            return []
        if not self.account:
            logger.warning("삼성증권 계좌번호 미설정 (user=%s)", self.user)
            return []

        results: list[dict] = []
        try:
            async with httpx.AsyncClient() as client:
                token = await self._get_token(client)

                # 예수금
                deposit = await self._fetch_deposit(client, token)
                if deposit > 0:
                    results.append({
                        "snapshot_date": snapshot_date.isoformat(),
                        "user": self.user,
                        "institution": INSTITUTION,
                        "asset_type": "현금",
                        "balance_krw": deposit,
                    })

                # 보유 종목
                holdings = await self._fetch_holdings(client, token)
                for h in holdings:
                    results.append({
                        "snapshot_date": snapshot_date.isoformat(),
                        "user": self.user,
                        "institution": INSTITUTION,
                        "asset_type": h["asset_type"],
                        "balance_krw": h["balance_krw"],
                    })

                logger.info(
                    "삼성증권 자산 조회 완료 (user=%s, 항목=%d건)", self.user, len(results)
                )
        except httpx.HTTPStatusError as e:
            logger.error("삼성증권 API HTTP 오류 (user=%s): %s %s", self.user, e.response.status_code, e.response.text)
        except Exception as e:
            logger.error("삼성증권 API 오류 (user=%s): %s", self.user, e)

        return results
