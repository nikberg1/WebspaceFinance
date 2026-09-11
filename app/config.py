from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    bot_token: str = "123456:REPLACE_ME"
    webapp_url: str = "http://127.0.0.1:8080"
    staff_ids: str = "111,222"
    dev_mode: bool = True
    secret_key: str = "change-me"
    host: str = "0.0.0.0"
    port: int = 8080

    @property
    def staff_id_set(self) -> set[int]:
        return {int(x.strip()) for x in self.staff_ids.split(",") if x.strip()}


settings = Settings()
