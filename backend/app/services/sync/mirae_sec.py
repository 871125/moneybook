"""
미래에셋증권 Open API 연동 모듈

미래에셋 오픈API 개발자센터: https://openapi.miraeasset.com
인증: App Key + App Secret → OAuth2 Client Credentials Access Token
계좌번호: 복수 계좌는 쉼표로 구분 (예: "12345678,98765432")
"""
import logging
import time
from datetime import date

import httpx

from app.services.sync.base import BaseAssetSyncer

logger = logging.getLogger(__name__)

INSTITUTION = "미래에셋"
BASE_URL = "https://openapi.miraeasset.com"

# 자산 유형 매핑 (미래에셋 응답의 상품구분 → 내부 asset_type)
_ASSET_TYPE_MAP = {
    "01": "국내주식",
    "02": "펀드",
    "03": "채권",
    "04": "ELS/ELB",
    "05": "ETF",
    "06": "ETN",
    "07": "선물옵션",
    "08": "해외주식",
    "09": "달러RP",
    "10": "발행어음",
    "20": "현금",
    "21": "CMA",
    "22": "연금",
}


class MiraeSecAssetSyncer(BaseAssetSyncer):
    """미래에셋증권 자산 현황 수집기 (App Key + App Secret 인증)"""

    def __init__(self, user: str, api_key: str, secret: str = "", account: str = ""):
        super().__init__(user, api_key, secret)
        # 복수 계좌는 쉼표 구분: "12345678,98765432"
        self.accounts: list[str] = [a.strip() for a in account.split(",") if a.strip()]
        self._token: str | None = None
        self._token_expires_at: float = 0.0

    async def _get_token(self, client: httpx.AsyncClient) -> str:
        """Access Token 발급 (만료 60초 전 자동 재발급)"""
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

    async def _fetch_deposit(self, client: httpx.AsyncClient, token: str, account: str) -> int:
        """예수금·CMA 잔고 조회"""
        resp = await client.get(
            f"{BASE_URL}/acc/v1/balance/deposit",
            params={
                "cano": account[:8],
                "acnt_prdt_cd": account[8:] if len(account) > 8 else "01",
            },
            headers=self._auth_headers(token),
            timeout=10,
        )
        resp.raise_for_status()
        body = resp.json()
        output = body.get("output", body.get("Output1", {}))
        # 예수금 잔액 또는 CMA 잔액 우선 사용
        amount_str = (
            output.get("dpst_amt")
            or output.get("cma_evlu_amt")
            or output.get("nxdy_excc_amt")
            or output.get("dnca_tot_amt", "0")
        )
        return int(str(amount_str).replace(",", "") or "0")

    async def _fetch_holdings(
        self, client: httpx.AsyncClient, token: str, account: str
    ) -> list[dict]:
        """보유 종목(주식·펀드·채권 등) 잔고 조회"""
        rows: list[dict] = []
        ctx_area_fk100 = ""
        ctx_area_nk100 = ""

        while True:
            resp = await client.get(
                f"{BASE_URL}/acc/v1/balance/stocks",
                params={
                    "cano": account[:8],
                    "acnt_prdt_cd": account[8:] if len(account) > 8 else "01",
                    "afhr_flpr_yn": "N",
                    "inqr_dvsn": "02",
                    "unpr_dvsn": "01",
                    "fund_sttl_icld_yn": "N",
                    "fncg_amt_auto_rdpt_yn": "N",
                    "prcs_dvsn": "01",
                    "ctx_area_fk100": ctx_area_fk100,
                    "ctx_area_nk100": ctx_area_nk100,
                },
                headers=self._auth_headers(token),
                timeout=10,
            )
            resp.raise_for_status()
            body = resp.json()

            for item in body.get("output2", body.get("Output2", [])):
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

            tr_cont = body.get("tr_cont", "")
            if tr_cont not in ("F", "M"):
                break
            ctx_area_fk100 = body.get("ctx_area_fk100", "")
            ctx_area_nk100 = body.get("ctx_area_nk100", "")

        return rows

    async def _fetch_pension(
        self, client: httpx.AsyncClient, token: str, account: str
    ) -> int:
        """연금계좌 평가금액 조회 (계좌 유형이 연금인 경우)"""
        try:
            resp = await client.get(
                f"{BASE_URL}/acc/v1/balance/pension",
                params={
                    "cano": account[:8],
                    "acnt_prdt_cd": account[8:] if len(account) > 8 else "01",
                },
                headers=self._auth_headers(token),
                timeout=10,
            )
            if resp.status_code == 404:
                return 0
            resp.raise_for_status()
            body = resp.json()
            output = body.get("output", body.get("Output1", {}))
            amt_str = output.get("tot_evlu_amt", output.get("pnsn_evlu_amt", "0"))
            return int(str(amt_str).replace(",", "") or "0")
        except httpx.HTTPStatusError:
            return 0

    async def fetch_assets(self, snapshot_date: date) -> list[dict]:
        if not self.api_key or not self.secret:
            logger.warning("미래에셋 API 키 미설정 (user=%s)", self.user)
            return []
        if not self.accounts:
            logger.warning("미래에셋 계좌번호 미설정 (user=%s)", self.user)
            return []

        results: list[dict] = []
        try:
            async with httpx.AsyncClient() as client:
                token = await self._get_token(client)

                for account in self.accounts:
                    # 예수금
                    deposit = await self._fetch_deposit(client, token, account)
                    if deposit > 0:
                        results.append({
                            "snapshot_date": snapshot_date.isoformat(),
                            "user": self.user,
                            "institution": INSTITUTION,
                            "asset_type": "현금",
                            "balance_krw": deposit,
                        })

                    # 보유 종목
                    for h in await self._fetch_holdings(client, token, account):
                        results.append({
                            "snapshot_date": snapshot_date.isoformat(),
                            "user": self.user,
                            "institution": INSTITUTION,
                            "asset_type": h["asset_type"],
                            "balance_krw": h["balance_krw"],
                        })

                    # 연금계좌 평가금액
                    pension_amt = await self._fetch_pension(client, token, account)
                    if pension_amt > 0:
                        results.append({
                            "snapshot_date": snapshot_date.isoformat(),
                            "user": self.user,
                            "institution": INSTITUTION,
                            "asset_type": "연금",
                            "balance_krw": pension_amt,
                        })

                logger.info(
                    "미래에셋 자산 조회 완료 (user=%s, 계좌=%d개, 항목=%d건)",
                    self.user, len(self.accounts), len(results),
                )
        except httpx.HTTPStatusError as e:
            logger.error(
                "미래에셋 API HTTP 오류 (user=%s): %s %s",
                self.user, e.response.status_code, e.response.text,
            )
        except Exception as e:
            logger.error("미래에셋 API 오류 (user=%s): %s", self.user, e)

        return results
