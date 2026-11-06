from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    max_hops: int = 5
    request_timeout_s: float = 20.0
    user_agent: str = "CiteBot/0.2 (+Exact Web Answer Agent; AMD AI League)"

    # Optional LLM — leave empty for rule-based MVP
    openai_api_key: str | None = None
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-4o-mini"
    use_llm: bool = False  # set true + key to enable optional LLM assist


settings = Settings()
