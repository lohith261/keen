#!/usr/bin/env python3
"""
KEEN — External API Connectivity Test

Run this BEFORE starting the backend to verify all external services
are reachable and credentials are valid. Helps distinguish between
API/credential errors vs project code errors.

Usage:
    cd backend
    source .venv/bin/activate
    python scripts/test_connections.py
"""

import asyncio
import base64
import json
import os
import sys
import time

from dotenv import load_dotenv

# Load .env from backend directory
env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
load_dotenv(env_path)

# ── Colors for terminal output ──────────────────────────

GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"

PASS = f"{GREEN}✅ PASS{RESET}"
FAIL = f"{RED}❌ FAIL{RESET}"
WARN = f"{YELLOW}⚠️  WARN{RESET}"
SKIP = f"{DIM}⏭️  SKIP{RESET}"

results: list[dict] = []


def log_result(service: str, status: str, message: str, details: str = ""):
    results.append({"service": service, "status": status, "message": message})
    icon = PASS if status == "pass" else FAIL if status == "fail" else WARN if status == "warn" else SKIP
    print(f"  {icon}  {BOLD}{service}{RESET} — {message}")
    if details:
        print(f"         {DIM}{details}{RESET}")


# ═══════════════════════════════════════════════════════════
# 1. ENV VARIABLE CHECK
# ═══════════════════════════════════════════════════════════

def test_env_variables():
    print(f"\n{CYAN}{BOLD}1. Environment Variables{RESET}")
    print(f"   {DIM}Checking all required variables are set{RESET}\n")

    required = {
        "SUPABASE_URL": os.getenv("SUPABASE_URL"),
        "SUPABASE_ANON_KEY": os.getenv("SUPABASE_ANON_KEY"),
        "SUPABASE_SERVICE_ROLE_KEY": os.getenv("SUPABASE_SERVICE_ROLE_KEY"),
        "DATABASE_URL": os.getenv("DATABASE_URL"),
        "REDIS_URL": os.getenv("REDIS_URL"),
        "SECRET_KEY": os.getenv("SECRET_KEY"),
        "CREDENTIAL_ENCRYPTION_KEY": os.getenv("CREDENTIAL_ENCRYPTION_KEY"),
        "TINYFISH_API_KEY": os.getenv("TINYFISH_API_KEY"),
        "TINYFISH_BASE_URL": os.getenv("TINYFISH_BASE_URL"),
    }

    # At least one LLM key is required
    optional_llm = {
        "GEMINI_API_KEY": os.getenv("GEMINI_API_KEY"),
        "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY"),
    }

    placeholders = ["change-me", "your-", "sk-...", "tf-..."]
    all_good = True

    for name, value in required.items():
        if not value:
            log_result(name, "fail", "Not set")
            all_good = False
        elif any(p in value for p in placeholders):
            log_result(name, "warn", f"Looks like a placeholder: {value[:30]}...")
            all_good = False
        else:
            log_result(name, "pass", f"Set ({len(value)} chars)")

    # Check LLM keys — at least one must be set
    has_llm = False
    for name, value in optional_llm.items():
        if value and not any(p in value for p in placeholders):
            log_result(name, "pass", f"Set ({len(value)} chars)")
            has_llm = True
        elif value:
            log_result(name, "warn", f"Looks like a placeholder")
        else:
            log_result(name, "skip", "Not set (optional)")
    if not has_llm:
        log_result("LLM_KEY", "fail", "At least one of GEMINI_API_KEY or OPENAI_API_KEY must be set")
        all_good = False

    # Validate encryption key format
    enc_key = os.getenv("CREDENTIAL_ENCRYPTION_KEY", "")
    try:
        decoded = base64.b64decode(enc_key)
        if len(decoded) != 32:
            log_result("ENCRYPTION_KEY_FORMAT", "fail", f"Must decode to 32 bytes, got {len(decoded)}")
        else:
            log_result("ENCRYPTION_KEY_FORMAT", "pass", "Valid 32-byte base64 key")
    except Exception:
        log_result("ENCRYPTION_KEY_FORMAT", "fail", "Not valid base64")

    # Check DATABASE_URL has asyncpg driver
    db_url = os.getenv("DATABASE_URL", "")
    if "+asyncpg" in db_url:
        log_result("DATABASE_URL_DRIVER", "pass", "Using asyncpg driver")
    else:
        log_result("DATABASE_URL_DRIVER", "warn", "Missing +asyncpg — async SQLAlchemy requires it")

    return all_good


# ═══════════════════════════════════════════════════════════
# 2. SUPABASE REST API
# ═══════════════════════════════════════════════════════════

