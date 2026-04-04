"""
Flow Map Generator
------------------
For each repo in emerging_leads.json:
1. Fetch repo file tree from GitHub API
2. Pick the 5-7 most important files (entry points, pipeline, config)
3. Feed file contents to Claude
4. Get back structured flow map JSON
5. Save result into flow_maps.json
"""

import json
import time
import base64
import os
import requests
from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv
load_dotenv()

# ── Config ────────────────────────────────────────────────────────────────────
GITHUB_TOKEN = "your_github_token_here"
INPUT_FILE   = "emerging_leads.json"
OUTPUT_FILE  = "flow_maps.json"
MAX_REPOS    = None   # Set to an int like 10 to test on a subset, None = all

GITHUB_HEADERS = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json",
}

# Files we prioritise fetching (matched by name substring, in priority order)
PRIORITY_FILENAMES = [
    "__main__.py", "cli.py", "main.py", "app.py",
    "runner.py", "pipeline.py", "stages.py", "executor.py",
    "config.py", "settings.py", "adapters.py",
    "prompts.default.yaml", "prompts.yaml",
]

# Extensions worth fetching at all
ALLOWED_EXTENSIONS = {".py", ".yaml", ".yml", ".toml", ".md"}

# Max files to send Claude per repo
MAX_FILES_TO_SEND = 7

client = OpenAI(
    api_key=os.getenv("XAI_API_KEY"),
    base_url="https://api.x.ai/v1",
)


# ── GitHub helpers ────────────────────────────────────────────────────────────

def get_file_tree(repo: str) -> list[dict]:
    """Return flat list of all files in the repo (default branch)."""
    url = f"https://api.github.com/repos/{repo}/git/trees/HEAD?recursive=1"
    r = requests.get(url, headers=GITHUB_HEADERS, timeout=15)
    if r.status_code != 200:
        print(f"  [!] Tree fetch failed for {repo}: {r.status_code}")
        return []
    return [f for f in r.json().get("tree", []) if f["type"] == "blob"]


def score_file(path: str) -> int:
    """
    Score a file path — higher = more important.
    Used to pick the best files to send Claude.
    """
    score = 0
    name = Path(path).name.lower()
    ext  = Path(path).suffix.lower()

    if ext not in ALLOWED_EXTENSIONS:
        return -1

    # Boost by priority filename match
    for i, pattern in enumerate(PRIORITY_FILENAMES):
        if pattern in name:
            score += (len(PRIORITY_FILENAMES) - i) * 10
            break

    # Boost files near the root (fewer slashes = closer to root)
    depth = path.count("/")
    score -= depth * 2

    # Boost test files for use-case discovery
    if "test" in path.lower():
        score += 5

    # Penalise docs, assets, examples
    for skip in ["docs/", "image/", "assets/", "examples/", ".github/"]:
        if path.startswith(skip):
            score -= 50

    return score


def pick_best_files(tree: list[dict]) -> list[str]:
    """Return paths of the top N most useful files."""
    scored = [(score_file(f["path"]), f["path"]) for f in tree]
    scored = [(s, p) for s, p in scored if s >= 0]
    scored.sort(reverse=True)
    return [p for _, p in scored[:MAX_FILES_TO_SEND]]


def fetch_file_content(repo: str, path: str) -> str | None:
    """Fetch decoded text content of a single file."""
    url = f"https://api.github.com/repos/{repo}/contents/{path}"
    r = requests.get(url, headers=GITHUB_HEADERS, timeout=15)
    if r.status_code != 200:
        return None
    data = r.json()
    if data.get("encoding") == "base64":
        try:
            return base64.b64decode(data["content"]).decode("utf-8", errors="replace")
        except Exception:
            return None
    return data.get("content")


# ── Claude helpers ────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are a senior software architect. 
Given source files from a GitHub repository, produce a control flow map as JSON.

Return ONLY a JSON object with this exact structure (no markdown, no explanation):
{
  "entry_point": "path/to/main_file.py",
  "core_files": ["file1.py", "file2.py"],
  "use_cases": [
    {
      "name": "Short use case name",
      "flow": [
        {"file": "path/to/file.py", "role": "what this file does in this flow"}
      ]
    }
  ],
  "phases": [
    {
      "id": "A",
      "label": "Phase name",
      "steps": ["STEP_ONE", "STEP_TWO"],
      "has_gate": false,
      "rollback_to": null
    }
  ],
  "key_insight": "One sentence explaining the most important architectural pattern"
}

