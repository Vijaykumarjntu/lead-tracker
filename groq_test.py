"""
Quick connection tester — run this before the main script.
Tests: 1) .env loading  2) xAI API  3) GitHub API
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ── Test 1: .env loading ──────────────────────────────────────────────────────
print("\n=== Test 1: .env keys ===")
xai_key    = os.getenv("XAI_API_KEY")
github_key = os.getenv("GITHUB_TOKEN")

print(f"XAI_API_KEY    : {'✅ found — ' + xai_key[:10] + '...' if xai_key else '❌ NOT FOUND'}")
print(f"GITHUB_TOKEN   : {'✅ found — ' + github_key[:10] + '...' if github_key else '❌ NOT FOUND'}")


# ── Test 2: xAI API ───────────────────────────────────────────────────────────
print("\n=== Test 2: xAI Grok API ===")
try:
    from openai import OpenAI
    client = OpenAI(api_key=xai_key, base_url="https://api.x.ai/v1")
    response = client.chat.completions.create(
        model="grok-3-mini",
        max_tokens=20,
        messages=[{"role": "user", "content": "say hello"}],
    )
    print(f"✅ xAI works! Response: {response.choices[0].message.content.strip()}")
except Exception as e:
    print(f"❌ xAI failed: {e}")


# ── Test 3: GitHub API ────────────────────────────────────────────────────────
print("\n=== Test 3: GitHub API ===")
try:
    import requests
    headers = {
        "Authorization": f"Bearer {github_key}",
        "Accept": "application/vnd.github+json",
    }
    # Test with a known small repo
    r = requests.get(
        "https://api.github.com/repos/aiming-lab/AutoResearchClaw/git/trees/HEAD?recursive=1",
        headers=headers,
        timeout=15,
    )
    if r.status_code == 200:
        files = [f for f in r.json().get("tree", []) if f["type"] == "blob"]
        print(f"✅ GitHub works! Found {len(files)} files in test repo")
    else:
        print(f"❌ GitHub failed: status {r.status_code} — {r.json().get('message')}")
except Exception as e:
    print(f"❌ GitHub failed: {e}")

print("\nDone. Fix any ❌ before running the main script.\n")