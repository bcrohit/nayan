"""Poll the navigation API on a fixed interval."""

from __future__ import annotations

import asyncio
import logging
import signal
from contextlib import suppress

import httpx

from config import get_settings

logger = logging.getLogger(__name__)


async def poll_navigate(client: httpx.AsyncClient, base_url: str) -> dict[str, str]:
    url = f"{base_url.rstrip('/')}/navigate?speak=true"
    response = await client.get(url)
    response.raise_for_status()
    return response.json()


async def wait_for_api(client: httpx.AsyncClient, base_url: str, stop: asyncio.Event) -> bool:
    health_url = f"{base_url.rstrip('/')}/health"
    while not stop.is_set():
        try:
            response = await client.get(health_url)
            if response.status_code == 200:
                logger.info("Navigation API is ready")
                return True
        except httpx.RequestError:
            pass
        await asyncio.sleep(1)
    return False


async def run_loop() -> None:
    settings = get_settings()
    base_url = settings.api_base_url
    interval = settings.poll_interval_seconds
    timeout = httpx.Timeout(settings.navigate_client_timeout_seconds)

    stop = asyncio.Event()

    def request_stop() -> None:
        logger.info("Shutdown requested")
        stop.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        with suppress(NotImplementedError):
            loop.add_signal_handler(sig, request_stop)

    async with httpx.AsyncClient(timeout=timeout) as client:
        if not await wait_for_api(client, base_url, stop):
            return

        while not stop.is_set():
            try:
                guidance = await poll_navigate(client, base_url)
                logger.info(
                    "action=%s speech=%r",
                    guidance.get("action"),
                    guidance.get("speech_text"),
                )
            except httpx.HTTPStatusError as exc:
                logger.warning(
                    "Navigation API error %s: %s",
                    exc.response.status_code,
                    exc.response.text,
                )
            except httpx.RequestError as exc:
                logger.warning("Navigation API unreachable: %s", exc)
            except Exception:
                logger.exception("Unexpected error during navigation poll")

            try:
                await asyncio.wait_for(stop.wait(), timeout=interval)
                break
            except TimeoutError:
                continue


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    asyncio.run(run_loop())


if __name__ == "__main__":
    main()
