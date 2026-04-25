from __future__ import annotations

import argparse
import asyncio
import csv
import re
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

import httpx
import structlog

from app.core.config import get_settings
from app.schemas.webhook import IngestEvent
from app.tools.replay import encode_event, post_event

log = structlog.get_logger(__name__)

_EMAIL_RE = re.compile(r"^(?P<date>\d{8})_(?P<time>\d{6})_(?P<id>EMAIL-\d+)\.eml$")
_INVOICE_RE = re.compile(r"^(?P<date>\d{8})_(?P<dl>DL-\d+)_(?P<id>INV-\d+)\.pdf$")


@dataclass(frozen=True)
class BackfillEvent:
    sort_key: str
    event: IngestEvent


def iter_archive_events(
    data_root: Path,
    *,
    property_id: str = "LIE-001",
    start: date | None = None,
    end: date | None = None,
) -> Iterator[IngestEvent]:
    """Walk archive emails / invoices / bank in chronological order."""
    items: list[BackfillEvent] = []
    items.extend(_email_archive(data_root / "emails", property_id, start, end))
    items.extend(_invoice_archive(data_root / "rechnungen", property_id, start, end))
    items.extend(_bank_archive(data_root / "bank", property_id, start, end))
    items.sort(key=lambda e: e.sort_key)
    for item in items:
        yield item.event


def _email_archive(
    root: Path,
    property_id: str,
    start: date | None,
    end: date | None,
) -> list[BackfillEvent]:
    if not root.is_dir():
        return []
    out: list[BackfillEvent] = []
    for path in sorted(root.glob("*/*.eml")):
        match = _EMAIL_RE.match(path.name)
        if match is None:
            continue
        d = _parse_date(match["date"])
        if not _in_window(d, start, end):
            continue
        sort_key = f"{match['date']}T{match['time']}"
        event = IngestEvent(
            event_id=match["id"],
            event_type="email",
            property_id=property_id,
            source_path=path,
            payload={},
        )
        out.append(BackfillEvent(sort_key=sort_key, event=event))
    return out


def _invoice_archive(
    root: Path,
    property_id: str,
    start: date | None,
    end: date | None,
) -> list[BackfillEvent]:
    if not root.is_dir():
        return []
    out: list[BackfillEvent] = []
    for path in sorted(root.glob("*/*.pdf")):
        match = _INVOICE_RE.match(path.name)
        if match is None:
            continue
        d = _parse_date(match["date"])
        if not _in_window(d, start, end):
            continue
        sort_key = f"{match['date']}T080000"
        event = IngestEvent(
            event_id=match["id"],
            event_type="invoice",
            property_id=property_id,
            source_path=path,
            payload={"dienstleister_id": match["dl"]},
        )
        out.append(BackfillEvent(sort_key=sort_key, event=event))
    return out


def _bank_archive(
    root: Path,
    property_id: str,
    start: date | None,
    end: date | None,
) -> list[BackfillEvent]:
    index = root / "bank_index.csv"
    if not index.is_file():
        return []
    out: list[BackfillEvent] = []
    with index.open("r", encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            datum = row.get("datum") or ""
            try:
                d = date.fromisoformat(datum)
            except ValueError:
                continue
            if not _in_window(d, start, end):
                continue
            sort_key = f"{d.strftime('%Y%m%d')}T120000"
            event = IngestEvent(
                event_id=row["id"],
                event_type="bank",
                property_id=property_id,
                source_path=index,
                payload={"row": dict(row)},
            )
            out.append(BackfillEvent(sort_key=sort_key, event=event))
    return out


def _parse_date(yyyymmdd: str) -> date:
    return date(int(yyyymmdd[:4]), int(yyyymmdd[4:6]), int(yyyymmdd[6:8]))


def _in_window(d: date, start: date | None, end: date | None) -> bool:
    if start is not None and d < start:
        return False
    return not (end is not None and d > end)


async def backfill(
    client: httpx.AsyncClient,
    data_root: Path,
    *,
    secret: str,
    base_url: str = "",
    property_id: str = "LIE-001",
    start: date | None = None,
    end: date | None = None,
    limit: int | None = None,
    rate_per_sec: float = 0.0,
) -> list[httpx.Response]:
    url = f"{base_url}/api/v1/webhook/ingest"
    delay = 1.0 / rate_per_sec if rate_per_sec > 0 else 0.0
    responses: list[httpx.Response] = []
    for idx, event in enumerate(
        iter_archive_events(data_root, property_id=property_id, start=start, end=end)
    ):
        if limit is not None and idx >= limit:
            break
        body = encode_event(event)
        response = await post_event(client, url=url, body=body, secret=secret)
        responses.append(response)
        log.info(
            "backfill_post",
            event_id=event.event_id,
            event_type=event.event_type,
            status=response.status_code,
        )
        if delay:
            await asyncio.sleep(delay)
    return responses


async def _run_cli(args: argparse.Namespace) -> int:
    settings = get_settings()
    secret = args.secret or settings.webhook_hmac_secret
    if not secret:
        raise SystemExit("missing webhook secret: pass --secret or set APP_WEBHOOK_HMAC_SECRET")
    if not args.data_root.is_dir():
        raise SystemExit(f"data root not found: {args.data_root}")

    start = _parse_iso(args.start) if args.start else None
    end = _parse_iso(args.end) if args.end else None

    async with httpx.AsyncClient(timeout=args.timeout) as client:
        responses = await backfill(
            client,
            args.data_root,
            secret=secret,
            base_url=args.base_url.rstrip("/"),
            property_id=args.property_id,
            start=start,
            end=end,
            limit=args.limit,
            rate_per_sec=args.rate,
        )
    failed = [r for r in responses if r.status_code >= httpx.codes.BAD_REQUEST]
    log.info("backfill_done", posted=len(responses), failed=len(failed))
    return 0 if not failed else 1


def _parse_iso(value: str) -> date:
    return datetime.fromisoformat(value).date()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Chronological backfill of archive into /webhook/ingest."
    )
    parser.add_argument("--data-root", type=Path, default=Path("data"))
    parser.add_argument("--base-url", type=str, default="http://localhost:8000")
    parser.add_argument("--secret", type=str, default=None)
    parser.add_argument("--property-id", type=str, default="LIE-001")
    parser.add_argument("--start", type=str, default=None, help="ISO start date (inclusive).")
    parser.add_argument("--end", type=str, default=None, help="ISO end date (inclusive).")
    parser.add_argument(
        "--limit",
        type=int,
        default=200,
        help="Max events to post (default 200 for demo cost control).",
    )
    parser.add_argument(
        "--rate",
        type=float,
        default=0.0,
        help="Max events per second (0 = unlimited).",
    )
    parser.add_argument("--timeout", type=float, default=30.0)
    args = parser.parse_args()
    raise SystemExit(asyncio.run(_run_cli(args)))


if __name__ == "__main__":
    main()


__all__ = ["backfill", "iter_archive_events"]
