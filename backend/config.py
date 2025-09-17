import os

def _normalize_pg_url(url: str | None) -> str | None:
    """
    Normalize common Postgres URLs:
    - Convert 'postgres://' -> 'postgresql://'
    - If using psycopg2, keep 'postgresql://'
    """
    if not url:
        return None
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    return url

class Config:
    # --- Core ---
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")

    # Choose DB in this order:
    # 1) If FLASK_ENV=development and DEV_DATABASE_URL is set -> use that
    # 2) Else if DATABASE_URL set (e.g. Aiven on Render) -> use that
    # 3) Else fallback to local SQLite (dev only)
    FLASK_ENV = os.getenv("FLASK_ENV", "development")
    if FLASK_ENV == "development" and os.getenv("DEV_DATABASE_URL"):
        SQLALCHEMY_DATABASE_URI = _normalize_pg_url(os.getenv("DEV_DATABASE_URL"))
    else:
        SQLALCHEMY_DATABASE_URI = _normalize_pg_url(os.getenv("DATABASE_URL")) or "sqlite:///app.db"

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # --- CORS / cookies for SPA ---
    FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", "http://localhost:5173")

    # Cookies: in production (Render + Netlify), allow cross-site cookies
    if os.getenv("PRODUCTION", "0") == "1":
        SESSION_COOKIE_SAMESITE = "None"
        SESSION_COOKIE_SECURE = True
    else:
        SESSION_COOKIE_SAMESITE = "Lax"
        SESSION_COOKIE_SECURE = False
