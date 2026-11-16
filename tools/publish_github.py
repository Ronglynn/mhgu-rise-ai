# -*- coding: utf-8 -*-
"""把 out/github_release/ 发布到 GitHub 公开仓库。

令牌从 C:/Users/RongLynn/.workbuddy/gh_pat.txt 读取，绝不打印、不写日志。
只做：GET /user、POST /user/repos、PUT /repos/.../contents/<path>、最终校验。
"""
from __future__ import annotations

import base64
import json
import pathlib
import sys
import urllib.error
import urllib.request

API = "https://api.github.com"
TOKEN_FILE = pathlib.Path("C:/Users/RongLynn/.workbuddy/gh_pat.txt")
PUB = pathlib.Path("D:/MHGU mod maker/04_RiseAI/out/github_release")
REPO = "mhgu-rise-ai"
DESCRIPTION = "Rise-style monster AI mod for Monster Hunter Generations Ultimate Recomp"
COMMIT_MSG = "Release v2: Rise-style monster AI mod for MHGU Recomp"

H = {
    "Authorization": "Bearer " + TOKEN_FILE.read_text(encoding="utf-8").strip(),
    "Accept": "application/vnd.github+json",
    "User-Agent": "WorkBuddy-Publish",
    "Content-Type": "application/json",
}


def call(method: str, path: str, body=None):
    data = json.dumps(body, ensure_ascii=False).encode("utf-8") if body is not None else None
    req = urllib.request.Request(API + path, data=data, headers=H, method=method)
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            raw = resp.read()
            return resp.status, (json.loads(raw) if raw else {})
    except urllib.error.HTTPError as e:
        raw = e.read()
        try:
            return e.code, json.loads(raw)
        except ValueError:
            return e.code, {"raw": raw[:200].decode("utf-8", "replace")}


def main() -> int:
    status, user = call("GET", "/user")
    if status != 200 or "login" not in user:
        print("FATAL: cannot resolve GitHub user:", status, str(user)[:200])
        return 1
    owner = user["login"]
    print("authenticated as", owner)

    st_exist, existing = call("GET", "/repos/%s/%s" % (owner, REPO))
    if st_exist == 200:
        print("repo already exists, reuse", existing.get("full_name"))
    else:
        status, repo = call("POST", "/user/repos", {
            "name": REPO,
            "description": DESCRIPTION,
            "private": False,
            "has_issues": True,
            "has_wiki": False,
            "has_projects": False,
            "auto_init": False,
        })
        if status == 201:
            print("created public repo", repo.get("full_name"))
        elif status == 422:
            print("repo already exists, reuse", owner + "/" + REPO)
        else:
            print("FATAL: create repo failed:", status, str(repo)[:300])
            print("hint: fine-grained PAT needs repository creation permission")
            return 1

    files = sorted(p for p in PUB.rglob("*")
                   if p.is_file() and ".git" not in p.parts)
    print("files to upload:", len(files))
    ok, fail = 0, []

    def blob_sha(data: bytes) -> str:
        import hashlib
        return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()

    for p in files:
        rel = p.relative_to(PUB).as_posix()
        data = p.read_bytes()
        api = "/repos/%s/%s/contents/%s" % (owner, REPO, rel)
        st0, cur = call("GET", api + "?ref=main")
        if st0 == 200 and isinstance(cur, dict) and cur.get("sha") == blob_sha(data):
            ok += 1
            print("  SKIP %-41s %7d B" % (rel, len(data)))
            continue
        payload = {
            "message": COMMIT_MSG,
            "content": base64.b64encode(data).decode("ascii"),
            "branch": "main",
        }
        if st0 == 200 and isinstance(cur, dict) and cur.get("sha"):
            payload["sha"] = cur["sha"]
        st, r, attempt = 0, {}, 0
        for attempt in range(4):
            st, r = call("PUT", api, payload)
            if st in (200, 201) or st < 500:
                break
        if st in (200, 201):
            ok += 1
            print("  OK   %-41s %7d B%s" % (rel, len(data), " (retry %d)" % attempt if attempt else ""))
        else:
            fail.append((rel, st, str(r)[:120]))
            print("  ERR  %-41s %s" % (rel, st))

    print("uploaded", ok, "/", len(files), "failures", len(fail))
    if fail:
        for f in fail:
            print("  ", f)
        return 1

    st, tree = call("GET", "/repos/%s/%s/git/trees/main?recursive=1" % (owner, REPO))
    n = len(tree.get("tree", [])) if st == 200 else -1
    st2, commits = call("GET", "/repos/%s/%s/commits?per_page=1" % (owner, REPO))
    head = commits[0].get("sha", "")[:8] if st2 == 200 and isinstance(commits, list) and commits else "?"
    print("verify: tree entries=%d head=%s" % (n, head))
    print("URL: https://github.com/%s/%s" % (owner, REPO))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
