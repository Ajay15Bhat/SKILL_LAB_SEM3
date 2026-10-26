"""
ClauseTrace Environment & Connection Verification Script
Includes strict 6-second timeouts to prevent any terminal hanging.
Run:
    python clausetrace/backend/test_setup.py
"""

import asyncio
import json
import os
import sys
import urllib.request
import urllib.error
from pathlib import Path
from dotenv import load_dotenv

# Load .env
env_path = Path(__file__).parent / ".env"
if not env_path.exists():
    print("\n[!] WARNING: .env file not found!")
    print(f"    Please copy {Path(__file__).parent / '.env.example'} to {env_path}")
    print("    and add your Supabase DATABASE_URL and GEMINI_API_KEY.\n")
    sys.exit(1)

load_dotenv(dotenv_path=env_path)

DATABASE_URL = os.getenv("DATABASE_URL", "")
# Auto-normalize scheme for asyncpg if user pasted standard postgresql://
if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

EXPECTED_TABLES = [
    "users",
    "contracts",
    "contract_versions",
    "clauses",
    "requirements",
    "findings",
    "audit_logs",
]


async def _run_db_checks():
    from sqlalchemy.ext.asyncio import create_async_engine
    from sqlalchemy import text

    engine = create_async_engine(
        DATABASE_URL,
        echo=False,
        connect_args={"timeout": 6},  # asyncpg connection timeout
    )
    async with engine.connect() as conn:
        # 1. Test basic query
        result = await conn.execute(text("SELECT current_database(), version();"))
        row = result.fetchone()
        print(f"[OK] Connected to database: '{row[0]}'")

        # 2. Check tables
        res = await conn.execute(
            text(
                "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';"
            )
        )
        found_tables = {r[0] for r in res.fetchall()}
        
        missing = [t for t in EXPECTED_TABLES if t not in found_tables]
        if missing:
            print(f"[FAIL] Missing tables: {missing}")
            print("       Did you run 'init_schema_and_rls.sql' in the Supabase SQL Editor?")
            return False
        else:
            print(f"[OK] All {len(EXPECTED_TABLES)} required tables are present in Supabase!")

        # 3. Test Full-Text Search indexing
        fts_check = await conn.execute(
            text(
                "SELECT indexname FROM pg_indexes WHERE tablename = 'clauses' AND indexname = 'ix_clauses_fts';"
            )
        )
        if fts_check.fetchone():
            print("[OK] Full-Text Search GIN index ('ix_clauses_fts') is verified!")

        # 4. Check seed users
        users_check = await conn.execute(text("SELECT email, role FROM users;"))
        users = users_check.fetchall()
        print(f"[OK] Seed demo users found: {len(users)} users active ({', '.join(u[0] for u in users)})")

    await engine.dispose()
    return True


async def test_database():
    print("\n" + "=" * 60)
    print(" 1. TESTING SUPABASE POSTGRESQL CONNECTION")
    print("=" * 60)

    if not DATABASE_URL or "YOUR_PASSWORD" in DATABASE_URL:
        print("[FAIL] DATABASE_URL is not configured properly in .env")
        print("       Please replace YOUR_PASSWORD and YOUR_PROJECT_REF.")
        return False

    print("Connecting to Supabase (timeout in 6s)...")
    try:
        return await asyncio.wait_for(_run_db_checks(), timeout=7.0)
    except asyncio.TimeoutError:
        print("[FAIL] Database connection timed out after 7 seconds.")
        print("       Tip: Ensure your Supabase database is active and password is correct.")
        return False
    except Exception as e:
        print(f"[FAIL] Database connection error: {e}")
        return False


def test_gemini():
    print("\n" + "=" * 60)
    print(" 2. TESTING GOOGLE GEMINI API KEY")
    print("=" * 60)

    if not GEMINI_API_KEY or "YOUR_GEMINI" in GEMINI_API_KEY:
        print("[WARN] GEMINI_API_KEY is not configured in .env.")
        print("       Semantic evaluation will be skipped until key is added.")
        return False

    print("Checking Gemini API key with Google servers (strict 5s timeout)...")
    
    # Direct lightweight REST probe with strict 5-second socket timeout
    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={GEMINI_API_KEY}"
    req = urllib.request.Request(url, headers={"User-Agent": "ClauseTrace-Verifier/1.0"})

    try:
        with urllib.request.urlopen(req, timeout=5.0) as response:
            if response.status == 200:
                body = json.loads(response.read().decode())
                models = [m.get("name", "").replace("models/", "") for m in body.get("models", [])]
                flash_models = [m for m in models if "flash" in m]
                print(f"[OK] Google Gemini API Key verified! (HTTP 200 OK)")
                print(f"[OK] Available Flash Models: {', '.join(flash_models[:3])}")
                return True
            else:
                print(f"[FAIL] Unexpected response status: {response.status}")
                return False

    except urllib.error.HTTPError as e:
        error_msg = e.read().decode()
        try:
            err_json = json.loads(error_msg)
            msg = err_json.get("error", {}).get("message", error_msg)
        except Exception:
            msg = error_msg
        print(f"[FAIL] Google API returned HTTP {e.code}: {msg}")
        return False

    except urllib.error.URLError as e:
        if "timed out" in str(e).lower():
            print("[FAIL] Gemini API probe timed out after 5 seconds.")
            print("       Check your internet connection.")
        else:
            print(f"[FAIL] Network error reaching Gemini: {e}")
        return False

    except Exception as e:
        print(f"[FAIL] Error testing Gemini: {e}")
        return False


async def main():
    print("\n>>> CLAUSETRACE SETUP VERIFICATION <<<\n")
    db_ok = await test_database()
    gemini_ok = test_gemini()

    print("\n" + "=" * 60)
    print(" SUMMARY")
    print("=" * 60)
    print(f" Supabase Database : {'READY [OK]' if db_ok else 'ACTION REQUIRED [!] '}")
    print(f" Gemini AI Service : {'READY [OK]' if gemini_ok else 'OPTIONAL / ACTION REQUIRED [!] '}")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
