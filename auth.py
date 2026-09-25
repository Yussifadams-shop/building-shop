import os
from itsdangerous import URLSafeTimedSerializer
from fastapi import Request, HTTPException
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

SECRET_KEY = os.getenv("SECRET_KEY", "defaultsecret")
serializer = URLSafeTimedSerializer(SECRET_KEY)
COOKIE_NAME = "shop_session"


def create_session(username: str) -> str:
    return serializer.dumps({"user": username})


def verify_session(token: str, max_age: int = 60 * 60 * 24 * 7):
    try:
        data = serializer.loads(token, max_age=max_age)
        return data.get("user")
    except Exception:
        return None


def get_current_user(request: Request):
    """Returns username (str) if logged in, else None"""
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        return None
    return verify_session(token)


def get_user_info(username: str):
    """Fetch full user info (role, name) from DB. Returns dict or None."""
    if not username:
        return None
    try:
        result = supabase.table("shop_users").select("*").eq("username", username).eq("is_active", True).single().execute()
        return result.data
    except Exception:
        return None


def log_activity(username: str, action_type: str, description: str, severity: str = "info", details: dict = None):
    """Log an activity to the activity_log table."""
    try:
        supabase.table("activity_log").insert({
            "username": username or "unknown",
            "action_type": action_type,
            "description": description,
            "severity": severity,
            "details": details or {}
        }).execute()
    except Exception:
        pass  # Don't break the app if logging fails


def verify_login(username: str, password: str):
    """Check username + password against the shop_users table. Returns user dict or None."""
    try:
        result = supabase.table("shop_users").select("*").eq("username", username).eq("is_active", True).execute()
        if not result.data:
            log_activity(username, "login_failed", f"Failed login attempt for '{username}' (user not found)", "warning")
            return None
        user = result.data[0]
        if user["password"] == password:
            log_activity(username, "login_success", f"User '{username}' logged in successfully", "info")
            return user
        log_activity(username, "login_failed", f"Failed login attempt for '{username}' (wrong password)", "warning")
        return None
    except Exception:
        return None


def require_role(request: Request, allowed_roles: list):
    """Raise 403 if the logged-in user's role isn't in allowed_roles."""
    username = get_current_user(request)
    if not username:
        raise HTTPException(status_code=303, headers={"Location": "/login"})
    info = get_user_info(username)
    if not info:
        raise HTTPException(status_code=303, headers={"Location": "/login"})
    if info.get("role") not in allowed_roles:
        raise HTTPException(status_code=403, detail="You do not have permission for this action.")
    return info


def is_admin(request: Request) -> bool:
    """Check if logged-in user is admin."""
    username = get_current_user(request)
    if not username:
        return False
    info = get_user_info(username)
    return info and info.get("role") == "admin"