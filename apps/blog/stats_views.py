"""
Async stats endpoint.

Why async?
----------
This view makes two independent HTTP requests to external APIs
(exchange rates and current time).  Doing them sequentially would
mean waiting for the first one to finish before starting the second,
so total latency = t1 + t2.

Using ``asyncio.gather`` fires both requests concurrently, so
total latency ≈ max(t1, t2) — the slowest of the two.  For I/O-bound
work this is free parallelism: no threads, no processes, just the
event loop switching while awaiting network responses.

If this were written synchronously every caller would block a
Django worker thread for t1 + t2 milliseconds, limiting throughput.
"""
import asyncio
import logging

import httpx
from django.contrib.auth import get_user_model
from django.http import JsonResponse

from drf_spectacular.utils import OpenApiExample, OpenApiResponse, extend_schema
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny

from .models import Comment, Post


logger = logging.getLogger("blog")

EXCHANGE_RATES_URL = "https://open.er-api.com/v6/latest/USD"
ALMATY_TIME_URL = "https://timeapi.io/api/time/current/zone?timeZone=Asia/Almaty"
TIMEOUT_SECONDS = 10.0
CURRENCIES = ("KZT", "RUB", "EUR")


@extend_schema(
    tags=["Stats"],
    summary="Blog statistics and external data",
    description="""
    Returns blog statistics (post / comment / user counts) combined with
    live data from two external public APIs fetched **concurrently** via
    ``asyncio.gather``.

    * **exchange_rates** — USD-based rates for KZT, RUB, EUR from
      open.er-api.com
    * **current_time** — current date/time in Asia/Almaty from
      timeapi.io

    No authentication required.
    """,
    responses={
        200: OpenApiResponse(
            description="Statistics returned successfully",
            examples=[
                OpenApiExample(
                    "Stats response",
                    value={
                        "blog": {
                            "total_posts": 42,
                            "total_comments": 137,
                            "total_users": 15,
                        },
                        "exchange_rates": {
                            "KZT": 450.23,
                            "RUB": 89.10,
                            "EUR": 0.92,
                        },
                        "current_time": "2024-03-15T18:30:00+05:00",
                    },
                    response_only=True,
                )
            ],
        ),
        502: OpenApiResponse(description="External API unavailable"),
    },
)
@api_view(["GET"])
@permission_classes([AllowAny])
def stats_view(request):
    """
    Sync DRF wrapper that drives the async implementation.

    asyncio.run() creates a fresh event loop for the async code and
    bridges the sync DRF layer with the async internal logic.  This
    keeps full drf-spectacular documentation support while still
    running the two HTTP calls concurrently inside _async_stats().
    """
    return asyncio.run(_async_stats())


async def _async_stats() -> JsonResponse:
    """Async core: DB counts + two external APIs all run concurrently."""
    User = get_user_model()

    # Django 4.1+ ships async ORM methods (acount, aget, etc.)
    # We run the three DB counts together with the external fetch.
    total_posts, total_comments, total_users, ext = await asyncio.gather(
        Post.objects.acount(),
        Comment.objects.acount(),
        User.objects.acount(),
        _fetch_external(),
    )

    exchange_rates, current_time = ext

    return JsonResponse(
        {
            "blog": {
                "total_posts": total_posts,
                "total_comments": total_comments,
                "total_users": total_users,
            },
            "exchange_rates": exchange_rates,
            "current_time": current_time,
        }
    )


async def _fetch_external() -> tuple:
    """
    Fire both external HTTP requests concurrently and return results.

    Returns (exchange_rates_dict, current_time_str).
    Falls back gracefully if either API is unreachable.
    """
    async with httpx.AsyncClient(timeout=TIMEOUT_SECONDS) as client:
        rates_resp, time_resp = await asyncio.gather(
            client.get(EXCHANGE_RATES_URL),
            client.get(ALMATY_TIME_URL),
        )

    # Exchange rates
    try:
        rates_data = rates_resp.json()
        all_rates = rates_data.get("rates", {})
        exchange_rates = {c: all_rates.get(c) for c in CURRENCIES}
    except Exception:
        logger.exception("Failed to parse exchange rates response")
        exchange_rates = {c: None for c in CURRENCIES}

    # Current Almaty time
    try:
        current_time = time_resp.json().get("dateTime", "")
    except Exception:
        logger.exception("Failed to parse time API response")
        current_time = ""

    return exchange_rates, current_time