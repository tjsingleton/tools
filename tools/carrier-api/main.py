from __future__ import annotations

import argparse
import json
import os
import shlex
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class RequestSpec:
    method: str
    url: str
    headers: dict[str, str]
    body: bytes | None


def _strip_leading_slash(path: str) -> str:
    return path[1:] if path.startswith("/") else path


def build_url(base_url: str, path: str, query: Iterable[str]) -> str:
    base_url = base_url.rstrip("/")
    path = _strip_leading_slash(path)

    parsed = urllib.parse.urlparse(base_url)
    if not parsed.scheme or not parsed.netloc:
        raise ValueError("base_url must include scheme and host, e.g. https://api.example.com")

    existing_qs = urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)
    extra_qs: list[tuple[str, str]] = []
    for item in query:
        if "=" not in item:
            raise ValueError(f"invalid --query item {item!r}; expected key=value")
        k, v = item.split("=", 1)
        extra_qs.append((k, v))

    merged_qs = existing_qs + extra_qs
    query_str = urllib.parse.urlencode(merged_qs)

    return urllib.parse.urlunparse(
        (
            parsed.scheme,
            parsed.netloc,
            f"{parsed.path.rstrip('/')}/{path}" if path else parsed.path,
            "",
            query_str,
            "",
        )
    )


def parse_headers(items: Iterable[str]) -> dict[str, str]:
    headers: dict[str, str] = {}
    for item in items:
        if ":" not in item:
            raise ValueError(f"invalid --header {item!r}; expected 'Key: Value'")
        key, value = item.split(":", 1)
        key = key.strip()
        value = value.lstrip()
        if not key:
            raise ValueError(f"invalid --header {item!r}; empty key")
        headers[key] = value
    return headers


def build_request_spec(
    *,
    base_url: str,
    path: str,
    method: str,
    token: str | None,
    header_items: Iterable[str],
    query_items: Iterable[str],
    json_body: str | None,
) -> RequestSpec:
    url = build_url(base_url, path, query_items)

    headers = parse_headers(header_items)
    headers.setdefault("Accept", "application/json")

    if token:
        headers.setdefault("Authorization", f"Bearer {token}")

    body: bytes | None = None
    if json_body is not None:
        try:
            parsed = json.loads(json_body)
        except json.JSONDecodeError as e:
            raise ValueError(f"--json must be valid JSON: {e}") from e
        body = json.dumps(parsed).encode("utf-8")
        headers.setdefault("Content-Type", "application/json")

    return RequestSpec(method=method.upper(), url=url, headers=headers, body=body)


def to_curl(spec: RequestSpec) -> str:
    parts: list[str] = ["curl", "-i", "-X", spec.method]
    for k, v in sorted(spec.headers.items(), key=lambda kv: kv[0].lower()):
        parts += ["-H", f"{k}: {v}"]
    if spec.body is not None:
        parts += ["--data-binary", spec.body.decode("utf-8")]
    parts.append(spec.url)
    return " ".join(shlex.quote(p) for p in parts)


def execute(spec: RequestSpec, *, timeout_s: float = 30.0) -> int:
    req = urllib.request.Request(
        spec.url,
        data=spec.body,
        method=spec.method,
        headers=spec.headers,
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            body = resp.read()
            content_type = resp.headers.get("Content-Type", "")
            sys.stdout.write(f"HTTP {resp.status}\n")
            if content_type:
                sys.stdout.write(f"Content-Type: {content_type}\n")
            sys.stdout.write("\n")

            if not body:
                return 0

            text = body.decode("utf-8", errors="replace")
            if "application/json" in content_type.lower():
                try:
                    obj = json.loads(text)
                except json.JSONDecodeError:
                    sys.stdout.write(text)
                else:
                    sys.stdout.write(json.dumps(obj, indent=2, sort_keys=True))
                    sys.stdout.write("\n")
            else:
                sys.stdout.write(text)
            return 0
    except urllib.error.HTTPError as e:
        sys.stderr.write(f"HTTPError: {e.code}\n")
        sys.stderr.write(e.read().decode("utf-8", errors="replace"))
        sys.stderr.write("\n")
        return 1
    except urllib.error.URLError as e:
        sys.stderr.write(f"URLError: {e.reason}\n")
        return 1


def _parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Carrier API helper (dry-run by default)")
    p.add_argument("--execute", action="store_true", help="Execute the request (otherwise prints curl)")
    p.add_argument("--base-url", default=os.environ.get("CARRIER_API_BASE_URL", ""), help="API base URL")
    p.add_argument("--token", default=os.environ.get("CARRIER_API_TOKEN", ""), help="Bearer token")
    p.add_argument("--method", default="GET", help="HTTP method")
    p.add_argument("--path", required=True, help="Request path, e.g. /v1/me")
    p.add_argument("--query", action="append", default=[], help="Query item key=value (repeatable)")
    p.add_argument("--header", action="append", default=[], help="Header 'Key: Value' (repeatable)")
    p.add_argument("--json", dest="json_body", default=None, help="JSON body string")
    p.add_argument("--timeout", type=float, default=30.0, help="Timeout seconds (execute mode)")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    ns = _parse_args(sys.argv[1:] if argv is None else argv)

    if not ns.base_url:
        sys.stderr.write("Missing --base-url (or env CARRIER_API_BASE_URL)\n")
        return 2

    token = ns.token or None
    try:
        spec = build_request_spec(
            base_url=ns.base_url,
            path=ns.path,
            method=ns.method,
            token=token,
            header_items=ns.header,
            query_items=ns.query,
            json_body=ns.json_body,
        )
    except ValueError as e:
        sys.stderr.write(f"{e}\n")
        return 2

    if not ns.execute:
        sys.stdout.write(to_curl(spec))
        sys.stdout.write("\n")
        return 0

    return execute(spec, timeout_s=ns.timeout)


if __name__ == "__main__":
    raise SystemExit(main())

