import os
from itsdangerous import URLSafeTimedSerializer
from fastapi import Request, HTTPException

SECRET_KEY = os.getenv("SECRET_KEY", "defaultsecret")
serializer = URLSafeTimedSerializer(SECRET_KEY)
COOKIE_NAME = "shop_session"


def create_session(username: str) -> str:
    return serializer.dumps({"user": username})


def verify_session(token: str, max_age: int = 60 * 60 * 24 * 7):
    """Session valid for 7 days"""
    try:
        data = serializer.loads(token, max_age=max_age)
        return data.get("user")
    except Exception:
        return None


def get_current_user(request: Request):
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        return None
    return verify_session(token)


def require_login(request: Request):
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=303, headers={"Location": "/login"})
    return user