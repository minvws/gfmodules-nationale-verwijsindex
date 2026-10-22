"""
One-off copy of the nvi-beheer-api data (separate database, public schema) into the admin schema of the NVI database.

Runs after migrate_db.sh. Requires DSN (target, NVI database) and SOURCE_DSN (nvi_beheer_api_db). Without SOURCE_DSN
nothing happens. The copy runs in a single transaction and is recorded in the migrations table, so it runs only once.
"""

import os
import sys

import psycopg

MARKER = "beheer-data-copy"

# In foreign key order
TABLES = [
    "organizations",
    "scopes",
    "clients",
    "certificates",
    "sources",
    "organizations_scopes",
    "clients_scopes",
    "clients_certificates",
    "clients_sources",
]


class CopyError(Exception):
    pass


def columns(conn: psycopg.Connection, table: str) -> list[str]:
    rows = conn.execute(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_schema = 'admin' AND table_name = %s ORDER BY ordinal_position",
        (table,),
    ).fetchall()
    return [row[0] for row in rows]


def count(conn: psycopg.Connection, schema: str, table: str) -> int:
    row = conn.execute(f'SELECT count(*) FROM {schema}."{table}"').fetchone()
    return row[0] if row else 0


def copy_table(source: psycopg.Connection, target: psycopg.Connection, table: str) -> None:
    cols = ", ".join(f'"{c}"' for c in columns(target, table))
    with (
        source.cursor().copy(f'COPY (SELECT {cols} FROM public."{table}") TO STDOUT') as src,
        target.cursor().copy(f'COPY admin."{table}" ({cols}) FROM STDIN') as dst,
    ):
        for block in src:
            dst.write(block)


def report_referrals(target: psycopg.Connection) -> None:
    without_org, only_deleted = target.execute(
        """
        SELECT
            count(*) FILTER (WHERE NOT EXISTS (
                SELECT 1 FROM admin.organizations o WHERE o.external_id = r.ura_number)),
            count(*) FILTER (WHERE EXISTS (
                SELECT 1 FROM admin.organizations o WHERE o.external_id = r.ura_number)
                AND NOT EXISTS (
                SELECT 1 FROM admin.organizations o WHERE o.external_id = r.ura_number AND o.deleted_at IS NULL))
        FROM public.referrals r
        """
    ).fetchone() or (0, 0)
    print(f"Referrals without any organization: {without_org}")
    print(f"Referrals with only deleted organizations: {only_deleted}")


def main() -> int:
    target_dsn = os.environ.get("DSN")
    source_dsn = os.environ.get("SOURCE_DSN")
    if not target_dsn:
        print("DSN is not set", file=sys.stderr)
        return 1
    if not source_dsn:
        print("SOURCE_DSN is not set, skipping beheer data copy")
        return 0

    try:
        copy(target_dsn, source_dsn)
    except CopyError as e:
        print(e, file=sys.stderr)
        return 1
    return 0


def copy(target_dsn: str, source_dsn: str) -> None:
    # Raising inside the connection blocks rolls back the transaction
    with psycopg.connect(target_dsn) as target, psycopg.connect(source_dsn) as source:
        target.execute("SELECT pg_advisory_xact_lock(hashtext(%s))", (MARKER,))
        if target.execute("SELECT 1 FROM migrations WHERE name = %s", (MARKER,)).fetchone():
            print("Beheer data already copied, skipping")
            return

        not_empty = [t for t in TABLES if t != "scopes" and count(target, "admin", t) > 0]
        if not_empty:
            raise CopyError(f"Target admin tables are not empty: {', '.join(not_empty)}")

        source.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")

        # Scopes are seeded by 026, replace them with the source rows so ids match
        target.execute("DELETE FROM admin.scopes")

        for table in TABLES:
            copy_table(source, target, table)
            expected, actual = count(source, "public", table), count(target, "admin", table)
            if expected != actual:
                raise CopyError(f"{table}: copied {actual} rows, expected {expected}")
            print(f"{table}: {actual} rows")

        target.execute(
            "SELECT setval(pg_get_serial_sequence('admin.scopes', 'id'), coalesce(max(id), 0) + 1, false) "
            "FROM admin.scopes"
        )
        report_referrals(target)
        target.execute("INSERT INTO migrations (name, checksum) VALUES (%s, %s)", (MARKER, "-"))

    print("Beheer data copied")


if __name__ == "__main__":
    sys.exit(main())
