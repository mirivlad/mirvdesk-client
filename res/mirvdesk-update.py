#!/usr/bin/env python3
"""Unattended MirvDesk Debian updates from its own GitHub Releases.

Run ONLY as the package-installed systemd timer (root); no upstream RustDesk
endpoint, arbitrary mirror, unverified artifact, or shell-interpolated input.
"""
import fcntl
import hashlib
import json
import os
import platform
import re
import subprocess
import sys
import tempfile
import urllib.parse
import urllib.request
from pathlib import Path

REPO = "mirivlad/mirvdesk-client"
API = f"https://api.github.com/repos/{REPO}/releases?per_page=30"
MAX_SIZE = 300 * 1024 * 1024
TAG = re.compile(r"^v?(\d+)\.(\d+)\.(\d+)(?:-(\d+))?$")
SHA256 = re.compile(r"^sha256:([0-9a-f]{64})$")
ALLOWED_REDIRECT_HOSTS = {
    "github.com", "api.github.com", "release-assets.githubusercontent.com",
    "objects.githubusercontent.com",
}


def version_key(value):
    value = value.strip()
    match = TAG.fullmatch(value)
    if not match:
        return None
    major, minor, patch, rc = match.groups()
    return int(major), int(minor), int(patch), (int(rc) if rc else 1000000)


def expected_name(tag, machine):
    arch = {"x86_64": "x86_64", "aarch64": "aarch64"}.get(machine)
    version = tag.removeprefix("v")
    if not arch or version_key(tag) is None:
        return None
    return f"mirvdesk-{version}-{arch}.deb"


def choose_release(releases, installed, machine):
    current = version_key(installed)
    if current is None:
        raise ValueError(f"Unsupported installed version: {installed!r}")
    # Pre-release users opt into the pre-release channel by installing one.
    preview_channel = current[3] < 1000000
    for release in sorted(releases, key=lambda x: version_key(x.get("tag_name", "")) or (0, 0, 0, 0),
                          reverse=True):
        tag = release.get("tag_name", "")
        version = version_key(tag)
        if release.get("draft") or not version or version <= current:
            continue
        if release.get("prerelease") and not preview_channel:
            continue
        filename = expected_name(tag, machine)
        for asset in release.get("assets", []):
            if not filename or asset.get("name") != filename:
                continue
            url = asset.get("browser_download_url", "")
            expected_url = f"https://github.com/{REPO}/releases/download/{tag}/{filename}"
            digest = asset.get("digest", "")
            match = SHA256.fullmatch(digest) if isinstance(digest, str) else None
            size = asset.get("size", 0)
            if url != expected_url or not match or not isinstance(size, int) or not 0 < size <= MAX_SIZE:
                continue
            return tag, url, match.group(1), size
    return None


def open_https(url):
    request = urllib.request.Request(url, headers={
        "User-Agent": "MirvDesk-SelfHosted-Updater/1.7",
        "Accept": "application/vnd.github+json",
    })
    response = urllib.request.urlopen(request, timeout=40)
    final = urllib.parse.urlparse(response.geturl())
    if final.scheme != "https" or final.hostname not in ALLOWED_REDIRECT_HOSTS:
        response.close()
        raise ValueError("Untrusted GitHub download redirect")
    return response


def installed_version():
    result = subprocess.run(["dpkg-query", "-W", "-f=${Version}", "mirvdesk"],
                            capture_output=True, text=True, check=True)
    return result.stdout.strip()


def host_idle():
    return subprocess.run(["/usr/bin/mirvdesk", "--update-idle"],
                          capture_output=True, timeout=25).returncode == 0


def apply_update(release):
    tag, url, digest, size = release
    if not host_idle():
        print("MirvDesk remote session is active or unknown; update deferred.")
        return
    with tempfile.TemporaryDirectory(prefix="mirvdesk-update-", dir="/var/tmp") as td:
        target = Path(td) / "mirvdesk.deb"
        checksum = hashlib.sha256()
        received = 0
        with open_https(url) as response, open(target, "xb") as package:
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                received += len(chunk)
                if received > MAX_SIZE or received > size:
                    raise ValueError("Unexpected update size")
                checksum.update(chunk)
                package.write(chunk)
        if received != size or checksum.hexdigest() != digest:
            raise ValueError("Update checksum or size verification failed")
        if not host_idle():
            print("Remote session began during download; update deferred.")
            return
        print(f"Installing verified MirvDesk {tag} ({received} bytes)")
        subprocess.run(["dpkg", "-i", str(target)], check=True, timeout=180)


def main():
    if os.geteuid() != 0:
        raise PermissionError("Updater must run as root through systemd")
    lock = os.open("/run/mirvdesk-update.lock", os.O_WRONLY | os.O_CREAT | os.O_CLOEXEC | os.O_NOFOLLOW, 0o600)
    with os.fdopen(lock, "w") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        current = installed_version()
        with open_https(API) as response:
            releases = json.load(response)
        selected = choose_release(releases, current, platform.machine())
        if selected:
            apply_update(selected)
        else:
            print("No newer verified MirvDesk package for this channel/architecture.")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"MirvDesk auto-update: {exc}", file=sys.stderr)
        sys.exit(1)
