# CallAssist Pro

Telegram AI assistant for customer-support teams: subscriptions (Free/Pro/Enterprise, mock Stripe),
OpenAI script generation (gpt-4o-mini, cost tracked), voicemail/callback management via a
**lawful SIP simulator**, TTS (ElevenLabs with Amazon Polly fallback), audit logging, rate limiting.
Built with Python 3.11+, Aiogram v3, FastAPI and async SQLAlchemy.

## Compliance
No caller-ID spoofing, no credential/OTP/2FA collection; the SIP simulator only logs and notifies.
All user actions are audited. GDPR: `/mydata` exports and `/deleteme` erases user data
(also `GET/DELETE /admin/users/{id}`). No data is sold or shared.

## Quick start
```bash
cp .env.example .env        # set TELEGRAM_BOT_TOKEN, OPENAI_API_KEY, ...
pip install -r requirements.txt
python -m src.bot.main                       # bot (long polling, SQLite by default)
uvicorn src.api.app:app --port 8000          # API + webhook; docs at /docs
```

## Docker
`docker compose up --build` starts PostgreSQL, the bot and the API.

## Replit
Import the repo, add the variables from `.env.example` as Secrets, install with
`pip install -r requirements.txt`, and press Run (`.replit` runs the bot with SQLite).

## Migrations
`src/database/migrations/init.sql` holds the SQLite schema; Alembic templates are in
`src/database/migrations/alembic` (`alembic -c src/database/migrations/alembic/alembic.ini upgrade head`;
PostgreSQL migrations additionally need `psycopg2-binary`). Tables are auto-created on startup in development.

## Bot commands
`/start /plan /script <topic> /voice <id> /voicemail [number] /callback <number> /history /mydata /deleteme /stats (admin)`

## Webhook mode
Set `TELEGRAM_WEBHOOK_URL` and `TELEGRAM_WEBHOOK_SECRET`; the API registers the webhook on startup
and serves `POST /webhook/telegram`. Admin endpoints require the `X-API-Key` header (`ADMIN_API_KEY`).

## Tests
`pytest` (coverage reported; CI enforces ≥80%).

## License
MIT
