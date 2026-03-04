from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

import httpx

from app.config import settings
from app.logging import configure_logging
from app.providers.seventv import SevenTVProvider
from app.providers.telegram import TelegramProvider
from app.services.report_service import render_sync_report
from app.services.sync_service import SyncService


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m app.main")
    subparsers = parser.add_subparsers(dest="command", required=True)

    sync_parser = subparsers.add_parser("sync", help="Synchronize SevenTV emotes to Telegram")
    sync_parser.add_argument("--dry-run", action="store_true", help="Run without applying changes")
    sync_parser.add_argument(
        "--kind",
        choices=["emoji", "stickers"],
        help="Synchronize only a specific kind",
    )
    sync_parser.add_argument(
        "--force-full-resync",
        action="store_true",
        help="Force update even if item checksum did not change",
    )
    sync_parser.add_argument("--max-items", type=int, default=0, help="Limit number of source items per kind")
    sync_parser.add_argument("--report-path", default="report.json", help="Path to sync report artifact")
    sync_parser.add_argument(
        "--desired-state-path",
        default="desired-state.json",
        help="Path to desired state artifact",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    configure_logging()
    logger = logging.getLogger(__name__)

    if args.command == "sync":
        settings.validate_required()
        seventv = SevenTVProvider(
            seventv_user_id=settings.seventv_user_id,
            client=httpx.Client(timeout=10.0),
        )
        telegram = TelegramProvider()
        service = SyncService(seventv=seventv, telegram=telegram)

        kinds = [args.kind] if args.kind else ["emoji", "stickers"]
        plans = []
        for kind in kinds:
            plan = service.run(
                kind=kind,
                dry_run=args.dry_run,
                force_full_resync=args.force_full_resync,
                max_items=args.max_items if args.max_items > 0 else None,
            )
            plans.append(plan)
            logger.info(render_sync_report(plan))

        report_path = Path(args.report_path)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_payload = {
            "plans": [plan.model_dump(mode="json") for plan in plans],
            "totals": {
                "source": sum(plan.source_count for plan in plans),
                "current": sum(plan.current_count for plan in plans),
                "create": sum(len(plan.to_create) for plan in plans),
                "update": sum(len(plan.to_update) for plan in plans),
                "delete": sum(len(plan.to_delete) for plan in plans),
                "skipped": sum(len(plan.skipped) for plan in plans),
            },
        }
        report_path.write_text(json.dumps(report_payload, ensure_ascii=False, indent=2), encoding="utf-8")

        desired_state_path = Path(args.desired_state_path)
        desired_state_path.parent.mkdir(parents=True, exist_ok=True)
        desired_state_payload = {"shards": [shard.model_dump(mode="json") for plan in plans for shard in plan.shards]}
        desired_state_path.write_text(json.dumps(desired_state_payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
