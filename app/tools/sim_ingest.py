from __future__ import annotations

import argparse
import asyncio
import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from app.core.config import REPO_ROOT, Settings
from app.schemas.webhook import IngestEvent
from app.services.llm.client import get_llm_client
from app.services.supervisor import Supervisor


def _git_init(wiki_dir: Path) -> None:
    wiki_dir.mkdir(parents=True, exist_ok=True)
    if (wiki_dir / ".git").is_dir():
        return
    for cmd in (
        ["git", "init", "-q"],
        ["git", "config", "user.email", "sim@example.test"],
        ["git", "config", "user.name", "sim"],
        ["git", "config", "commit.gpgsign", "false"],
    ):
        subprocess.run(cmd, cwd=wiki_dir, check=True, capture_output=True)


def _build_settings(args: argparse.Namespace) -> tuple[Settings, Path]:
    if args.wiki_dir:
        wiki_dir = Path(args.wiki_dir).resolve()
        workspace = wiki_dir.parent
    else:
        workspace = Path(tempfile.mkdtemp(prefix="sim_ingest_"))
        wiki_dir = workspace / "wiki"
    _git_init(wiki_dir)

    overrides: dict[str, object] = {
        "wiki_dir": wiki_dir,
        "normalize_dir": workspace / "normalize",
        "output_dir": workspace / "output",
        "data_dir": Path(args.data_dir).resolve() if args.data_dir else REPO_ROOT / "data",
        "env": "dev",
    }
    if args.provider:
        overrides["llm_provider"] = args.provider
    settings = Settings(**overrides)
    return settings, workspace


async def _run(args: argparse.Namespace) -> int:
    settings, workspace = _build_settings(args)
    llm = get_llm_client(settings)
    sup = Supervisor(settings=settings, llm=llm)

    payload: dict[str, object] = {}
    if args.text:
        payload["text"] = args.text
    if args.payload_json:
        payload.update(json.loads(args.payload_json))

    event = IngestEvent(
        event_id=args.event_id,
        event_type=args.event_type,
        property_id=args.property_id,
        source_path=args.source_path,
        payload=payload,
    )

    print(f"workspace: {workspace}")
    print(f"wiki_dir:  {settings.wiki_dir}")
    print(f"provider:  {settings.llm_provider} (fast={settings.fast_model}, smart={settings.smart_model})")
    print(f"event:     {event.event_id} type={event.event_type} property={event.property_id}\n")

    t0 = time.time()
    result = await sup.handle(event)
    dt_ms = (time.time() - t0) * 1000

    print(f"=== RESULT ({dt_ms:.0f} ms) ===")
    print(f"status={result.status}")
    if result.classification:
        c = result.classification
        print(f"classify: signal={c.signal} category={c.category} priority={c.priority} confidence={c.confidence}")
    if result.patch:
        print(f"applied_ops={result.patch.applied_ops} commit={result.patch.commit_sha} idempotent={result.patch.idempotent}")
        print(f"touched: {list(result.patch.touched)}")

    root = settings.wiki_dir / event.property_id
    if root.is_dir() and result.patch:
        print(f"\n=== files under {root} ===")
        for rel in result.patch.touched:
            f = root / rel
            if not f.is_file():
                continue
            print(f"\n--- {rel} ---")
            print(f.read_text(encoding="utf-8").rstrip())

    git_log = subprocess.run(
        ["git", "log", "--oneline", "-n", "5"],
        cwd=settings.wiki_dir,
        capture_output=True,
        text=True,
        check=False,
    )
    if git_log.stdout.strip():
        print("\n=== git log ===")
        print(git_log.stdout.rstrip())

    return 0 if result.status in {"applied", "no_signal"} else 1


def _parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Simulate one ingest event end-to-end.")
    p.add_argument("--event-id", required=True)
    p.add_argument("--event-type", default="manual",
                   help="manual|email|invoice|bank|letter|document|chat|... (default: manual)")
    p.add_argument("--property-id", default="LIE-001")
    p.add_argument("--text", help="free-text payload (used by manual/chat handlers)")
    p.add_argument("--source-path", help="repo-relative path to source file (.eml, .pdf, ...)")
    p.add_argument("--payload-json", help="extra JSON merged into event.payload")
    p.add_argument("--wiki-dir", help="wiki dir (default: fresh tmp dir per run)")
    p.add_argument("--data-dir", help="data dir (default: repo data/)")
    p.add_argument("--provider", choices=["gemini", "anthropic", "fake"],
                   help="override APP_LLM_PROVIDER")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    return asyncio.run(_run(_parse_args(argv if argv is not None else sys.argv[1:])))


if __name__ == "__main__":
    raise SystemExit(main())
