#!/usr/bin/env python3
"""Audit a SendPing integration without displaying secret values."""

from __future__ import annotations

import argparse
import json
import os
import re
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable


SKIP_DIRS = {
    ".git", ".next", ".nuxt", ".output", ".venv", "venv", "node_modules",
    "vendor", "dist", "build", "target", "bin", "obj", "coverage",
}
TEXT_SUFFIXES = {
    ".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".py", ".php", ".rb",
    ".go", ".java", ".cs", ".rs", ".json", ".toml", ".xml", ".gradle",
    ".md", ".yaml", ".yml", ".env", ".example", ".sample",
}
MANIFEST_NAMES = {
    "package.json", "pyproject.toml", "requirements.txt", "composer.json",
    "Gemfile", "go.mod", "pom.xml", "build.gradle", "build.gradle.kts",
    "Cargo.toml",
}


@dataclass
class Finding:
    level: str
    code: str
    message: str
    path: str | None = None


def iter_text_files(root: Path) -> Iterable[Path]:
    for path in root.rglob("*"):
        if any(part in SKIP_DIRS for part in path.parts) or not path.is_file():
            continue
        if path.name.startswith(".env") and path.name not in {".env.example", ".env.sample", ".env.template"}:
            continue
        if path.name in MANIFEST_NAMES or path.suffix.lower() in TEXT_SUFFIXES:
            try:
                if path.stat().st_size <= 1_000_000:
                    yield path
            except OSError:
                continue


def read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def looks_real_secret(token: str) -> bool:
    suffix = token.split("_", 1)[-1]
    return len(set(suffix)) > 4 and "xxxx" not in suffix.lower()


def audit(root: Path) -> list[Finding]:
    root = root.resolve()
    if not root.is_dir():
        raise ValueError(f"not a directory: {root}")

    findings: list[Finding] = []
    texts: list[tuple[Path, str]] = [(path, read(path)) for path in iter_text_files(root)]
    joined = "\n".join(text for _, text in texts)

    for path, text in texts:
        rel = str(path.relative_to(root))
        fixture = any(part.lower() in {"test", "tests", "fixtures", "testdata"} for part in path.parts)
        for token in re.findall(r"\bmb_[A-Za-z0-9_-]{32}\b", text):
            if looks_real_secret(token):
                level = "warning" if fixture else "error"
                findings.append(Finding(level, "exposed_api_key", "A value shaped like a live SendPing API key is tracked in text; verify that it is only a non-production test vector.", rel))
                break
        for token in re.findall(r"\bwhsec_[A-Za-z0-9_+/=-]{20,}\b", text):
            if looks_real_secret(token):
                level = "warning" if fixture else "error"
                findings.append(Finding(level, "exposed_webhook_secret", "A value shaped like a live webhook signing secret is tracked in text; verify that it is only a non-production test vector.", rel))
                break
        if re.search(r"\b(?:NEXT_PUBLIC|VITE|PUBLIC|REACT_APP)_SENDPING_(?:API_KEY|WEBHOOK_SECRET)\b", text):
            findings.append(Finding("error", "client_exposed_secret", "A SendPing secret uses a browser-public environment prefix.", rel))

    has_key_ref = "SENDPING_API_KEY" in joined
    has_client = bool(re.search(r"(?:from\s+['\"]sendping['\"]|import\s+sendping|SendPing::|SendPingClient|sendping\.NewClient|com\.sendping|sendping::|/api/emails)", joined, re.I))
    mail_boundary = [
        str(path.relative_to(root)) for path, text in texts
        if "sendping" in text.lower() and re.search(r"(?:mail|email|notification|message)", str(path), re.I)
    ]
    has_idempotency = bool(re.search(r"Idempotency-Key|idempotencyKey|idempotency_key", joined, re.I))
    has_from = "SENDPING_FROM" in joined or bool(re.search(r"\bfrom\s*[:=]", joined))
    has_webhook_secret = "SENDPING_WEBHOOK_SECRET" in joined
    has_svix = all(header in joined.lower() for header in ("svix-id", "svix-timestamp", "svix-signature"))

    if not has_key_ref:
        findings.append(Finding("error", "missing_key_reference", "No server configuration reference to SENDPING_API_KEY was found."))
    if not has_client:
        findings.append(Finding("error", "missing_client", "No official SendPing SDK or REST email client usage was found."))
    if not mail_boundary:
        findings.append(Finding("warning", "missing_mail_boundary", "No SendPing-aware mail/email service boundary was detected."))
    else:
        findings.append(Finding("info", "mail_boundary", f"Detected SendPing integration files: {', '.join(mail_boundary[:6])}"))
    if not has_idempotency:
        findings.append(Finding("warning", "missing_idempotency", "No stable SendPing idempotency key usage was detected."))
    if not has_from:
        findings.append(Finding("warning", "missing_sender_config", "No default sender configuration was detected."))
    if has_webhook_secret and not has_svix:
        findings.append(Finding("error", "incomplete_webhook_verification", "A webhook secret is configured but all three Svix verification headers were not found."))
    if has_svix and not has_webhook_secret:
        findings.append(Finding("error", "missing_webhook_secret", "Webhook header handling exists without SENDPING_WEBHOOK_SECRET configuration."))

    gitignore = read(root / ".gitignore")
    if not gitignore:
        findings.append(Finding("warning", "missing_gitignore", "No .gitignore was found; verify local secret files cannot be committed."))
    elif not any(line.strip() in {".env", ".env*", ".env.local"} for line in gitignore.splitlines()):
        findings.append(Finding("warning", "env_not_ignored", "The .gitignore does not clearly ignore local .env secret files."))

    examples = [path for path, _ in texts if path.name in {".env.example", ".env.sample", ".env.template"}]
    if examples and not any("SENDPING_API_KEY" in read(path) for path in examples):
        findings.append(Finding("warning", "env_example_missing", "Environment example files do not document SENDPING_API_KEY."))
    return findings


