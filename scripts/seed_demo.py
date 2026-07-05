#!/usr/bin/env python3
"""Upload the demo_subset smoke data to a running NoteClaw backend.

Usage:
    python scripts/seed_demo.py [--base-url http://127.0.0.1:8000] [--root data/demo_subset]

Idempotent in the loose sense: re-running just creates more notes. The backend
de-dupes by content hash where it can.
"""
from __future__ import annotations

import argparse
import mimetypes
import sys
import time
from pathlib import Path
from urllib import request as urlrequest
from urllib.error import HTTPError, URLError

EXT_TO_TYPE: dict[str, str] = {
    ".md": "text",
    ".txt": "text",
    ".csv": "table",
    ".json": "document",
    ".html": "document",
    ".py": "code",
    ".ts": "code",
    ".js": "code",
    ".go": "code",
    ".rs": "code",
    ".java": "code",
    ".rb": "code",
    ".png": "image",
    ".jpg": "image",
    ".jpeg": "image",
    ".pdf": "document",
}

KIND_TO_PREFIX: dict[str, str] = {
    "text": "demo:text",
    "code": "demo:code",
    "tables": "demo:table",
    "images": "demo:image",
}


def detect_content_type(path: Path) -> str:
    ext = path.suffix.lower()
    if ext in EXT_TO_TYPE:
        return EXT_TO_TYPE[ext]
    guess, _ = mimetypes.guess_type(path.name)
    if guess:
        if guess.startswith("image/"):
            return "image"
        if "pdf" in guess:
            return "document"
    return "document"


def upload_one(base_url: str, path: Path, source: str) -> tuple[bool, str]:
    content_type = detect_content_type(path)
    boundary = "----noteclawseed" + hex(int(time.time() * 1000))[-8:]
    body = bytearray()
    body += f"--{boundary}\r\n".encode()
    body += b'Content-Disposition: form-data; name="content_type"\r\n\r\n'
    body += f"{content_type}\r\n".encode()
    body += f"--{boundary}\r\n".encode()
    body += b'Content-Disposition: form-data; name="source"\r\n\r\n'
    body += f"{source}\r\n".encode()
    body += f"--{boundary}\r\n".encode()
    body += (
        f'Content-Disposition: form-data; name="file"; filename="{path.name}"\r\n'
    ).encode()
    mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    body += f"Content-Type: {mime}\r\n\r\n".encode()
    body += path.read_bytes()
    body += f"\r\n--{boundary}--\r\n".encode()

    req = urlrequest.Request(
        f"{base_url.rstrip('/')}/api/ingest/files",
        data=bytes(body),
        method="POST",
    )
    req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")
    try:
        with urlrequest.urlopen(req, timeout=60) as resp:
            return resp.status == 200, resp.read().decode("utf-8", errors="replace")[:200]
    except (HTTPError, URLError) as e:
        return False, str(e)[:200]


def iter_files(root: Path) -> list[tuple[Path, str]]:
    """Return (path, source) pairs for everything we want to upload."""
    out: list[tuple[Path, str]] = []
    for kind in ("text", "code", "tables", "images"):
        sub = root / kind
        if not sub.exists():
            continue
        prefix = KIND_TO_PREFIX.get(kind, f"demo:{kind}")
        for p in sorted(sub.rglob("*")):
            if p.is_file() and not p.name.startswith("."):
                out.append((p, prefix))
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--root", default="data/demo_subset")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    if not root.exists():
        print(f"[seed] root not found: {root}", file=sys.stderr)
        return 1

    files = iter_files(root)
    if not files:
        print(f"[seed] no files under {root}", file=sys.stderr)
        return 1

    print(f"[seed] uploading {len(files)} files from {root} to {args.base_url}")
    ok = 0
    failed: list[str] = []
    for i, (path, source) in enumerate(files, 1):
        success, info = upload_one(args.base_url, path, source)
        rel = path.relative_to(root)
        if success:
            ok += 1
            print(f"  [{i:>2}/{len(files)}] OK   {rel}")
        else:
            failed.append(str(rel))
            print(f"  [{i:>2}/{len(files)}] FAIL {rel} — {info}")

    print(f"[seed] done: {ok}/{len(files)} succeeded")
    if failed:
        print("[seed] failed files:", file=sys.stderr)
        for f in failed:
            print(f"  - {f}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
