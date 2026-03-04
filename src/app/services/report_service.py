from __future__ import annotations

from app.domain.models import SyncPlan


def render_sync_report(plan: SyncPlan) -> str:
    skip_tail = ""
    if plan.skipped:
        sample = "; ".join(
            f"{item.source_id} ({item.reason})"
            for item in plan.skipped[:3]
        )
        skip_tail = f", skipped={len(plan.skipped)} [{sample}]"

    return (
        f"Sync report for {plan.kind}: "
        f"source={plan.source_count}, current={plan.current_count}, "
        f"create={len(plan.to_create)}, update={len(plan.to_update)}, delete={len(plan.to_delete)}, "
        f"shards={len(plan.shards)}, dry_run={plan.dry_run}, full_resync={plan.force_full_resync}"
        f"{skip_tail}"
    )
