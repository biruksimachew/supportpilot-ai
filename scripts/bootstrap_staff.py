import argparse
import getpass
import json
import re
import shutil
import subprocess
import sys

from urllib.error import (
    HTTPError,
    URLError,
)

from urllib.parse import (
    urlencode,
)

from urllib.request import (
    Request,
    urlopen,
)


DEFAULT_EMAIL = (
    "support.manager@example.com"
)

DEFAULT_NAME = (
    "SupportPilot Local Manager"
)

DEFAULT_ROLE = (
    "SUPPORT_MANAGER"
)


VALID_ROLES = {
    "SUPPORT_AGENT",
    "SUPPORT_MANAGER",
    "SYSTEM_ADMIN",
}


def load_supabase_environment() -> dict[str, str]:

    npx = shutil.which(
        "npx"
    )


    if npx is None:

        raise RuntimeError(
            "npx was not found on PATH."
        )


    result = subprocess.run(
        [
            npx,
            "supabase",
            "status",
            "-o",
            "env",
        ],

        capture_output=True,
        text=True,
        check=False,
    )


    if result.returncode != 0:

        raise RuntimeError(
            (
                "Unable to read local "
                "Supabase status.\n\n"
                + result.stderr.strip()
            )
        )


    environment: dict[
        str,
        str,
    ] = {}


    pattern = re.compile(
        r'^([A-Z0-9_]+)="?(.*?)"?$'
    )


    for raw_line in (
        result.stdout.splitlines()
    ):

        line = raw_line.strip()


        match = pattern.match(
            line
        )


        if match is None:

            continue


        key = match.group(
            1
        )


        value = match.group(
            2
        )


        environment[
            key
        ] = value


    api_url = (
        environment.get(
            "API_URL"
        )
    )


    service_role_key = (
        environment.get(
            "SERVICE_ROLE_KEY"
        )
    )


    if not api_url:

        raise RuntimeError(
            (
                "Supabase CLI did not return "
                "API_URL."
            )
        )


    if not service_role_key:

        raise RuntimeError(
            (
                "Supabase CLI did not return "
                "SERVICE_ROLE_KEY."
            )
        )


    return {
        "api_url":
            api_url.rstrip(
                "/"
            ),

        "service_role_key":
            service_role_key,
    }


def request_json(
    *,
    method: str,
    url: str,
    service_role_key: str,

    payload=None,

    prefer:
        str | None = None,

) -> object:

    headers = {
        "apikey":
            service_role_key,

        "Authorization":
            (
                "Bearer "
                + service_role_key
            ),

        "Content-Type":
            "application/json",
    }


    if prefer:

        headers[
            "Prefer"
        ] = prefer


    body = None


    if payload is not None:

        body = json.dumps(
            payload
        ).encode(
            "utf-8"
        )


    request = Request(
        url=
            url,

        data=
            body,

        headers=
            headers,

        method=
            method,
    )


    try:

        with urlopen(
            request,
            timeout=15,
        ) as response:

            raw = (
                response
                .read()
                .decode(
                    "utf-8"
                )
            )


            if not raw.strip():

                return {}


            return json.loads(
                raw
            )


    except HTTPError as exc:

        raw = (
            exc.read()
            .decode(
                "utf-8",
                errors="replace",
            )
        )


        raise RuntimeError(
            (
                f"HTTP {exc.code} "
                f"from {url}\n\n"
                f"{raw}"
            )
        ) from exc


    except URLError as exc:

        raise RuntimeError(
            (
                "Could not reach local "
                f"Supabase at {url}: "
                f"{exc}"
            )
        ) from exc


def list_auth_users(
    *,
    api_url: str,
    service_role_key: str,
) -> list[dict]:

    query = urlencode(
        {
            "page":
                1,

            "per_page":
                1000,
        }
    )


    response = request_json(
        method=
            "GET",

        url=(
            f"{api_url}"
            "/auth/v1/admin/users?"
            + query
        ),

        service_role_key=
            service_role_key,
    )


    if isinstance(
        response,
        dict,
    ):

        users = response.get(
            "users",
            [],
        )


        if isinstance(
            users,
            list,
        ):

            return users


    if isinstance(
        response,
        list,
    ):

        return response


    raise RuntimeError(
        (
            "Unexpected response while "
            "listing Supabase Auth users."
        )
    )


def find_auth_user(
    *,
    api_url: str,
    service_role_key: str,
    email: str,
) -> dict | None:

    target = (
        email
        .strip()
        .casefold()
    )


    users = list_auth_users(
        api_url=
            api_url,

        service_role_key=
            service_role_key,
    )


    for user in users:

        candidate = str(
            user.get(
                "email",
                "",
            )
        ).strip().casefold()


        if candidate == target:

            return user


    return None


def create_auth_user(
    *,
    api_url: str,
    service_role_key: str,

    email: str,
    password: str,
    name: str,
) -> dict:

    response = request_json(
        method=
            "POST",

        url=(
            f"{api_url}"
            "/auth/v1/admin/users"
        ),

        service_role_key=
            service_role_key,

        payload={
            "email":
                email,

            "password":
                password,

            "email_confirm":
                True,

            "user_metadata": {
                "name":
                    name,
            },
        },
    )


    if not isinstance(
        response,
        dict,
    ):

        raise RuntimeError(
            (
                "Unexpected response while "
                "creating Auth user."
            )
        )


    # Depending on Auth version, the response
    # may be either the user object directly
    # or wrapped inside {"user": {...}}.

    user = response.get(
        "user"
    )


    if isinstance(
        user,
        dict,
    ):

        return user


    if response.get(
        "id"
    ):

        return response


    raise RuntimeError(
        (
            "Supabase created no usable "
            "Auth user object."
        )
    )


