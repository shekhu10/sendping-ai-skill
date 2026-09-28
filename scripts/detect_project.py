#!/usr/bin/env python3
"""Detect the host application's stack without reading secret files."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


SKIP_DIRS = {
    ".git", ".next", ".nuxt", ".output", ".venv", "venv", "node_modules",
    "vendor", "dist", "build", "target", "bin", "obj", "coverage",
}

MANIFESTS = {
    "package.json": "node",
    "pyproject.toml": "python",
    "requirements.txt": "python",
    "Pipfile": "python",
    "composer.json": "php",
    "Gemfile": "ruby",
    "go.mod": "go",
    "pom.xml": "java",
    "build.gradle": "java",
    "build.gradle.kts": "java",
    "Cargo.toml": "rust",
}

PACKAGE_MANAGERS = {
    "pnpm-lock.yaml": "pnpm",
    "yarn.lock": "yarn",
    "bun.lock": "bun",
    "bun.lockb": "bun",
    "package-lock.json": "npm",
    "uv.lock": "uv",
    "poetry.lock": "poetry",
    "Pipfile.lock": "pipenv",
    "composer.lock": "composer",
    "Gemfile.lock": "bundler",
    "go.sum": "go",
    "Cargo.lock": "cargo",
}


def files_under(root: Path) -> list[Path]:
    files: list[Path] = []
    for path in root.rglob("*"):
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if path.is_file():
            files.append(path)
    return files


def read_small(path: Path, limit: int = 500_000) -> str:
    try:
        if path.stat().st_size > limit:
            return ""
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def detect(root: Path) -> dict[str, Any]:
    root = root.resolve()
    if not root.is_dir():
        raise ValueError(f"not a directory: {root}")
    files = files_under(root)
    rels = {str(path.relative_to(root)) for path in files}
    names = {path.name for path in files}

    languages = sorted({language for name, language in MANIFESTS.items() if name in names})
    managers = sorted({manager for name, manager in PACKAGE_MANAGERS.items() if name in names})
    manifests = sorted(rel for rel in rels if Path(rel).name in MANIFESTS)

    manifest_text = "\n".join(read_small(root / rel) for rel in manifests).lower()
    frameworks: set[str] = set()
    checks = {
        "next.js": ('"next"',),
        "express": ('"express"',),
        "nestjs": ('"@nestjs/core"',),
        "remix": ('"@remix-run/',),
        "fastapi": ("fastapi",),
        "django": ("django",),
        "flask": ("flask",),
        "laravel": ("laravel/framework",),
        "rails": ("rails",),
        "spring": ("spring-boot", "org.springframework"),
        "asp.net": ("microsoft.net.sdk.web",),
        "actix": ("actix-web",),
        "axum": ("axum",),
    }
    for framework, needles in checks.items():
        if any(needle in manifest_text for needle in needles):
            frameworks.add(framework)
    lower_rels = {rel.lower() for rel in rels}
    if any(Path(rel).name.startswith("next.config") for rel in lower_rels):
        frameworks.add("next.js")
    if "manage.py" in lower_rels:
        frameworks.add("django")
    if "artisan" in lower_rels:
        frameworks.add("laravel")
    if "config/routes.rb" in lower_rels:
        frameworks.add("rails")

    existing_mail = sorted({
        provider for provider, needles in {
            "sendping": ("sendping",),
            "resend": ('"resend"', "resend.com"),
            "sendgrid": ("sendgrid",),
            "mailgun": ("mailgun",),
            "postmark": ("postmark",),
            "nodemailer": ("nodemailer",),
            "aws-ses": ("@aws-sdk/client-ses", "boto3"),
        }.items() if any(needle in manifest_text for needle in needles)
    })

    env_files = sorted(rel for rel in rels if Path(rel).name in {
        ".env.example", ".env.sample", ".env.template", "example.env",
    })
    has_gitignore = ".gitignore" in names
    gitignore = read_small(root / ".gitignore") if has_gitignore else ""
    env_ignored = any(token in gitignore.splitlines() for token in (".env", ".env*", ".env.local"))

    recommended = {
        "node": "official npm package: sendping",
        "python": "official PyPI package: sendping",
        "php": "official Composer package: sendping/sendping",
        "ruby": "official gem: sendping",
        "go": "official Go v5 module",
        "java": "official Maven artifact: co.sendping:sendping",
        "rust": "official crate: sendping",
    }
    if any(path.suffix in {".cs", ".csproj"} for path in files):
        languages = sorted(set(languages) | {"dotnet"})

    client = [recommended.get(language, "REST API") for language in languages]
    if not client:
        client = ["REST API with the application's server HTTP client"]

    return {
        "root": str(root),
        "languages": languages,
        "frameworks": sorted(frameworks),
        "packageManagers": managers,
        "manifests": manifests,
        "existingMailProviders": existing_mail,
        "environmentExamples": env_files,
        "gitignorePresent": has_gitignore,
        "environmentSecretsAppearIgnored": env_ignored,
        "recommendedClients": client,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".", help="Target repository root")
    args = parser.parse_args()
    try:
        result = detect(Path(args.root))
    except ValueError as exc:
        parser.error(str(exc))
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
