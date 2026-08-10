import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from uuid import UUID

from fastapi import Header, HTTPException, status
from psycopg.rows import dict_row

from app.core.config import settings
from app.core.database import get_database_connection
from app.schemas.auth import InternalUser


class SupabaseAuthUnavailable(RuntimeError):
    pass


def _extract_bearer_token(
    authorization: str | None,
) -> str:
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "AUTHENTICATION_REQUIRED",
                "message": "Authentication is required.",
            },
            headers={
                "WWW-Authenticate": "Bearer",
            },
        )

    scheme, separator, token = (
        authorization.partition(" ")
    )

    if (
        separator != " "
        or scheme.lower() != "bearer"
        or not token.strip()
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "INVALID_AUTHORIZATION",
                "message": "A valid Bearer token is required.",
            },
            headers={
                "WWW-Authenticate": "Bearer",
            },
        )

    return token.strip()


def _verify_supabase_user(
    access_token: str,
) -> dict:
    if not settings.supabase_anon_key:
        raise SupabaseAuthUnavailable(
            "SUPABASE_ANON_KEY is not configured."
        )

    request = Request(
        (
            settings.supabase_url.rstrip("/")
            + "/auth/v1/user"
        ),
        method="GET",
        headers={
            "apikey":
                settings.supabase_anon_key,
            "Authorization":
                f"Bearer {access_token}",
            "Accept":
                "application/json",
        },
    )

    try:
        with urlopen(
            request,
            timeout=5,
        ) as response:
            return json.loads(
                response.read().decode(
                    "utf-8"
                )
            )

    except HTTPError as exc:
        if exc.code in (401, 403):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "code": "INVALID_ACCESS_TOKEN",
                    "message": (
                        "The authentication session is invalid."
                    ),
                },
                headers={
                    "WWW-Authenticate": "Bearer",
                },
            ) from exc

        raise SupabaseAuthUnavailable(
            "Supabase Auth returned an unexpected response."
        ) from exc

    except (
        URLError,
        TimeoutError,
        json.JSONDecodeError,
    ) as exc:
        raise SupabaseAuthUnavailable(
            "Supabase Auth is unavailable."
        ) from exc


def _load_internal_profile(
    user_id: UUID,
) -> InternalUser:
    with get_database_connection() as connection:
        connection.row_factory = dict_row

        with connection.cursor() as cursor:
            cursor.execute(
                """
                select
                    id,
                    email,
                    name,
                    role
                from public.users
                where id = %s
                  and status = 'ACTIVE'
                limit 1;
                """,
                (user_id,),
            )

            profile = cursor.fetchone()

    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "STAFF_ACCESS_REQUIRED",
                "message": (
                    "This account does not have active "
                    "SupportPilot staff access."
                ),
            },
        )

    return InternalUser(
        id=profile["id"],
        email=profile["email"],
        name=profile["name"],
        role=profile["role"],
    )


def get_current_internal_user(
    authorization: str | None = Header(
        default=None,
        alias="Authorization",
    ),
) -> InternalUser:
    access_token = _extract_bearer_token(
        authorization
    )

    try:
        auth_user = _verify_supabase_user(
            access_token
        )

    except SupabaseAuthUnavailable as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "AUTH_SERVICE_UNAVAILABLE",
                "message": (
                    "Authentication is temporarily unavailable."
                ),
            },
        ) from exc

    user_id = auth_user.get("id")

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "INVALID_ACCESS_TOKEN",
                "message": (
                    "The authentication session is invalid."
                ),
            },
        )

    try:
        parsed_user_id = UUID(
            str(user_id)
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "INVALID_ACCESS_TOKEN",
                "message": (
                    "The authentication session is invalid."
                ),
            },
        ) from exc

    return _load_internal_profile(
        parsed_user_id
    )