from __future__ import annotations

import argparse
import logging

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
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    configure_logging()
    logger = logging.getLogger(__name__)

    if args.command == "sync":
        if not settings.seventv_user_id:
            raise RuntimeError("SEVENTV_USER_ID is required")
        seventv = SevenTVProvider(
            seventv_user_id=settings.seventv_user_id,
            client=httpx.Client(timeout=10.0),
        )
        telegram = TelegramProvider()
        service = SyncService(seventv=seventv, telegram=telegram)

        kinds = [args.kind] if args.kind else ["emoji", "stickers"]
        for kind in kinds:
            plan = service.run(
                kind=kind,
                dry_run=args.dry_run,
                force_full_resync=args.force_full_resync,
            )
            logger.info(render_sync_report(plan))
        return 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
