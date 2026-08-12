import json

from functools import lru_cache
from typing import Protocol

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

from app.core.config import (
    settings,
)

from app.schemas.commerce import (
    CommerceOrder,
)


class CommerceConfigurationError(
    RuntimeError
):
    pass


class CommerceProviderError(
    RuntimeError
):
    pass


class CommerceProvider(
    Protocol
):
    provider_name: str

    def lookup_order(
        self,
        *,
        customer_external_id: str,
        order_number: str,
    ) -> CommerceOrder | None:
        ...


class MockCommerceProvider:
    provider_name = (
        "northstar-commerce-mock"
    )


    def __init__(
        self,
        *,
        base_url: str,
        timeout_seconds: int,
    ) -> None:

        self.base_url = (
            base_url.rstrip("/")
        )

        self.timeout_seconds = (
            timeout_seconds
        )


    def lookup_order(
        self,
        *,
        customer_external_id: str,
        order_number: str,
    ) -> CommerceOrder | None:

        query = urlencode(
            {
                "customer_id":
                    customer_external_id,

                "order_number":
                    order_number,
            }
        )


        url = (
            self.base_url
            + "/v1/orders/lookup?"
            + query
        )


        request = Request(
            url,
            method="GET",
            headers={
                "Accept":
                    "application/json",
            },
        )


        try:

            with urlopen(
                request,
                timeout=
                    self.timeout_seconds,
            ) as response:

                payload = json.loads(
                    response
                    .read()
                    .decode(
                        "utf-8"
                    )
                )


        except HTTPError as exc:

            if exc.code == 404:
                return None

            raise CommerceProviderError(
                (
                    "Commerce provider request "
                    f"failed with HTTP {exc.code}."
                )
            ) from exc


        except (
            URLError,
            TimeoutError,
        ) as exc:

            raise CommerceProviderError(
                (
                    "Commerce provider "
                    "is unavailable."
                )
            ) from exc


        except json.JSONDecodeError as exc:

            raise CommerceProviderError(
                (
                    "Commerce provider returned "
                    "invalid JSON."
                )
            ) from exc


        try:
            order = (
                CommerceOrder
                .model_validate(
                    payload
                )
            )

        except Exception as exc:

            raise CommerceProviderError(
                (
                    "Commerce provider returned "
                    "an invalid order contract."
                )
            ) from exc


        # Defense in depth:
        # never trust an upstream provider response
        # that escapes the requested customer/order scope.
        if (
            order.customer_id
            != customer_external_id

            or order.order_number
            != order_number
        ):
            raise CommerceProviderError(
                (
                    "Commerce provider returned "
                    "an out-of-scope order."
                )
            )


        return order


@lru_cache(
    maxsize=1,
)
def get_commerce_provider(
) -> CommerceProvider:

    provider_name = (
        settings
        .commerce_provider
        .strip()
        .lower()
    )


    if provider_name == "mock":

        return MockCommerceProvider(
            base_url=
                settings
                .commerce_mock_base_url,

            timeout_seconds=
                settings
                .commerce_timeout_seconds,
        )


    raise CommerceConfigurationError(
        (
            "Unsupported commerce provider: "
            f"{provider_name}"
        )
    )