async def test_supabase():
    print(f"\n{CYAN}{BOLD}2. Supabase REST API{RESET}")
    print(f"   {DIM}Testing connectivity and auth{RESET}\n")

    import httpx

    url = os.getenv("SUPABASE_URL", "")
    anon_key = os.getenv("SUPABASE_ANON_KEY", "")
    service_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")

    # Test anon key — hit the REST health endpoint
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                f"{url}/rest/v1/",
                headers={
                    "apikey": anon_key,
                    "Authorization": f"Bearer {anon_key}",
                },
            )
            if resp.status_code == 200:
                log_result("Supabase REST (anon)", "pass", f"HTTP {resp.status_code}")
            else:
                log_result("Supabase REST (anon)", "fail", f"HTTP {resp.status_code}", resp.text[:100])
    except Exception as e:
        log_result("Supabase REST (anon)", "fail", str(e)[:100])

    # Test service role key
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                f"{url}/rest/v1/",
                headers={
                    "apikey": service_key,
                    "Authorization": f"Bearer {service_key}",
                },
            )
            if resp.status_code == 200:
                log_result("Supabase REST (service_role)", "pass", f"HTTP {resp.status_code}")
            else:
                log_result("Supabase REST (service_role)", "fail", f"HTTP {resp.status_code}", resp.text[:100])
    except Exception as e:
        log_result("Supabase REST (service_role)", "fail", str(e)[:100])


# ═══════════════════════════════════════════════════════════
# 3. SUPABASE POSTGRESQL (direct connection)
# ═══════════════════════════════════════════════════════════

async def test_database():
    print(f"\n{CYAN}{BOLD}3. Supabase PostgreSQL (direct){RESET}")
    print(f"   {DIM}Testing database connectivity via asyncpg{RESET}\n")

    db_url = os.getenv("DATABASE_URL", "")
    # Strip the SQLAlchemy prefix for raw asyncpg
    raw_url = db_url.replace("postgresql+asyncpg://", "postgresql://")

    try:
        import asyncpg
        conn = await asyncpg.connect(raw_url, timeout=10)
        version = await conn.fetchval("SELECT version()")
        await conn.close()
        short_ver = version.split(",")[0] if version else "unknown"
        log_result("PostgreSQL Connection", "pass", f"Connected — {short_ver}")
    except Exception as e:
        log_result("PostgreSQL Connection", "fail", str(e)[:120])


# ═══════════════════════════════════════════════════════════
# 4. REDIS
# ═══════════════════════════════════════════════════════════

async def test_redis():
    print(f"\n{CYAN}{BOLD}4. Redis{RESET}")
    print(f"   {DIM}Testing connectivity (needed for checkpointing){RESET}\n")

    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    try:
        import redis.asyncio as aioredis
        client = aioredis.from_url(redis_url, decode_responses=True)
        pong = await client.ping()
        info = await client.info("server")
        version = info.get("redis_version", "unknown")
        await client.aclose()
        if pong:
            log_result("Redis Connection", "pass", f"PONG — Redis v{version}")
        else:
            log_result("Redis Connection", "fail", "Ping returned False")
    except ConnectionRefusedError:
        log_result("Redis Connection", "fail", "Connection refused — is Redis running?",
                   "Start with: brew install redis && redis-server")
    except Exception as e:
        log_result("Redis Connection", "fail", str(e)[:120],
                   "Start with: brew install redis && redis-server")


# ═══════════════════════════════════════════════════════════
# 5. LLM APIs (Gemini + OpenAI)
# ═══════════════════════════════════════════════════════════

async def test_llm():
    print(f"\n{CYAN}{BOLD}5. LLM APIs{RESET}")
    print(f"   {DIM}Testing Gemini and OpenAI API keys{RESET}\n")

    import httpx

    # ── Gemini ───────────────────────────────────────────
    gemini_key = os.getenv("GEMINI_API_KEY", "")
    if gemini_key:
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(
                    f"https://generativelanguage.googleapis.com/v1beta/models?key={gemini_key}",
                )
                if resp.status_code == 200:
                    models = resp.json().get("models", [])
                    model_names = [m.get("name", "").split("/")[-1] for m in models[:5]]
                    log_result("Gemini API Key", "pass",
                               f"Valid — {len(models)} models available",
                               f"Models: {', '.join(model_names)}")
                elif resp.status_code == 400:
                    error_msg = resp.json().get("error", {}).get("message", resp.text[:100])
                    log_result("Gemini API Key", "fail", f"Bad request: {error_msg[:80]}")
                elif resp.status_code == 403:
                    log_result("Gemini API Key", "fail", "Forbidden (403) — API key invalid or Gemini API not enabled")
                else:
                    log_result("Gemini API Key", "fail", f"HTTP {resp.status_code}", resp.text[:100])
        except Exception as e:
            log_result("Gemini API Key", "fail", str(e)[:120])
    else:
        log_result("Gemini API Key", "skip", "GEMINI_API_KEY not set")

    # ── OpenAI ───────────────────────────────────────────
    openai_key = os.getenv("OPENAI_API_KEY", "")
    if openai_key:
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(
                    "https://api.openai.com/v1/models",
                    headers={"Authorization": f"Bearer {openai_key}"},
                )
                if resp.status_code == 200:
                    models = resp.json().get("data", [])
                    model_names = [m["id"] for m in models[:5]]
                    log_result("OpenAI API Key", "pass",
                               f"Valid — {len(models)} models available",
                               f"Models: {', '.join(model_names)}")
                elif resp.status_code == 401:
                    log_result("OpenAI API Key", "warn", "Invalid key (401) — Gemini is available as fallback")
                elif resp.status_code == 429:
                    log_result("OpenAI API Key", "warn", "Rate limited (429) — key works but quota exceeded")
                else:
                    log_result("OpenAI API Key", "warn", f"HTTP {resp.status_code}", resp.text[:100])
        except Exception as e:
            log_result("OpenAI API Key", "warn", str(e)[:120])
    else:
        log_result("OpenAI API Key", "skip", "OPENAI_API_KEY not set")


