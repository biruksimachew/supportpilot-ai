from uuid import UUID

import psycopg

from fastapi.testclient import (
    TestClient,
)

from app.core.auth import (
    get_current_internal_user,
)

from app.core.config import (
    settings,
)

from app.main import app

from app.schemas.auth import (
    InternalUser,
)


client = TestClient(
    app
)


TEST_MANAGER_ID = UUID(
    "88888888-8888-4888-8888-888888888888"
)


def fake_manager() -> InternalUser:

    return InternalUser(
        id=
            TEST_MANAGER_ID,

        email=
            "dashboard-manager@test.local",

        name=
            "Dashboard Test Manager",

        role=
            "SUPPORT_MANAGER",
    )


def test_agent_dashboard_matches_database_state(
) -> None:

    app.dependency_overrides[
        get_current_internal_user
    ] = fake_manager


    try:

        response = client.get(
            "/api/v1/agent/dashboard"
        )


        assert (
            response.status_code
            == 200
        )


        result = (
            response.json()
        )


        with psycopg.connect(
            settings.database_url
        ) as connection:

            with connection.cursor() as cursor:

                cursor.execute(
                    """
                    select count(*)
                    from public.tickets
                    where status <> 'RESOLVED';
                    """
                )

                expected_open = (
                    cursor.fetchone()[0]
                )


                cursor.execute(
                    """
                    select count(*)
                    from public.ai_runs;
                    """
                )

                expected_ai_runs = (
                    cursor.fetchone()[0]
                )


                cursor.execute(
                    """
                    select count(*)
                    from public.outbound_deliveries;
                    """
                )

                expected_deliveries = (
                    cursor.fetchone()[0]
                )


        assert (
            result[
                "queue"
            ][
                "open_tickets"
            ]
            == expected_open
        )


        assert (
            result[
                "ai"
            ][
                "total_runs"
            ]
            == expected_ai_runs
        )


        assert (
            result[
                "delivery"
            ][
                "total_deliveries"
            ]
            == expected_deliveries
        )


        assert (
            sum(
                item["count"]

                for item
                in result[
                    "status_breakdown"
                ]
            )
            >= expected_open
        )


        if expected_ai_runs == 0:

            assert (
                result[
                    "ai"
                ][
                    "automation_rate_pct"
                ]
                is None
            )


        if expected_deliveries == 0:

            assert (
                result[
                    "delivery"
                ][
                    "delivery_success_rate_pct"
                ]
                is None
            )


    finally:

        app.dependency_overrides.clear()