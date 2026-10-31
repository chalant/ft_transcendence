import os
import time

import jwt

SECRET = os.environ["JWT_SECRET_KEY"]
ISSUER = "ft_transcendence.com"
LIFETIME_SECONDS = 2 * 60 * 60


def issue(user) -> str:
    now = int(time.time())
    return jwt.encode(
        {
            "sub": str(user.id),
            "name": user.username,
            "iat": now,
            "exp": now + LIFETIME_SECONDS,
            "iss": ISSUER,
        },
        SECRET,
        algorithm="HS256",
    )


def verify(token) -> dict | None:
    """Return the token payload, or None if it is missing, forged or expired."""
    if not token:
        return None
    try:
        return jwt.decode(
            token,
            SECRET,
            algorithms=["HS256"],
            issuer=ISSUER,
            options={"require": ["exp", "sub"]},
        )
    except jwt.PyJWTError:
        return None
