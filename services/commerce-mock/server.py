import json

from http import HTTPStatus
from http.server import (
    BaseHTTPRequestHandler,
    ThreadingHTTPServer,
)

from pathlib import Path

from urllib.parse import (
    parse_qs,
    urlparse,
)


ROOT = Path(__file__).resolve().parent

ORDERS_PATH = (
    ROOT
    / "fixtures"
    / "orders.json"
)


def load_orders() -> list[dict]:
    return json.loads(
        ORDERS_PATH.read_text(
            encoding="utf-8"
        )
    )


ORDERS = load_orders()


class CommerceHandler(
    BaseHTTPRequestHandler
):
    server_version = (
        "SupportPilotCommerceMock/1.0"
    )


    def _json(
        self,
        *,
        status: int,
        payload: dict,
    ) -> None:

        body = json.dumps(
            payload,
            separators=(
                ",",
                ":",
            ),
        ).encode(
            "utf-8"
        )

        self.send_response(
            status
        )

        self.send_header(
            "Content-Type",
            "application/json",
        )

        self.send_header(
            "Content-Length",
            str(
                len(body)
            ),
        )

        self.end_headers()

        self.wfile.write(
            body
        )


    def do_GET(
        self,
    ) -> None:

        parsed = urlparse(
            self.path
        )


        if (
            parsed.path
            == "/health/live"
        ):
            self._json(
                status=
                    HTTPStatus.OK,

                payload={
                    "status":
                        "ok",
                },
            )

            return


        if (
            parsed.path
            != "/v1/orders/lookup"
        ):
            self._json(
                status=
                    HTTPStatus.NOT_FOUND,

                payload={
                    "detail":
                        "not found",
                },
            )

            return


        query = parse_qs(
            parsed.query,
            keep_blank_values=True,
        )


        customer_ids = (
            query.get(
                "customer_id"
            )
            or []
        )

        order_numbers = (
            query.get(
                "order_number"
            )
            or []
        )


        if (
            len(customer_ids) != 1
            or len(order_numbers) != 1
        ):
            self._json(
                status=
                    HTTPStatus.BAD_REQUEST,

                payload={
                    "detail":
                        (
                            "customer_id and "
                            "order_number are required"
                        ),
                },
            )

            return


        customer_id = (
            customer_ids[0]
            .strip()
        )

        order_number = (
            order_numbers[0]
            .strip()
        )


        order = next(
            (
                candidate
                for candidate
                in ORDERS

                if (
                    candidate.get(
                        "customer_id"
                    )
                    == customer_id

                    and candidate.get(
                        "order_number"
                    )
                    == order_number
                )
            ),

            None,
        )


        # Intentionally identical response for:
        # - unknown order
        # - order belonging to another customer
        #
        # The caller must not learn whether an order exists
        # outside the supplied customer scope.
        if order is None:

            self._json(
                status=
                    HTTPStatus.NOT_FOUND,

                payload={
                    "detail":
                        (
                            "order not found "
                            "for customer"
                        ),
                },
            )

            return


        self._json(
            status=
                HTTPStatus.OK,

            payload=
                order,
        )


    def log_message(
        self,
        format: str,
        *args,
    ) -> None:

        print(
            (
                f"{self.client_address[0]} "
                + (
                    format
                    % args
                )
            ),
            flush=True,
        )


def main() -> None:

    server = ThreadingHTTPServer(
        (
            "0.0.0.0",
            8080,
        ),
        CommerceHandler,
    )

    print(
        (
            "SupportPilot commerce mock "
            "listening on 0.0.0.0:8080"
        ),
        flush=True,
    )

    server.serve_forever()


if __name__ == "__main__":
    main()