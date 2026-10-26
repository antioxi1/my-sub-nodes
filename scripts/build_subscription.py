#!/usr/bin/env python3
"""Build a Base64-encoded proxy URI subscription from source URLs.

Expected input: SUBSCRIPTION_URLS environment variable containing one URL per line.
Output: dist/subscription.txt (Base64 encoded URI list) and dist/nodes.txt (plain URI list).
"""
from __future__ import annotations

import base64
import json
import os
import re
import socket
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.parse import urlsplit

SUPPORTED = ("ss://", "vmess://", "vless://", "trojan://", "socks://", "socks5://", "http://", "https://")
TIMEOUT = float(os.getenv("TCP_TIMEOUT_SECONDS", "3"))
MAX_WORKERS = int(os.getenv("MAX_WORKERS", "40"))
MAX_PER_SOURCE = int(os.getenv("MAX_PER_SOURCE", "3000"))


def safe_base64_decode(raw: str) -> bytes:
    """Robust Base64 decoder supporting both standard and URL-safe variants."""
    compact = re.sub(r"\s+", "", raw)
    padding = "=" * (-len(compact) % 4)
    # Try standard base64 first, then urlsafe
    for b64_str in (compact + padding, compact):
        try:
            return base64.b64decode(b64_str)
        except Exception:
            try:
                return base64.urlsafe_b64decode(b64_str)
            except Exception:
                continue
    raise ValueError("Invalid base64 string")


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "my-sub-nodes/1.0"})
    with urllib.request.urlopen(req, timeout=15) as response:
        data = response.read(8 * 1024 * 1024)
    text = data.decode("utf-8", errors="ignore").strip()
    
    # Subscription feeds are commonly Base64 encoded. Decode if it matches Base64 characters.
    compact = re.sub(r"\s+", "", text)
    if compact and re.fullmatch(r"[A-Za-z0-9+/=_-]+", compact):
        try:
            decoded_bytes = safe_base64_decode(compact)
            decoded = decoded_bytes.decode("utf-8", errors="ignore")
            if "://" in decoded:
                text = decoded
        except Exception:
            pass
    return text


def get_host_port(uri: str):
    """Best-effort endpoint extraction for common URI schemes."""
    try:
        if uri.startswith("vmess://"):
            raw = uri[len("vmess://"):]
            obj = safe_base64_decode(raw).decode("utf-8", "ignore")
            data = json.loads(obj)
            return data.get("add"), int(data.get("port", 0))
        parsed = urlsplit(uri)
        if parsed.hostname and parsed.port:
            return parsed.hostname, parsed.port
    except Exception:
        return None
    return None


def tcp_latency(uri: str):
    endpoint = get_host_port(uri)
    if not endpoint:
        return None
    host, port = endpoint
    if not host or not port or port < 1 or port > 65535:
        return None
    started = time.monotonic()
    try:
        with socket.create_connection((host, port), timeout=TIMEOUT):
            return round((time.monotonic() - started) * 1000)
    except (OSError, ValueError):
        return None


def main():
    source_text = os.getenv("SUBSCRIPTION_URLS", "").strip()
    if not source_text:
        raise SystemExit("Missing SUBSCRIPTION_URLS secret. Add one subscription URL per line.")
    urls = [line.strip() for line in source_text.splitlines() if line.strip() and not line.strip().startswith("#")]

    all_uris = []
    errors = []

    for url in urls:
        try:
            text = fetch(url)

            pattern = re.compile(
                r"""(?i)(?:ss|vmess|vless|trojan|socks5?|https?)://[^\s"'<>]+"""
            )

            found = []
            for match in pattern.findall(text):
                candidate = match.rstrip("),;]}")
                if candidate.startswith(SUPPORTED):
                    found.append(candidate)

            found = list(dict.fromkeys(found))
            all_uris.extend(found[:MAX_PER_SOURCE])

            print(
                f"Fetched source: "
                f"{len(found[:MAX_PER_SOURCE])} candidate links"
            )

          except Exception as exc:
            errors.append(
                f"{type(exc).__name__}: {exc}"
            )
            print(
                f"WARNING: source fetch failed "
                f"({type(exc).__name__})"
            )


    # Preserve order while removing duplicates.
    unique = list(dict.fromkeys(all_uris))
    if not unique:
        raise SystemExit("No supported proxy URI links were found. Check your source URLs and formats.")

    # Optional endpoint TCP reachability filter.
    if os.getenv("ENABLE_TCP_CHECK", "true").lower() in ("1", "true", "yes"):
        passed = set()
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
            futures = {pool.submit(tcp_latency, uri): uri for uri in unique}
            for future in as_completed(futures):
                uri = futures[future]
                try:
                    latency = future.result()
                    if latency is None or latency <= int(os.getenv("MAX_TCP_LATENCY_MS", "2500")):
                        passed.add(uri)
                except Exception:
                    passed.add(uri)
        filtered = [uri for uri in unique if uri in passed]
    else:
        filtered = unique

    # Keep URI lines for common mobile proxy clients.
    out = Path("dist")
    out.mkdir(parents=True, exist_ok=True)
    payload = ("\n".join(filtered) + "\n").encode("utf-8")
    (out / "nodes.txt").write_bytes(payload)
    (out / "subscription.txt").write_text(base64.b64encode(payload).decode("ascii") + "\n", encoding="ascii")
    (out / "summary.txt").write_text(
        f"Sources: {len(urls)}\nCandidates: {len(unique)}\nOutput links: {len(filtered)}\n",
        encoding="utf-8",
    )
    print(f"Output links: {len(filtered)}")
    if errors:
        print(f"Sources with errors: {len(errors)}")


if __name__ == "__main__":
    main()
