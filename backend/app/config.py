"""
Central configuration. All secrets/URLs come from environment variables
(.env in dev, real secret manager in prod) — nothing is hard-coded.
"""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- Core ---
    APP_NAME: str = "Uzhavan.AI"
    ENV: str = "development"
    DEBUG: bool = True

    # --- Database ---
    # Dev default is a local SQLite file so the whole backend runs with zero
    # external infra. Production MUST set DATABASE_URL to a Postgres+PostGIS
    # instance, e.g. postgresql+psycopg2://user:pass@host:5432/uzhavan
    DATABASE_URL: str = "sqlite:///./uzhavan_dev.db"

    # --- Auth ---
    JWT_SECRET_KEY: str = "CHANGE_ME_IN_PRODUCTION"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24h, mirrors low-connectivity field use

    # --- Redis / Celery ---
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/1"

    # --- Bhashini (voice/NLP) ---
    BHASHINI_API_BASE: str = "https://meity-auth.ulcacontrib.org"
    BHASHINI_INFERENCE_BASE: str = "https://dhruva-api.bhashini.gov.in"
    BHASHINI_USER_ID: str = ""
    BHASHINI_API_KEY: str = ""
    BHASHINI_DEFAULT_LANG: str = "ta"  # Tamil

    # --- Payments (Razorpay) ---
    RAZORPAY_KEY_ID: str = ""
    RAZORPAY_KEY_SECRET: str = ""
    RAZORPAY_API_BASE: str = "https://api.razorpay.com/v1"

    # --- KYC (DigiLocker) ---
    DIGILOCKER_CLIENT_ID: str = ""
    DIGILOCKER_CLIENT_SECRET: str = ""
    DIGILOCKER_API_BASE: str = "https://api.digitallocker.gov.in"
    DIGILOCKER_REDIRECT_URI: str = "https://your-domain.example/kyc/callback"

    # --- Routing / Maps ---
    OSRM_BASE_URL: str = "https://router.project-osrm.org"
    GOOGLE_MAPS_API_KEY: str = ""

    # --- Price scraping ---
    AGMARKNET_BASE_URL: str = "https://agmarknet.gov.in"
    OGD_INDIA_API_KEY: str = ""

    # --- Logistics pooling ---
    POOLING_RADIUS_KM: float = 8.0
    POOLING_MIN_FARMERS: int = 3

    # --- Fair price algorithm weights ---
    PRICE_FARMER_SHARE: float = 0.65   # fraction of (retail - wholesale) spread passed to farmer
    PRICE_PLATFORM_FEE_PCT: float = 0.03

    # --- Post-harvest advisor ---
    # See services/post_harvest_advisor.py for how each of these is used.
    POST_HARVEST_DEMAND_LOOKBACK_DAYS: int = 14
    POST_HARVEST_MAX_FACILITY_RADIUS_KM: float = 50.0
    POST_HARVEST_NO_HISTORY_SELL_FRACTION: float = 0.4
    # Illustrative-only: what a forced, no-plan, same-day sale of oversupply
    # typically clears relative to fair price, used solely to compute the
    # "do nothing" baseline a recommendation is measured against — not used
    # anywhere a farmer is actually paid.
    POST_HARVEST_DISTRESS_SALE_FRACTION: float = 0.15


@lru_cache
def get_settings() -> Settings:
    return Settings()
