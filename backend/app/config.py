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
    POST_HARVEST_DEMAND_LOOKBACK_DAYS: int = 14
    POST_HARVEST_MAX_FACILITY_RADIUS_KM: float = 50.0
    POST_HARVEST_NO_HISTORY_SELL_FRACTION: float = 0.4
    POST_HARVEST_DISTRESS_SALE_FRACTION: float = 0.15

    # --- Meta Model API ---
    META_AI_ENABLED: bool = False          # master switch; False = app behaves as before
    MODEL_API_KEY: str = ""
    META_API_BASE: str = "https://api.meta.ai/v1"
    META_MODEL_FAST: str = "muse-spark-1.3"
    META_MODEL_DEEP: str = "muse-wonder-1.0"
    META_MODEL_SAM: str = "sam-3.1"
    META_MODEL_IMAGE: str = "muse-image-1.0"
    META_TIMEOUT_S: float = 12.0
    META_DAILY_CALL_CAP: int = 2000        # hard stop so a bug cannot burn your credits
    UPLOAD_DIR: str = "uploads"


@lru_cache
def get_settings() -> Settings:
    return Settings()
