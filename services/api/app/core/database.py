from contextlib import contextmanager
from typing import Iterator

import psycopg

from app.core.config import settings


@contextmanager
def get_database_connection() -> Iterator[psycopg.Connection]:
    """
    Open an application database connection.

    Transaction boundaries remain the responsibility of the
    calling service.
    """
    with psycopg.connect(
        settings.database_url,
        connect_timeout=5,
    ) as connection:
        yield connection


def check_database_readiness() -> dict[str, bool]:
    """
    Verify that PostgreSQL is reachable and pgvector exists.

    No application data is modified.
    """
    with psycopg.connect(
        settings.database_url,
        connect_timeout=3,
    ) as connection:
        with connection.cursor() as cursor:
            cursor.execute("select 1;")

            database_ready = (
                cursor.fetchone()[0] == 1
            )

            cursor.execute(
                """
                select exists (
                    select 1
                    from pg_extension
                    where extname = 'vector'
                );
                """
            )

            pgvector_ready = bool(
                cursor.fetchone()[0]
            )

    return {
        "database": database_ready,
        "pgvector": pgvector_ready,
    }