import json
import os
import re
import subprocess
import time
import urllib.request
from datetime import datetime
from html import escape


USERNAME = os.getenv("GITHUB_USERNAME", "zufarrizal")
INDEX_PATH = os.getenv("INDEX_PATH", "index.html")


def fetch_repos(username: str):
    repos = []
    page = 1
    token = os.getenv("GITHUB_TOKEN", "").strip()

    while True:
        url = f"https://api.github.com/users/{username}/repos?per_page=100&page={page}"
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": f"{username}-projects-sync",
        }
        if token:
            headers["Authorization"] = f"Bearer {token}"

        data = None
        last_error = None

        for attempt in range(1, 6):
            try:
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=25) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                break
            except Exception as err:
                last_error = err
                time.sleep(attempt)

        # Fallback to curl if urllib repeatedly fails on the host.
        if data is None:
            cmd = ["curl", "-sL", url, "-H", "Accept: application/vnd.github+json"]
            if token:
                cmd.extend(["-H", f"Authorization: Bearer {token}"])
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, check=True)
                data = json.loads(result.stdout)
            except Exception as curl_err:
                raise RuntimeError(f"Failed to fetch GitHub repos page {page}: {last_error} / {curl_err}")

        if not data:
            break

        repos.extend(data)
        if len(data) < 100:
            break
        page += 1

    return sorted(repos, key=lambda r: (r.get("name") or "").lower())


def fmt_date(value: str) -> str:
    if not value:
        return "-"
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d")
    except Exception:
        return value


def build_rows(repos):
    rows = []
    for repo in repos:
        name = escape(repo.get("name") or "-")
        url = escape(repo.get("html_url") or "#", quote=True)
        repo_type = "Fork" if repo.get("fork") else "Source"
        language = escape(repo.get("language") or "-")
        updated = fmt_date(repo.get("pushed_at") or repo.get("updated_at"))
        description = escape((repo.get("description") or "-").strip() or "-")

        rows.append(
            f'            <tr><td>{name}</td><td><a href="{url}" target="_blank" rel="noreferrer">Open</a></td><td>{repo_type}</td><td>{language}</td><td>{updated}</td><td>{description}</td></tr>'
        )

    return "\n".join(rows)


def sync_index(index_path: str, rows_html: str):
    with open(index_path, "r", encoding="utf-8") as f:
        html = f.read()

    pattern = re.compile(r"(<tbody>\s*\n)([\s\S]*?)(\n\s*</tbody>)", re.MULTILINE)
    match = pattern.search(html)
    if not match:
        raise RuntimeError("Could not locate <tbody>...</tbody> in index.html")

    updated = html[: match.start(2)] + rows_html + html[match.end(2) :]

    with open(index_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(updated)


def main():
    repos = fetch_repos(USERNAME)
    rows_html = build_rows(repos)
    sync_index(INDEX_PATH, rows_html)
    print(f"Synced {len(repos)} repositories into {INDEX_PATH}")


if __name__ == "__main__":
    main()
