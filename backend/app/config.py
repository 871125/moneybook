from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # 사용자 이름
    user1_name: str = "User1"
    user2_name: str = "User2"

    # User1 은행
    user1_woori_bank_api: str = ""
    user1_kakao_bank_api: str = ""
    user1_saemaeul_api: str = ""
    user1_hana_bank_api: str = ""

    # User1 카드
    user1_woori_card_api: str = ""
    user1_hana_card_api: str = ""
    user1_shinhan_card_api: str = ""

    # User1 증권
    user1_samsung_sec_api: str = ""
    user1_mirae_sec_api: str = ""
    user1_meritz_sec_api: str = ""
    user1_nh_sec_api: str = ""

    # User1 거래소
    user1_binance_api_key: str = ""
    user1_binance_secret: str = ""
    user1_upbit_access_key: str = ""
    user1_upbit_secret_key: str = ""

    # User2 은행
    user2_woori_bank_api: str = ""
    user2_kakao_bank_api: str = ""
    user2_saemaeul_api: str = ""
    user2_hana_bank_api: str = ""

    # User2 카드
    user2_woori_card_api: str = ""
    user2_hana_card_api: str = ""
    user2_shinhan_card_api: str = ""

    # User2 증권
    user2_samsung_sec_api: str = ""
    user2_mirae_sec_api: str = ""
    user2_meritz_sec_api: str = ""
    user2_nh_sec_api: str = ""

    # User2 거래소
    user2_bingx_api_key: str = ""
    user2_bingx_secret: str = ""
    user2_upbit_access_key: str = ""
    user2_upbit_secret_key: str = ""

    # 서버 설정
    data_dir: str = "./app/data"

    @property
    def user_names(self) -> list[str]:
        return [self.user1_name, self.user2_name]


@lru_cache
def get_settings() -> Settings:
    return Settings()
