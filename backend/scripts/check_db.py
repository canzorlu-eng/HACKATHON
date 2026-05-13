"""
Database health check script.

Usage (from backend/ directory):
    python -m scripts.check_db

Checks:
  1. PostgreSQL connection and table existence (users, analyses)
  2. ChromaDB connection and reviews_v1 document count (optional)

Exit codes:
  0 — all checks passed
  1 — PostgreSQL check failed
  2 — ChromaDB unavailable (warning only, does not cause exit 1)
"""

import os
import sys


def check_postgres() -> bool:
    print("=== PostgreSQL Check ===")
    try:
        from app.config import get_settings
        from app.db import get_engine
        from sqlmodel import text

        s = get_settings()
        print(f"  host={s.postgres_host}:{s.postgres_port} db={s.postgres_db} user={s.postgres_user}")

        engine = get_engine()
        with engine.connect() as conn:
            # Verify connection
            result = conn.execute(text("SELECT 1")).scalar()
            assert result == 1
            print("  [OK] Connection established")

            # Check tables exist
            result = conn.execute(
                text(
                    "SELECT table_name FROM information_schema.tables "
                    "WHERE table_schema = 'public' AND table_name IN ('users', 'analyses')"
                )
            ).fetchall()
            existing = {row[0] for row in result}

            for table in ("users", "analyses"):
                if table in existing:
                    count = conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
                    print(f"  [OK] table '{table}' exists — {count} rows")
                else:
                    print(f"  [MISSING] table '{table}' — run startup or call create_db_tables()")

            if {"users", "analyses"} <= existing:
                print("  [OK] All required tables present")
                return True
            else:
                print("  [WARN] Some tables missing — run the app once to create them via lifespan hook")
                return False

    except Exception as exc:
        print(f"  [FAIL] PostgreSQL unreachable: {exc}")
        print("  [HINT] Start Postgres: docker compose up postgres")
        return False


def check_chroma() -> None:
    print("\n=== ChromaDB Check ===")
    try:
        import chromadb
        from app.config import get_settings

        s = get_settings()
        print(f"  host={s.chroma_host}:{s.chroma_port}")
        client = chromadb.HttpClient(host=s.chroma_host, port=s.chroma_port)
        client.heartbeat()
        print("  [OK] Connection established")

        try:
            col = client.get_collection("reviews_v1")
            count = col.count()
            print(f"  [OK] reviews_v1 has {count} documents")
            if count == 0:
                print("  [HINT] Ingest data: python -m scripts.ingest")
        except Exception:
            print("  [WARN] reviews_v1 collection not found — run: python -m scripts.ingest")

    except ImportError:
        print("  [SKIP] chromadb not installed")
    except Exception as exc:
        print(f"  [WARN] ChromaDB unavailable: {exc}")
        print("  [HINT] Start ChromaDB: docker compose up chromadb")


def main() -> None:
    # Ensure backend package is importable
    backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if backend_dir not in sys.path:
        sys.path.insert(0, backend_dir)

    pg_ok = check_postgres()
    check_chroma()

    print("\n=== Summary ===")
    if pg_ok:
        print("  PostgreSQL: OK")
    else:
        print("  PostgreSQL: FAILED")

    sys.exit(0 if pg_ok else 1)


if __name__ == "__main__":
    main()
