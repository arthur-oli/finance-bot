import os
import psycopg2
import structlog

log = structlog.get_logger()

_SCHEMA_CANDIDATES = [
    "/app/schema.sql",                                                              # Docker (copied by wizard before deploy)
    os.path.join(os.path.dirname(__file__), "..", "..", "schema.sql"),              # backend/schema.sql
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "schema.sql"),        # project root (local dev)
]


def apply_schema():
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        log.warning("migrations.skipped", reason="DATABASE_URL not set")
        return

    schema_path = None
    for candidate in _SCHEMA_CANDIDATES:
        if os.path.exists(candidate):
            schema_path = os.path.abspath(candidate)
            break

    if not schema_path:
        log.error("migrations.schema_not_found", candidates=_SCHEMA_CANDIDATES)
        return

    with open(schema_path, encoding="utf-8") as f:
        sql = f.read()

    try:
        conn = psycopg2.connect(db_url)
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute(sql)
        conn.close()
        log.info("migrations.applied", schema=schema_path)
    except Exception as e:
        log.error("migrations.error", error=str(e))
