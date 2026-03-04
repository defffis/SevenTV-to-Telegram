# SevenTV-to-Telegram

## Local run

1. Copy `.env.example` to `.env` and fill required values.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run sync:
   ```bash
   ./scripts/local_run.sh --dry-run
   ```

Artifacts are written to `artifacts/`:
- `report.json`
- `desired-state.json`
- `run.log`

## GitHub Actions secrets

Both workflows (`nightly-sync.yml` and `manual-sync.yml`) read configuration from `secrets` in the `production` environment.

Required secrets:
- `SEVENTV_USER_ID`
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_BOT_USERNAME`

Optional secrets (override defaults):
- `TELEGRAM_BOT_USER_ID`
- `TELEGRAM_SET_BASE_NAME`
- `TELEGRAM_API_BASE_URL`
- `TELEGRAM_MAX_RETRIES`
- `TELEGRAM_BACKOFF_SECONDS`
- `TELEGRAM_TIMEOUT_SECONDS`
- `SHARD_SIZE`
- `ENABLE_ANIMATED`
- `ENABLE_VIDEO`