Rules:
- core_files: max 7 files a new contributor must read first, in study order
- use_cases: 3 to 5 most common ways this repo is used
- phases: the high-level pipeline stages if the repo has a pipeline, else omit
- Be precise. Only reference files that actually exist in the provided content.
"""


def build_user_prompt(repo: str, description: str, files: dict[str, str]) -> str:
    parts = [
        f"Repository: {repo}",
        f"Description: {description}",
        "",
        "=== FILE CONTENTS ===",
    ]
    for path, content in files.items():
        # Truncate very large files to save tokens
        truncated = content[:3000] + "\n... [truncated]" if len(content) > 3000 else content
        parts.append(f"\n--- {path} ---\n{truncated}")
    return "\n".join(parts)


def get_flow_map(repo: str, description: str, files: dict[str, str]) -> dict | None:
    """Call Claude and return parsed flow map JSON."""
    prompt = build_user_prompt(repo, description, files)
    try:
        response = client.chat.completions.create(
            model="grok-3-mini",
            max_tokens=2048,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": prompt},
            ],
        )
        raw = response.choices[0].message.content.strip()
        # Strip markdown fences if present
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        return json.loads(raw.strip())
    except json.JSONDecodeError as e:
        print(f"  [!] JSON parse error: {e}")
        return None
    except Exception as e:
        print(f"  [!] Claude error: {e}")
        return None


# ── Main pipeline ─────────────────────────────────────────────────────────────

def process_repo(entry: dict) -> dict:
    repo        = entry["repo"]
    description = entry.get("description", "")
    print(f"\n{'='*60}")
    print(f"  Repo: {repo}")

    result = {
        "rank":        entry.get("rank"),
        "repo":        repo,
        "stars":       entry.get("stars"),
        "description": description,
        "repo_url":    entry.get("repo_url"),
        "flow_map":    None,
        "error":       None,
    }

    # Step 1: get file tree
    tree = get_file_tree(repo)
    if not tree:
        result["error"] = "could not fetch file tree"
        return result
    print(f"  Files in repo: {len(tree)}")

    # Step 2: pick best files
    best_paths = pick_best_files(tree)
    print(f"  Selected files: {best_paths}")

    # Step 3: fetch file contents
    file_contents = {}
    for path in best_paths:
        content = fetch_file_content(repo, path)
        if content:
            file_contents[path] = content
        time.sleep(0.3)  # be polite to GitHub API

    if not file_contents:
        result["error"] = "could not fetch any file contents"
        return result

    print(f"  Fetched {len(file_contents)} files, calling Claude...")

    # Step 4: get flow map from Claude
    flow_map = get_flow_map(repo, description, file_contents)
    if flow_map:
        result["flow_map"] = flow_map
        print(f"  Flow map generated. Entry: {flow_map.get('entry_point')} | Use cases: {len(flow_map.get('use_cases', []))}")
    else:
        result["error"] = "Claude returned invalid JSON"

    return result


def main():
    # Load repos
    with open(INPUT_FILE) as f:
        repos = json.load(f)

    if MAX_REPOS:
        repos = repos[:MAX_REPOS]

    print(f"Processing {len(repos)} repos...")

    # Load existing results to allow resume
    existing = {}
    if Path(OUTPUT_FILE).exists():
        with open(OUTPUT_FILE) as f:
            for item in json.load(f):
                existing[item["repo"]] = item
        print(f"Resuming — {len(existing)} already done.")

    results = list(existing.values())

    for entry in repos:
        repo = entry["repo"]

        # Skip already processed
        if repo in existing:
            print(f"  Skipping {repo} (already done)")
            continue

        result = process_repo(entry)
        results.append(result)
        existing[repo] = result

        # Save after every repo so progress is never lost
        with open(OUTPUT_FILE, "w") as f:
            json.dump(results, f, indent=2)

        # Respect rate limits between repos
        time.sleep(1.5)

    print(f"\nDone. Results saved to {OUTPUT_FILE}")
    success = sum(1 for r in results if r["flow_map"])
    print(f"Success: {success}/{len(results)} repos")


if __name__ == "__main__":
    main()
