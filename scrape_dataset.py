"""Build a Luau/Roblox instruct-tuning corpus from public GitHub repos.

Usage: python scrape_dataset.py [--max-repos N] [--out data/luau_corpus.jsonl]
Needs env var GITHUB_TOKEN (personal access token, no scopes needed) to avoid
GitHub's unauthenticated rate limit (60 req/hr vs 5000 req/hr).
"""
import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

import requests

PERMISSIVE_LICENSES = {"mit", "apache-2.0", "bsd-2-clause", "bsd-3-clause"}
MAX_FILE_BYTES = 60_000  # skip huge/minified/vendored files
SEARCH_QUERIES = [
    "roblox luau language:Luau",
    "roblox script language:Lua",
    "RemoteEvent RobloxService language:Lua",
]


def github_headers():
    token = os.environ.get("GITHUB_TOKEN")
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def find_repos(max_repos: int) -> list[dict]:
    seen, repos = set(), []
    for q in SEARCH_QUERIES:
        resp = requests.get(
            "https://api.github.com/search/repositories",
            params={"q": q, "sort": "stars", "per_page": 30},
            headers=github_headers(),
            timeout=30,
        )
        resp.raise_for_status()
        for item in resp.json().get("items", []):
            full_name = item["full_name"]
            if full_name in seen:
                continue
            license_key = (item.get("license") or {}).get("key")
            if license_key not in PERMISSIVE_LICENSES:
                continue
            seen.add(full_name)
            repos.append(item)
            if len(repos) >= max_repos:
                return repos
    return repos


def clone_shallow(repo: dict, dest: Path) -> bool:
    url = repo["clone_url"]
    try:
        subprocess.run(
            ["git", "clone", "--depth", "1", "--quiet", url, str(dest)],
            check=True, timeout=120,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        return True
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return False


def extract_pairs(code: str) -> list[tuple[str, str]]:
    """Split a Luau file into (prompt, completion) pairs at function boundaries."""
    pairs = []
    # function foo(...) ... end  OR  local function foo(...) ... end
    pattern = re.compile(
        r"((?:--.*\n)*)"          # optional leading comment lines
        r"((?:local\s+)?function\s+[\w:.]+\s*\([^)]*\)"  # signature
        r".*?\nend)",              # body up to matching 'end' (non-greedy, single func)
        re.DOTALL,
    )
    for match in pattern.finditer(code):
        comment, body = match.group(1).strip(), match.group(2).strip()
        if len(body) < 20 or len(body) > 4000:
            continue
        sig_line = body.split("\n", 1)[0]
        if comment:
            prompt = f"Write a Luau function based on this description:\n{comment}"
        else:
            prompt = f"Complete this Luau function:\n{sig_line}"
        pairs.append((prompt, body))
    return pairs


def collect_from_repo(repo_dir: Path) -> list[tuple[str, str]]:
    pairs = []
    for path in repo_dir.rglob("*"):
        if path.suffix.lower() not in (".lua", ".luau"):
            continue
        if path.stat().st_size > MAX_FILE_BYTES:
            continue
        try:
            code = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        pairs.extend(extract_pairs(code))
    return pairs


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-repos", type=int, default=40)
    parser.add_argument("--out", default="data/luau_corpus.jsonl")
    args = parser.parse_args()

    repos = find_repos(args.max_repos)
    print(f"Found {len(repos)} permissively-licensed candidate repos.")

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    seen_hashes = set()
    total = 0
    with out_path.open("w", encoding="utf-8") as out_f, tempfile.TemporaryDirectory() as tmp:
        for i, repo in enumerate(repos):
            dest = Path(tmp) / f"repo_{i}"
            if not clone_shallow(repo, dest):
                continue
            for prompt, completion in collect_from_repo(dest):
                h = hashlib.sha1(completion.encode("utf-8")).hexdigest()
                if h in seen_hashes:
                    continue
                seen_hashes.add(h)
                out_f.write(json.dumps({"prompt": prompt, "completion": completion}) + "\n")
                total += 1
            out_f.flush()
            shutil.rmtree(dest, ignore_errors=True)
            print(f"[{i+1}/{len(repos)}] {repo['full_name']}: {total} examples so far")

    assert total > 0, "Collected zero training examples — check GITHUB_TOKEN / network / query terms."
    print(f"Wrote {total} examples to {out_path}")


if __name__ == "__main__":
    main()
