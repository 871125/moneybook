from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # 사용자 이름
    user1_name: str = "User1"
    user2_name: str = "User2"
    user3_name: str = "User3"

    # User1 은행
    user1_woori_bank_app_key: str = ""
    user1_woori_bank_app_secret: str = ""
    user1_woori_bank_account: str = ""
    user1_kakao_bank_app_key: str = ""
    user1_kakao_bank_app_secret: str = ""
    user1_kakao_bank_account: str = ""
    user1_saemaeul_app_key: str = ""
    user1_saemaeul_app_secret: str = ""
    user1_saemaeul_branch: str = ""
    user1_saemaeul_account: str = ""
    user1_hana_bank_app_key: str = ""
    user1_hana_bank_app_secret: str = ""
    user1_hana_bank_account: str = ""

    # User1 카드
    user1_woori_card_app_key: str = ""
    user1_woori_card_app_secret: str = ""
    user1_woori_card_no: str = ""
    user1_hana_card_app_key: str = ""
    user1_hana_card_app_secret: str = ""
    user1_hana_card_no: str = ""
    user1_shinhan_card_app_key: str = ""
    user1_shinhan_card_app_secret: str = ""
    user1_shinhan_card_no: str = ""
    user1_lotte_card_app_key: str = ""
    user1_lotte_card_app_secret: str = ""
    user1_lotte_card_no: str = ""
    user1_samsung_card_app_key: str = ""
    user1_samsung_card_app_secret: str = ""
    user1_samsung_card_no: str = ""

    # User1 증권
    user1_samsung_sec_app_key: str = ""
    user1_samsung_sec_app_secret: str = ""
    user1_samsung_sec_account: str = ""
    user1_mirae_sec_app_key: str = ""
    user1_mirae_sec_app_secret: str = ""
    user1_mirae_sec_account: str = ""
    user1_meritz_sec_app_key: str = ""
    user1_meritz_sec_app_secret: str = ""
    user1_meritz_sec_account: str = ""
    user1_nh_sec_app_key: str = ""
    user1_nh_sec_app_secret: str = ""
    user1_nh_sec_account: str = ""

    # User1 거래소
    user1_binance_api_key: str = ""
    user1_binance_secret: str = ""
    user1_bingx_api_key: str = ""
    user1_bingx_secret: str = ""
    user1_upbit_access_key: str = ""
    user1_upbit_secret_key: str = ""

    # User2 은행
    user2_woori_bank_app_key: str = ""
    user2_woori_bank_app_secret: str = ""
    user2_woori_bank_account: str = ""
    user2_kakao_bank_app_key: str = ""
    user2_kakao_bank_app_secret: str = ""
    user2_kakao_bank_account: str = ""
    user2_saemaeul_app_key: str = ""
    user2_saemaeul_app_secret: str = ""
    user2_saemaeul_branch: str = ""
    user2_saemaeul_account: str = ""
    user2_hana_bank_app_key: str = ""
    user2_hana_bank_app_secret: str = ""
    user2_hana_bank_account: str = ""

    # User2 카드
    user2_woori_card_app_key: str = ""
    user2_woori_card_app_secret: str = ""
    user2_woori_card_no: str = ""
    user2_hana_card_app_key: str = ""
    user2_hana_card_app_secret: str = ""
    user2_hana_card_no: str = ""
    user2_shinhan_card_app_key: str = ""
    user2_shinhan_card_app_secret: str = ""
    user2_shinhan_card_no: str = ""
    user2_lotte_card_app_key: str = ""
    user2_lotte_card_app_secret: str = ""
    user2_lotte_card_no: str = ""
    user2_samsung_card_app_key: str = ""
    user2_samsung_card_app_secret: str = ""
    user2_samsung_card_no: str = ""

    # User2 증권
    user2_samsung_sec_app_key: str = ""
    user2_samsung_sec_app_secret: str = ""
    user2_samsung_sec_account: str = ""
    user2_mirae_sec_app_key: str = ""
    user2_mirae_sec_app_secret: str = ""
    user2_mirae_sec_account: str = ""
    user2_meritz_sec_app_key: str = ""
    user2_meritz_sec_app_secret: str = ""
    user2_meritz_sec_account: str = ""
    user2_nh_sec_app_key: str = ""
    user2_nh_sec_app_secret: str = ""
    user2_nh_sec_account: str = ""

    # User2 거래소
    user2_bingx_api_key: str = ""
    user2_bingx_secret: str = ""
    user2_upbit_access_key: str = ""
    user2_upbit_secret_key: str = ""

    # User3 은행
    user3_woori_bank_app_key: str = ""
    user3_woori_bank_app_secret: str = ""
    user3_woori_bank_account: str = ""
    user3_kakao_bank_app_key: str = ""
    user3_kakao_bank_app_secret: str = ""
    user3_kakao_bank_account: str = ""
    user3_saemaeul_app_key: str = ""
    user3_saemaeul_app_secret: str = ""
    user3_saemaeul_branch: str = ""
    user3_saemaeul_account: str = ""
    user3_hana_bank_app_key: str = ""
    user3_hana_bank_app_secret: str = ""
    user3_hana_bank_account: str = ""

    # User3 카드
    user3_woori_card_app_key: str = ""
    user3_woori_card_app_secret: str = ""
    user3_woori_card_no: str = ""
    user3_hana_card_app_key: str = ""
    user3_hana_card_app_secret: str = ""
    user3_hana_card_no: str = ""
    user3_shinhan_card_app_key: str = ""
    user3_shinhan_card_app_secret: str = ""
    user3_shinhan_card_no: str = ""
    user3_lotte_card_app_key: str = ""
    user3_lotte_card_app_secret: str = ""
    user3_lotte_card_no: str = ""
    user3_samsung_card_app_key: str = ""
    user3_samsung_card_app_secret: str = ""
    user3_samsung_card_no: str = ""

    # User3 증권
    user3_samsung_sec_app_key: str = ""
    user3_samsung_sec_app_secret: str = ""
    user3_samsung_sec_account: str = ""
    user3_mirae_sec_app_key: str = ""
    user3_mirae_sec_app_secret: str = ""
    user3_mirae_sec_account: str = ""
    user3_meritz_sec_app_key: str = ""
    user3_meritz_sec_app_secret: str = ""
    user3_meritz_sec_account: str = ""
    user3_nh_sec_app_key: str = ""
    user3_nh_sec_app_secret: str = ""
    user3_nh_sec_account: str = ""

    # User3 거래소
    user3_binance_api_key: str = ""
    user3_binance_secret: str = ""
    user3_bingx_api_key: str = ""
    user3_bingx_secret: str = ""
    user3_upbit_access_key: str = ""
    user3_upbit_secret_key: str = ""

    # 서버 설정
    data_dir: str = "./app/data"

    @property
    def user_names(self) -> list[str]:
        return [self.user1_name, self.user2_name, self.user3_name]


@lru_cache
def get_settings() -> Settings:
    return Settings()