def check_api() -> Finding:
    key = os.environ.get("SENDPING_API_KEY", "")
    if not key:
        return Finding("error", "api_key_absent", "SENDPING_API_KEY is not set; live API check skipped.")
    request = urllib.request.Request(
        "https://www.sendping.co/api/domains?limit=1",
        headers={"Authorization": f"Bearer {key}", "User-Agent": "sendping-ai-skill/1.0"},
    )
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            return Finding("info", "api_authenticated", f"Read-only API check succeeded (HTTP {response.status}).")
    except urllib.error.HTTPError as exc:
        try:
            body = json.loads(exc.read().decode("utf-8", errors="replace"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            body = {}
        name = str(body.get("name") or body.get("error") or "http_error")
        if name == "restricted_api_key":
            return Finding("info", "api_sending_key", "The key authenticated but is sending-only; the read probe was correctly restricted.")
        return Finding("error", "api_check_failed", f"Read-only API check failed (HTTP {exc.code}, {name}).")
    except (urllib.error.URLError, TimeoutError) as exc:
        return Finding("error", "api_unreachable", f"Read-only API check could not complete: {type(exc).__name__}.")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".", help="Target repository root")
    parser.add_argument("--check-api", action="store_true", help="Run a read-only API authentication check")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON")
    parser.add_argument("--strict", action="store_true", help="Treat warnings as failures")
    args = parser.parse_args()
    try:
        findings = audit(Path(args.root))
    except ValueError as exc:
        parser.error(str(exc))
    if args.check_api:
        findings.append(check_api())

    if args.json:
        print(json.dumps({"findings": [asdict(item) for item in findings]}, indent=2))
    else:
        for item in findings:
            where = f" [{item.path}]" if item.path else ""
            print(f"{item.level.upper():7} {item.code}{where}: {item.message}")
        errors = sum(item.level == "error" for item in findings)
        warnings = sum(item.level == "warning" for item in findings)
        print(f"\nSummary: {errors} error(s), {warnings} warning(s)")

    return 1 if any(item.level == "error" or (args.strict and item.level == "warning") for item in findings) else 0


if __name__ == "__main__":
    raise SystemExit(main())
