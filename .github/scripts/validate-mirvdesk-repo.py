#!/usr/bin/env python3
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]

def fail(message: str) -> None:
    print(f"::error::{message}")
    raise SystemExit(1)

def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")

cargo = re.search(r'^version = "([^"]+)"', read("Cargo.toml"), re.M)
pub = re.search(r'^version: ([0-9.]+)\+', read("flutter/pubspec.yaml"), re.M)
workflow = re.search(r'^  VERSION: "([^"]+)"', read(".github/workflows/flutter-build.yml"), re.M)
pkg = re.search(r'^pkgver=([^\s]+)', read("res/PKGBUILD"), re.M)
versions = {
    "Cargo.toml": cargo.group(1) if cargo else None,
    "flutter/pubspec.yaml": pub.group(1) if pub else None,
    "flutter-build.yml": workflow.group(1) if workflow else None,
    "res/PKGBUILD": pkg.group(1) if pkg else None,
}
if None in versions.values() or len(set(versions.values())) != 1:
    fail(f"MirvDesk version metadata is inconsistent: {versions}")

build_rs = read("build.rs")
if 'MIRVDESK_SERVER_URL' not in build_rs or 'must not be empty' not in build_rs:
    fail("build.rs no longer enforces MIRVDESK_SERVER_URL")

for workflow_path in [
    ".github/workflows/flutter-build.yml",
    ".github/workflows/flutter-build-win_lin_and.yml",
]:
    text = read(workflow_path)
    arch_jobs = text.count("rustdesk-org/run-on-arch-action@")
    propagated = text.count("--env MIRVDESK_SERVER_URL")
    if arch_jobs != propagated:
        fail(f"{workflow_path}: MIRVDESK_SERVER_URL reaches {propagated}/{arch_jobs} run-on-arch containers")

for path in ROOT.rglob("*"):
    if not path.is_file() or ".git" in path.parts or "target" in path.parts:
        continue
    if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp", ".ico", ".dll", ".so", ".a"}:
        continue
    try:
        text = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        continue
    project_server = "desk" + ".mirv.top"
    if project_server in text:
        fail(f"hard-coded project server found in {path.relative_to(ROOT)}")

print(f"MirvDesk repository invariants OK (version {next(iter(versions.values()))})")
