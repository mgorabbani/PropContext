from __future__ import annotations

import argparse
import asyncio
import csv
import hashlib
import hmac
import json
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import anyio
import httpx
import structlog

from app.core.config import get_settings
from app.schemas.webhook import IngestEvent

log = structlog.get_logger(__name__)


@dataclass(frozen=True)
class ReplayEvent:
    sort_key: str
    event: IngestEvent


def iter_day_events(
    day_dir: Path,
    *,
    property_id: str = "LIE-001",
) -> Iterator[IngestEvent]:
    """Yield events for a day's delta in chronological order."""
    items: list[ReplayEvent] = []
    items.extend(_email_events(day_dir, property_id))
    items.extend(_invoice_events(day_dir, property_id))
    items.extend(_bank_events(day_dir, property_id))
    items.sort(key=lambda e: e.sort_key)
    for item in items:
        yield item.event


def _email_events(day_dir: Path, property_id: str) -> list[ReplayEvent]:
    index = day_dir / "emails_index.csv"
    if not index.is_file():
        return []
    out: list[ReplayEvent] = []
    for row in _read_csv(index):
        filename = row.get("filename")
        month = row.get("month_dir")
        if not filename or not month:
            continue
        source = day_dir / "emails" / month / filename
        sort_key = row.get("datetime") or row.get("id", "")
        event = IngestEvent(
            event_id=row["id"],
            event_type="email",
            property_id=property_id,
            source_path=source,
            payload={"category": row.get("category", ""), "thread_id": row.get("thread_id", "")},
        )
        out.append(ReplayEvent(sort_key=sort_key, event=event))
    return out


def _invoice_events(day_dir: Path, property_id: str) -> list[ReplayEvent]:
    index = day_dir / "rechnungen_index.csv"
    if not index.is_file():
        return []
    out: list[ReplayEvent] = []
    for row in _read_csv(index):
        filename = row.get("filename")
        month = row.get("month_dir")
        if not filename or not month:
            continue
        source = day_dir / "rechnungen" / month / filename
        sort_key = (row.get("datum") or "") + "T12:00:00"
        event = IngestEvent(
            event_id=row["id"],
            event_type="invoice",
            property_id=property_id,
            source_path=source,
            payload={
                "rechnungsnr": row.get("rechnungsnr", ""),
                "dienstleister_id": row.get("dienstleister_id", ""),
                "brutto": row.get("brutto", ""),
            },
        )
        out.append(ReplayEvent(sort_key=sort_key, event=event))
    return out


def _bank_events(day_dir: Path, property_id: str) -> list[ReplayEvent]:
    index = day_dir / "bank" / "bank_index.csv"
    if not index.is_file():
        return []
    out: list[ReplayEvent] = []
    for row in _read_csv(index):
        sort_key = (row.get("datum") or "") + "T12:00:00"
        event = IngestEvent(
            event_id=row["id"],
            event_type="bank",
            property_id=property_id,
            source_path=index,
            payload={"row": dict(row)},
        )
        out.append(ReplayEvent(sort_key=sort_key, event=event))
    return out


def _read_csv(path: Path) -> Iterator[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            yield {k: (v if v is not None else "") for k, v in row.items()}


def sign_body(body: bytes, secret: str) -> dict[str, str]:
    digest = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return {
        "x-propcontext-signature": f"sha256={digest}",
        "content-type": "application/json",
    }


def encode_event(event: IngestEvent) -> bytes:
    payload: dict[str, Any] = json.loads(event.model_dump_json())
    return json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")


async def post_event(
    client: httpx.AsyncClient,
    *,
    url: str,
    body: bytes,
    secret: str,
) -> httpx.Response:
    headers = sign_body(body, secret)
    return await client.post(url, content=body, headers=headers)


async def replay_day(
    client: httpx.AsyncClient,
    day_dir: Path,
    *,
    secret: str,
    base_url: str = "",
    property_id: str = "LIE-001",
    limit: int | None = None,
    rate_per_sec: float = 0.0,
) -> list[httpx.Response]:
    """Replay one day's delta. Returns posted responses."""
    url = f"{base_url}/api/v1/webhook/ingest"
    delay = 1.0 / rate_per_sec if rate_per_sec > 0 else 0.0
    responses: list[httpx.Response] = []
    for idx, event in enumerate(iter_day_events(day_dir, property_id=property_id)):
        if limit is not None and idx >= limit:
            break
        body = encode_event(event)
        response = await post_event(client, url=url, body=body, secret=secret)
        responses.append(response)
        log.info(
            "replay_post",
            event_id=event.event_id,
            event_type=event.event_type,
            status=response.status_code,
        )
        if delay:
            await anyio.sleep(delay)
    return responses


async def _run_cli(args: argparse.Namespace) -> int:
    settings = get_settings()
    secret = args.secret or settings.webhook_hmac_secret
    if not secret:
        raise SystemExit("missing webhook secret: pass --secret or set APP_WEBHOOK_HMAC_SECRET")

    day_dir = args.data_root / f"day-{args.day:02d}"
    if not day_dir.is_dir():
        raise SystemExit(f"day directory not found: {day_dir}")

    async with httpx.AsyncClient(timeout=args.timeout) as client:
        responses = await replay_day(
            client,
            day_dir,
            secret=secret,
            base_url=args.base_url.rstrip("/"),
            property_id=args.property_id,
            limit=args.limit,
            rate_per_sec=args.rate,
        )
    failed = [r for r in responses if r.status_code >= httpx.codes.BAD_REQUEST]
    log.info("replay_done", posted=len(responses), failed=len(failed))
    return 0 if not failed else 1


def main() -> None:
    parser = argparse.ArgumentParser(description="Replay an incremental day into /webhook/ingest.")
    parser.add_argument("--day", type=int, required=True, help="Day index, e.g. 1.")
    parser.add_argument(
        "--data-root",
        type=Path,
        default=Path("data/incremental"),
        help="Root containing day-NN/ directories.",
    )
    parser.add_argument("--base-url", type=str, default="http://localhost:8000")
    parser.add_argument("--secret", type=str, default=None)
    parser.add_argument("--property-id", type=str, default="LIE-001")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument(
        "--rate",
        type=float,
        default=0.0,
        help="Max events per second (0 = no rate limit).",
    )
    parser.add_argument("--timeout", type=float, default=30.0)
    args = parser.parse_args()
    raise SystemExit(asyncio.run(_run_cli(args)))


if __name__ == "__main__":
    main()


# Re-export for tests
__all__ = [
    "encode_event",
    "iter_day_events",
    "post_event",
    "replay_day",
    "sign_body",
]


# Convenience for callers wanting a parsed datetime sort key.
def _parse_dt(value: str) -> datetime:
    return datetime.fromisoformat(value)