def ensure_auth_user(
    *,
    api_url: str,
    service_role_key: str,

    email: str,
    password: str,
    name: str,
) -> dict:

    existing = find_auth_user(
        api_url=
            api_url,

        service_role_key=
            service_role_key,

        email=
            email,
    )


    if existing is not None:

        print(
            (
                "[bootstrap] Auth user "
                "already exists."
            )
        )

        return existing


    print(
        (
            "[bootstrap] Creating "
            "Supabase Auth user..."
        )
    )


    return create_auth_user(
        api_url=
            api_url,

        service_role_key=
            service_role_key,

        email=
            email,

        password=
            password,

        name=
            name,
    )


def upsert_staff_profile(
    *,
    api_url: str,
    service_role_key: str,

    user_id: str,
    email: str,
    name: str,
    role: str,
) -> dict:

    response = request_json(
        method=
            "POST",

        url=(
            f"{api_url}"
            "/rest/v1/users"
            "?on_conflict=id"
        ),

        service_role_key=
            service_role_key,

        prefer=(
            "resolution=merge-duplicates,"
            "return=representation"
        ),

        payload={
            "id":
                user_id,

            "role":
                role,

            "name":
                name,

            "email":
                email,

            "status":
                "ACTIVE",
        },
    )


    if isinstance(
        response,
        list,
    ):

        if not response:

            raise RuntimeError(
                (
                    "Staff profile upsert "
                    "returned no row."
                )
            )


        return response[
            0
        ]


    if isinstance(
        response,
        dict,
    ):

        return response


    raise RuntimeError(
        (
            "Unexpected response while "
            "upserting public.users."
        )
    )


def parse_arguments():

    parser = argparse.ArgumentParser(
        description=(
            "Create or restore a local "
            "SupportPilot staff account."
        )
    )


    parser.add_argument(
        "--email",

        default=
            DEFAULT_EMAIL,
    )


    parser.add_argument(
        "--name",

        default=
            DEFAULT_NAME,
    )


    parser.add_argument(
        "--role",

        default=
            DEFAULT_ROLE,

        choices=
            sorted(
                VALID_ROLES
            ),
    )


    return parser.parse_args()


def main() -> None:

    args = parse_arguments()


    email = (
        args.email
        .strip()
        .casefold()
    )


    name = (
        args.name
        .strip()
    )


    role = (
        args.role
        .strip()
        .upper()
    )


    if not email:

        raise RuntimeError(
            "Staff email cannot be empty."
        )


    if not name:

        raise RuntimeError(
            "Staff name cannot be empty."
        )


    if role not in VALID_ROLES:

        raise RuntimeError(
            (
                "Unsupported role: "
                + role
            )
        )


    print(
        (
            "[bootstrap] Reading local "
            "Supabase configuration..."
        )
    )


    supabase = (
        load_supabase_environment()
    )


    existing = find_auth_user(
        api_url=
            supabase[
                "api_url"
            ],

        service_role_key=
            supabase[
                "service_role_key"
            ],

        email=
            email,
    )


    if existing is None:

        password = getpass.getpass(
            (
                "Local staff password "
                "(input hidden): "
            )
        )


        if len(
            password
        ) < 8:

            raise RuntimeError(
                (
                    "Use a local development "
                    "password with at least "
                    "8 characters."
                )
            )

    else:

        # Existing Auth account does not need its
        # password changed just to restore public.users.

        password = ""


    if existing is None:

        auth_user = (
            ensure_auth_user(
                api_url=
                    supabase[
                        "api_url"
                    ],

                service_role_key=
                    supabase[
                        "service_role_key"
                    ],

                email=
                    email,

                password=
                    password,

                name=
                    name,
            )
        )

    else:

        print(
            (
                "[bootstrap] Auth user "
                "already exists."
            )
        )

        auth_user = existing


    user_id = str(
        auth_user.get(
            "id",
            "",
        )
    ).strip()


    if not user_id:

        raise RuntimeError(
            (
                "Auth user response does "
                "not contain an id."
            )
        )


    print(
        (
            "[bootstrap] Upserting "
            "public.users staff profile..."
        )
    )


    profile = (
        upsert_staff_profile(
            api_url=
                supabase[
                    "api_url"
                ],

            service_role_key=
                supabase[
                    "service_role_key"
                ],

            user_id=
                user_id,

            email=
                email,

            name=
                name,

            role=
                role,
        )
    )


    print()
    print(
        "SupportPilot local staff ready."
    )

    print(
        f"  id:     {user_id}"
    )

    print(
        f"  email:  {email}"
    )

    print(
        f"  name:   {name}"
    )

    print(
        f"  role:   {role}"
    )

    print(
        (
            "  status: "
            + str(
                profile.get(
                    "status",
                    "ACTIVE",
                )
            )
        )
    )


if __name__ == "__main__":

    try:

        main()

    except Exception as exc:

        print(
            (
                "\nBootstrap failed:\n"
                + str(
                    exc
                )
            ),

            file=
                sys.stderr,
        )

        raise SystemExit(
            1
        )