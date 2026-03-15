import json
import os
import urllib.error
import urllib.request


USERNAME = os.getenv("GITHUB_USERNAME", "zufarrizal")
TOKEN = os.getenv("GH_REPO_ADMIN_TOKEN", "").strip()
DRY_RUN = os.getenv("DRY_RUN", "true").lower() in {"1", "true", "yes"}
MAP_FILE = os.getenv("DESCRIPTION_MAP_FILE", "scripts/repo_descriptions.json")


def patch_description(repo: str, description: str):
    url = f"https://api.github.com/repos/{USERNAME}/{repo}"
    payload = json.dumps({"description": description}).encode("utf-8")

    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {TOKEN}",
        "User-Agent": f"{USERNAME}-repo-description-updater",
        "Content-Type": "application/json",
    }
    req = urllib.request.Request(url, data=payload, headers=headers, method="PATCH")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.status


def main():
    if not os.path.exists(MAP_FILE):
        raise FileNotFoundError(f"Description map not found: {MAP_FILE}")

    with open(MAP_FILE, "r", encoding="utf-8") as f:
        mapping = json.load(f)

    print(f"Loaded {len(mapping)} descriptions from {MAP_FILE}")

    if DRY_RUN:
        for repo, desc in mapping.items():
            print(f"[DRY-RUN] {repo}: {desc}")
        return

    if not TOKEN:
        raise RuntimeError("GH_REPO_ADMIN_TOKEN is required when DRY_RUN=false")

    updated = 0
    failed = 0

    for repo, desc in mapping.items():
        try:
            status = patch_description(repo, desc)
            print(f"[OK] {repo} -> HTTP {status}")
            updated += 1
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="ignore")
            print(f"[FAIL] {repo} -> HTTP {e.code} {body}")
            failed += 1
        except Exception as e:
            print(f"[FAIL] {repo} -> {e}")
            failed += 1

    print(f"Done. Updated: {updated}, Failed: {failed}")


if __name__ == "__main__":
    main()
