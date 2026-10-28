# Alembic templates

Run from the repository root:

```bash
alembic -c src/database/migrations/alembic/alembic.ini upgrade head
```

Set `DATABASE_URL` to a sync-compatible URL override via `sqlalchemy.url` if needed;
`env.py` converts the async URL from the app settings to a sync driver.
