"""Database schema creation and lightweight SQLite migrations.

Shared by the API server and the command-line sync script, so a sync run
against a fresh database initializes it the same way the server would.
"""
from sqlalchemy import text

from database import engine, Base
import models  # noqa: F401  -- registers every table on Base.metadata


def _add_column_if_missing(conn, table: str, column: str, ddl: str) -> None:
    existing = [row[1] for row in conn.execute(text(f"PRAGMA table_info({table})"))]
    if column not in existing:
        conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {ddl}"))


def init_db() -> None:
    """create_all plus the ALTERs it cannot perform on existing tables."""
    Base.metadata.create_all(bind=engine)

    with engine.connect() as conn:
        _add_column_if_missing(conn, "savings_goals", "category_id",
                               "category_id INTEGER REFERENCES categories(id)")
        _add_column_if_missing(conn, "transactions", "external_id", "external_id VARCHAR")
        _add_column_if_missing(conn, "transactions", "pending", "pending BOOLEAN DEFAULT 0")
        _add_column_if_missing(conn, "transactions", "is_transfer", "is_transfer BOOLEAN DEFAULT 0")
        _add_column_if_missing(conn, "categories", "is_transfer", "is_transfer BOOLEAN DEFAULT 0")
        _add_column_if_missing(conn, "accounts", "simplefin_account_id", "simplefin_account_id VARCHAR")
        _add_column_if_missing(conn, "accounts", "last_synced_at", "last_synced_at DATETIME")
        _add_column_if_missing(conn, "accounts", "net_worth_group",
                               "net_worth_group VARCHAR DEFAULT 'everyday'")

        # net_worth_group replaced an earlier include_in_net_worth boolean.
        # Carry those opt-outs over as long_term, then drop the old column so
        # it cannot be mistaken for the live one.
        existing = [row[1] for row in conn.execute(text("PRAGMA table_info(accounts)"))]
        if "include_in_net_worth" in existing:
            conn.execute(text(
                "UPDATE accounts SET net_worth_group = 'long_term' "
                "WHERE include_in_net_worth = 0 AND "
                "(net_worth_group IS NULL OR net_worth_group = 'everyday')"
            ))
            try:
                conn.execute(text("ALTER TABLE accounts DROP COLUMN include_in_net_worth"))
            except Exception:
                pass  # DROP COLUMN needs SQLite 3.35+; harmless to leave behind
        conn.execute(text(
            "UPDATE accounts SET net_worth_group = 'everyday' WHERE net_worth_group IS NULL"
        ))

        # Categories that have always meant "money between my own accounts"
        # keep that meaning now that it is a flag rather than a hardcoded name.
        conn.execute(text(
            "UPDATE categories SET is_transfer = 1 "
            "WHERE name IN ('Transfer', 'Credit Card Payment') AND is_transfer = 0"
        ))

        # SimpleFIN transaction ids are unique per account, not globally, so the
        # index is composite. SQLite treats NULLs as distinct, so CSV-imported
        # rows (external_id NULL) never collide under it.
        conn.execute(text(
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_transaction_account_external_id "
            "ON transactions (account_id, external_id)"
        ))
        conn.execute(text(
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_account_simplefin_id "
            "ON accounts (simplefin_account_id)"
        ))
        conn.commit()