# ═══════════════════════════════════════════════════════════
# 6. TINYFISH API
# ═══════════════════════════════════════════════════════════

async def test_tinyfish():
    print(f"\n{CYAN}{BOLD}6. TinyFish Browser Automation API{RESET}")
    print(f"   {DIM}Testing API key and endpoint{RESET}\n")

    api_key = os.getenv("TINYFISH_API_KEY", "")
    base_url = os.getenv("TINYFISH_BASE_URL", "")

    # Test basic connectivity to the base URL
    try:
        import httpx
        async with httpx.AsyncClient(timeout=15) as client:
            # Try a lightweight request to verify the endpoint is reachable
            resp = await client.post(
                f"{base_url}/automation/run-sse",
                headers={
                    "X-API-Key": api_key,
                    "Content-Type": "application/json",
                },
                json={
                    "url": "https://example.com",
                    "goal": "Return the page title in json: {title: '...'}",
                },
                timeout=30,
            )
            if resp.status_code == 200:
                log_result("TinyFish API", "pass",
                           f"HTTP {resp.status_code} — API responding",
                           f"Response: {resp.text[:100]}")
            elif resp.status_code == 401:
                log_result("TinyFish API", "fail", "Invalid API key (401)")
            elif resp.status_code == 403:
                log_result("TinyFish API", "fail", "Forbidden (403) — check API key permissions")
            else:
                log_result("TinyFish API", "warn",
                           f"HTTP {resp.status_code}",
                           resp.text[:150])
    except httpx.ConnectError:
        log_result("TinyFish API", "fail", f"Cannot connect to {base_url}",
                   "Check TINYFISH_BASE_URL in .env")
    except httpx.ReadTimeout:
        log_result("TinyFish API", "warn", "Request timed out (30s) — endpoint may be slow but reachable")
    except Exception as e:
        log_result("TinyFish API", "fail", str(e)[:120])


# ═══════════════════════════════════════════════════════════
# 7. ENCRYPTION KEY VALIDATION
# ═══════════════════════════════════════════════════════════

def test_encryption():
    print(f"\n{CYAN}{BOLD}7. AES-256-GCM Encryption{RESET}")
    print(f"   {DIM}Testing encrypt/decrypt roundtrip{RESET}\n")

    enc_key = os.getenv("CREDENTIAL_ENCRYPTION_KEY", "")

    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        key = base64.b64decode(enc_key)
        aesgcm = AESGCM(key)
        nonce = os.urandom(12)
        test_data = b'{"username": "test", "password": "secret123"}'
        ciphertext = aesgcm.encrypt(nonce, test_data, None)
        decrypted = aesgcm.decrypt(nonce, ciphertext, None)

        if decrypted == test_data:
            log_result("Encrypt/Decrypt", "pass", "Roundtrip successful — credentials can be stored securely")
        else:
            log_result("Encrypt/Decrypt", "fail", "Decrypted data doesn't match original")
    except Exception as e:
        log_result("Encrypt/Decrypt", "fail", str(e)[:120])


# ═══════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════

async def main():
    print(f"\n{'═' * 60}")
    print(f"{BOLD}{CYAN}  KEEN — External API Connectivity Test{RESET}")
    print(f"{'═' * 60}")

    start = time.time()

    # 1. Sync tests
    test_env_variables()
    test_encryption()

    # 2. Async tests
    await test_supabase()
    await test_database()
    await test_redis()
    await test_llm()
    await test_tinyfish()

    elapsed = time.time() - start

    # ── Summary ──────────────────────────────────────────
    print(f"\n{'═' * 60}")
    print(f"{BOLD}  Summary{RESET}  ({elapsed:.1f}s)\n")

    passed = sum(1 for r in results if r["status"] == "pass")
    failed = sum(1 for r in results if r["status"] == "fail")
    warned = sum(1 for r in results if r["status"] == "warn")

    print(f"  {GREEN}{passed} passed{RESET}  ", end="")
    if warned:
        print(f"  {YELLOW}{warned} warnings{RESET}  ", end="")
    if failed:
        print(f"  {RED}{failed} failed{RESET}  ", end="")
    print()

    if failed:
        print(f"\n  {RED}{BOLD}Some external services are unreachable.{RESET}")
        print(f"  {DIM}Fix the failures above before starting the backend.{RESET}")
        print(f"{'═' * 60}\n")
        sys.exit(1)
    elif warned:
        print(f"\n  {YELLOW}{BOLD}All critical services OK, but some warnings.{RESET}")
        print(f"{'═' * 60}\n")
        sys.exit(0)
    else:
        print(f"\n  {GREEN}{BOLD}All external services are healthy! Ready to start the backend.{RESET}")
        print(f"{'═' * 60}\n")
        sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())
