# MoneyBook — 통합 가계부 및 자산 관리 대시보드

은행·증권·카드·거래소 계좌를 한 곳에서 조회하는 개인 자산 관리 도구입니다.  
매일 거래내역을 자동 수집하고, 매월 자산 스냅샷을 기록합니다.

---

## 목차

1. [기술 스택](#기술-스택)
2. [지원 기관](#지원-기관)
3. [프로젝트 구조](#프로젝트-구조)
4. [환경 설정](#환경-설정)
   - [백엔드 .env](#백엔드-env)
   - [프론트엔드 .env](#프론트엔드-env)
5. [기관별 API 키 발급 및 설정](#기관별-api-키-발급-및-설정)
   - [은행](#은행)
   - [증권](#증권)
   - [카드](#카드)
   - [거래소](#거래소)
6. [구동 방법](#구동-방법)
   - [백엔드](#백엔드-실행)
   - [프론트엔드](#프론트엔드-실행)
7. [수동 동기화](#수동-동기화)
8. [자동 수집 스케줄](#자동-수집-스케줄)

---

## 기술 스택

| 구분 | 기술 |
|---|---|
| 백엔드 | Python 3.11+, FastAPI, APScheduler, httpx |
| 프론트엔드 | React 19, TypeScript, Ant Design, Vite |
| 저장소 | CSV 파일 (별도 DB 불필요) |

---

## 지원 기관

| 구분 | 기관 | 수집 데이터 |
|---|---|---|
| 은행 | 우리은행, 카카오뱅크, 하나은행, 새마을금고 | 거래내역 + 잔고 |
| 증권 | 삼성증권, 미래에셋, 메리츠증권, NH투자증권 | 자산 평가금액 |
| 카드 | 우리카드, 하나카드, 신한카드, 롯데카드, 삼성카드 | 승인·취소 내역 |
| 거래소 | Binance, BingX, Upbit | 보유 코인 KRW 환산 |

---

## 프로젝트 구조

```
moneybook/
├── backend/
│   ├── app/
│   │   ├── config.py              # 환경변수 설정 (pydantic-settings)
│   │   ├── main.py                # FastAPI 앱 진입점
│   │   ├── routers/               # API 라우터 (transactions, assets)
│   │   ├── services/
│   │   │   ├── csv_store.py       # CSV 읽기/쓰기
│   │   │   ├── scheduler.py       # APScheduler 배치 작업
│   │   │   └── sync/              # 기관별 Open API 연동 모듈
│   │   └── data/                  # CSV 데이터 파일
│   ├── .env.example
│   └── requirements.txt
└── frontend/
    ├── src/
    │   ├── api/                   # axios API 클라이언트
    │   ├── components/            # 차트·테이블 컴포넌트
    │   └── pages/                 # Assets, Transactions 페이지
    ├── .env.example
    └── package.json
```

---

## 환경 설정

### 백엔드 .env

`backend/.env.example`을 복사해 `backend/.env`를 만들고 값을 채웁니다.

```bash
cp backend/.env.example backend/.env
```

```dotenv
# ── 사용자 이름 ──────────────────────────────────────────
USER1_NAME=홍길동
USER2_NAME=홍길순
USER3_NAME=홍길삼

# ── 서버 설정 ────────────────────────────────────────────
DATA_DIR=./app/data
```

사용하지 않는 기관의 필드는 **비워두면** 해당 기관은 자동으로 스킵됩니다.

### 프론트엔드 .env

`frontend/.env.example`을 복사해 `frontend/.env`를 만듭니다.

```bash
cp frontend/.env.example frontend/.env
```

```dotenv
VITE_API_URL=http://localhost:8000/api/v1
VITE_USER1_NAME=홍길동
VITE_USER2_NAME=홍길순
```

---

## 기관별 API 키 발급 및 설정

> 각 기관의 오픈API 개발자 포털에서 앱을 등록한 뒤 App Key와 App Secret을 발급받습니다.  
> 계좌번호·카드번호는 하이픈 포함 또는 숫자만 모두 허용합니다.  
> **복수 계좌·카드는 쉼표(`,`)로 구분합니다.**

---

### 은행

#### 우리은행
> 개발자 포털: https://developer.wooribank.com

```dotenv
USER1_WOORI_BANK_APP_KEY=발급받은_앱키
USER1_WOORI_BANK_APP_SECRET=발급받은_앱시크릿
USER1_WOORI_BANK_ACCOUNT=1002-123-456789          # 복수: 1002-123-456789,1002-987-654321
```

#### 카카오뱅크
> 개발자 포털: https://developers.kakaobank.com

```dotenv
USER1_KAKAO_BANK_APP_KEY=발급받은_앱키
USER1_KAKAO_BANK_APP_SECRET=발급받은_앱시크릿
USER1_KAKAO_BANK_ACCOUNT=3333-01-1234567
```

#### 하나은행
> 개발자 포털: https://developer.kebhana.com  
> ⚠️ 요청마다 HMAC-SHA256 서명이 자동으로 생성됩니다.

```dotenv
USER1_HANA_BANK_APP_KEY=발급받은_앱키
USER1_HANA_BANK_APP_SECRET=발급받은_앱시크릿
USER1_HANA_BANK_ACCOUNT=123-456789-01234
```

#### 새마을금고
> 개발자 포털: https://openapi.mgcredit.co.kr  
> ⚠️ `BRANCH`는 거래 새마을금고의 **금고코드 4자리**입니다.

```dotenv
USER1_SAEMAEUL_APP_KEY=발급받은_앱키
USER1_SAEMAEUL_APP_SECRET=발급받은_앱시크릿
USER1_SAEMAEUL_BRANCH=0001                        # 금고코드 (4자리)
USER1_SAEMAEUL_ACCOUNT=1234-56-789012
```

---

### 증권

#### 삼성증권
> 개발자 포털: https://openapi.samsungsecurities.com

```dotenv
USER1_SAMSUNG_SEC_APP_KEY=발급받은_앱키
USER1_SAMSUNG_SEC_APP_SECRET=발급받은_앱시크릿
USER1_SAMSUNG_SEC_ACCOUNT=1234567890              # 계좌번호 (10자리)
```

#### 미래에셋증권
> 개발자 포털: https://openapi.miraeasset.com

```dotenv
USER1_MIRAE_SEC_APP_KEY=발급받은_앱키
USER1_MIRAE_SEC_APP_SECRET=발급받은_앱시크릿
USER1_MIRAE_SEC_ACCOUNT=12345678                  # 복수: 12345678,98765432
```

#### 메리츠증권
> 개발자 포털: https://openapi.meritzsecurities.com

```dotenv
USER1_MERITZ_SEC_APP_KEY=발급받은_앱키
USER1_MERITZ_SEC_APP_SECRET=발급받은_앱시크릿
USER1_MERITZ_SEC_ACCOUNT=12345678
```

#### NH투자증권 (나무 Open API)
> 개발자 포털: https://openapi.nhqv.com

```dotenv
USER1_NH_SEC_APP_KEY=발급받은_앱키
USER1_NH_SEC_APP_SECRET=발급받은_앱시크릿
USER1_NH_SEC_ACCOUNT=12345678                     # ISA·IRP 포함 복수 계좌 지원
```

---

### 카드

> 모든 카드사는 **가맹점명**을 거래 적요로 저장합니다.

#### 우리카드
> 개발자 포털: https://developer.wooricard.com

```dotenv
USER1_WOORI_CARD_APP_KEY=발급받은_앱키
USER1_WOORI_CARD_APP_SECRET=발급받은_앱시크릿
USER1_WOORI_CARD_NO=1234-5678-9012-3456
```

#### 하나카드
> 개발자 포털: https://developers.hanacard.co.kr  
> ⚠️ 요청마다 HMAC-SHA256 서명이 자동으로 생성됩니다.

```dotenv
USER1_HANA_CARD_APP_KEY=발급받은_앱키
USER1_HANA_CARD_APP_SECRET=발급받은_앱시크릿
USER1_HANA_CARD_NO=1234-5678-9012-3456
```

#### 신한카드
> 개발자 포털: https://developers.shinhancard.com  
> ⚠️ 카드번호를 RSA-OAEP로 암호화합니다. 운영 환경에서는 `cryptography` 패키지 필요:  
> `pip install cryptography`

```dotenv
USER1_SHINHAN_CARD_APP_KEY=발급받은_앱키
USER1_SHINHAN_CARD_APP_SECRET=발급받은_앱시크릿
USER1_SHINHAN_CARD_NO=1234-5678-9012-3456
```

#### 롯데카드
> 개발자 포털: https://developers.lottecard.co.kr

```dotenv
USER1_LOTTE_CARD_APP_KEY=발급받은_앱키
USER1_LOTTE_CARD_APP_SECRET=발급받은_앱시크릿
USER1_LOTTE_CARD_NO=1234-5678-9012-3456
```

#### 삼성카드
> 개발자 포털: https://developers.samsungcard.com

```dotenv
USER1_SAMSUNG_CARD_APP_KEY=발급받은_앱키
USER1_SAMSUNG_CARD_APP_SECRET=발급받은_앱시크릿
USER1_SAMSUNG_CARD_NO=1234-5678-9012-3456
```

---

### 거래소

#### Binance
> API 관리: https://www.binance.com/en/my/settings/api-management  
> 권한: **Read Only** (출금 권한 불필요)  
> ⚠️ HMAC-SHA256 서명 방식. Spot + Simple Earn 잔고를 수집합니다.

```dotenv
USER1_BINANCE_API_KEY=발급받은_API_Key
USER1_BINANCE_SECRET=발급받은_Secret_Key
```

#### BingX
> API 관리: https://bingx.com/en-us/account/api  
> 권한: **Read Only**  
> ⚠️ Spot + Perpetual Futures(USDT-M) 잔고를 수집합니다.

```dotenv
USER2_BINGX_API_KEY=발급받은_API_Key
USER2_BINGX_SECRET=발급받은_Secret_Key
```

#### Upbit
> API 관리: https://upbit.com/mypage/open_api_management  
> 권한: **자산 조회** (출금·주문 권한 불필요)  
> ⚠️ JWT(HS256) 인증. KRW·BTC·USDT 마켓 보유 코인을 KRW로 환산합니다.

```dotenv
USER1_UPBIT_ACCESS_KEY=발급받은_Access_Key
USER1_UPBIT_SECRET_KEY=발급받은_Secret_Key
```

> **KRW 환산 방식** (Binance·BingX):  
> 코인 잔고 × USDT 가격(각 거래소) × USDT/KRW(Upbit 공개 API 실시간)

---

## 구동 방법

### 백엔드 실행

```bash
cd backend

# 1. 가상환경 생성 및 활성화
python -m venv .venv

# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

# 2. 의존성 설치
pip install -r requirements.txt

# 3. 환경변수 파일 준비
cp .env.example .env
# .env 파일에 API 키 입력

# 4. 서버 실행 (기본 포트: 8000)
uvicorn app.main:app --reload
```

서버가 뜨면 API 문서를 브라우저에서 확인할 수 있습니다:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

---

### 프론트엔드 실행

```bash
cd frontend

# 1. 의존성 설치
npm install

# 2. 환경변수 파일 준비
cp .env.example .env
# .env에서 사용자 이름 설정

# 3. 개발 서버 실행 (기본 포트: 5173)
npm run dev
```

브라우저에서 http://localhost:5173 으로 접속합니다.

---

## 수동 동기화

백엔드 서버가 실행 중일 때 API를 직접 호출해 즉시 수집할 수 있습니다.

```bash
# 거래내역 즉시 수집 (전일 기준)
curl -X POST http://localhost:8000/api/v1/sync/transactions

# 자산 스냅샷 즉시 수집 (오늘 기준)
curl -X POST http://localhost:8000/api/v1/sync/assets
```

또는 Swagger UI(http://localhost:8000/docs)에서 버튼으로 실행할 수 있습니다.

---

## 자동 수집 스케줄

서버가 실행되어 있으면 APScheduler가 자동으로 아래 작업을 수행합니다.

| 작업 | 주기 | 시각 | 내용 |
|---|---|---|---|
| 거래내역 수집 | 매일 | 오전 02:00 | 전일 입출금·카드 승인 내역 |
| 자산 스냅샷 | 매월 1일 | 오전 00:10 | 전 기관 잔고·평가금액 기록 |

수집된 데이터는 `backend/app/data/` 폴더의 CSV 파일에 저장됩니다.

```
backend/app/data/
├── transactions.csv   # 거래내역
└── monthly_assets.csv # 월별 자산 스냅샷
```
