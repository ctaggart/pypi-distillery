#!/usr/bin/env python3
"""Download distillery release assets and repackage them as Python wheels."""

# /// script
# requires-python = ">=3.12"
# dependencies = ["requests"]
# ///

import hashlib
import io
import re
import stat
import sys
import tarfile
import zipfile
from base64 import urlsafe_b64encode
from pathlib import Path

import requests  # type: ignore[import-untyped]

IMPORT_NAME = "distillery_cli"
DIST_NAME = "distillery_bin"
UPSTREAM_REPO = "ctaggart/distillery"

# Map distillery release platform keys to Python wheel platform tags.
# Go binaries built with CGO_ENABLED=0 are fully static, so the same
# linux binary works for both glibc and musl systems.
PLATFORMS = {
    "linux-amd64": {
        "ext": ".tar.gz",
        "tag": "manylinux_2_17_x86_64.manylinux2014_x86_64",
        "binary": "dist",
    },
    "linux-amd64-musl": {
        "ext": ".tar.gz",
        "asset_key": "linux-amd64",
        "tag": "musllinux_1_1_x86_64",
        "binary": "dist",
    },
    "linux-arm64": {
        "ext": ".tar.gz",
        "tag": "manylinux_2_17_aarch64.manylinux2014_aarch64",
        "binary": "dist",
    },
    "linux-arm64-musl": {
        "ext": ".tar.gz",
        "asset_key": "linux-arm64",
        "tag": "musllinux_1_1_aarch64",
        "binary": "dist",
    },
    "darwin-amd64": {
        "ext": ".tar.gz",
        "tag": "macosx_10_9_x86_64",
        "binary": "dist",
    },
    "darwin-arm64": {
        "ext": ".tar.gz",
        "tag": "macosx_11_0_arm64",
        "binary": "dist",
    },
    "windows-amd64": {
        "ext": ".zip",
        "tag": "win_amd64",
        "binary": "dist.exe",
    },
    "windows-arm64": {
        "ext": ".zip",
        "tag": "win_arm64",
        "binary": "dist.exe",
    },
}

# PEP 440 pre-release labels that are valid on PyPI.
_PEP440_PRE_LABELS = {"a", "alpha", "b", "beta", "rc", "preview", "dev"}


def to_pep440(version: str) -> str:
    """Convert a GitHub release version to a PEP 440 compatible version.

    Stable versions pass through unchanged. Pre-release segments like
    ``1.8.13-ct.1`` or ``1.8.13-foo.3`` are converted to ``1.8.13.dev1``
    or ``1.8.13.dev3``. Recognised PEP 440 labels (a, b, rc, dev) are
    kept as-is, e.g. ``1.8.13-rc.1`` becomes ``1.8.13rc1``.
    """
    m = re.match(r"^(\d+(?:\.\d+)*)(?:-([a-zA-Z]+)\.?(\d+))?$", version)
    if not m:
        raise ValueError(f"Cannot parse version: {version!r}")
    base, label, num = m.group(1), m.group(2), m.group(3)
    if label is None:
        return base
    label_lower = label.lower()
    if label_lower in _PEP440_PRE_LABELS:
        return f"{base}.{label_lower}{num}" if label_lower == "dev" else f"{base}{label_lower}{num}"
    return f"{base}.dev{num}"
    """Return url-safe base64 sha256 digest (no padding)."""
    return urlsafe_b64encode(hashlib.sha256(data).digest()).rstrip(b"=").decode()


def download_asset(version: str, platform_key: str, ext: str) -> bytes:
    """Download a distillery release asset."""
    asset_name = f"distillery-v{version}-{platform_key}{ext}"
    url = f"https://github.com/{UPSTREAM_REPO}/releases/download/v{version}/{asset_name}"
    print(f"  Downloading {asset_name} ...")
    resp = requests.get(url, allow_redirects=True, timeout=300)
    resp.raise_for_status()
    return resp.content


def extract_binary(data: bytes, ext: str, binary_name: str) -> bytes:
    """Extract just the binary from an archive."""
    if ext == ".tar.gz":
        with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as tf:
            for member in tf.getmembers():
                if member.name == binary_name or member.name.endswith(f"/{binary_name}"):
                    f = tf.extractfile(member)
                    if f is not None:
                        return f.read()
    elif ext == ".zip":
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            for name in zf.namelist():
                if name == binary_name or name.endswith(f"/{binary_name}"):
                    return zf.read(name)

    raise FileNotFoundError(f"Binary {binary_name!r} not found in archive")


_EXEC_ATTR = (
    stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH
) << 16
_FILE_ATTR = (stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH) << 16


def build_wheel(
    release_version: str,
    wheel_version: str,
    platform_key: str,
    info: dict[str, str],
    dist_dir: Path,
    *,
    asset_cache: dict[str, bytes],
) -> Path:
    """Build a single platform wheel."""
    ext = info["ext"]
    platform_tag = info["tag"]
    binary_name = info["binary"]
    # Allow reusing the same downloaded asset for musl variants.
    asset_key = info.get("asset_key", platform_key)

    if asset_key not in asset_cache:
        asset_cache[asset_key] = download_asset(release_version, asset_key, ext)
    data = asset_cache[asset_key]

    binary_data = extract_binary(data, ext, binary_name)

    # Collect wheel entries: (arcname, data_bytes, is_executable)
    entries: list[tuple[str, bytes, bool]] = []

    # Add __init__.py
    init_py = Path(__file__).resolve().parent.parent / "python" / IMPORT_NAME / "__init__.py"
    entries.append(
        (f"{IMPORT_NAME}/__init__.py", init_py.read_bytes(), False)
    )

    # Add the binary
    entries.append((f"{IMPORT_NAME}/{binary_name}", binary_data, True))

    # dist-info directory
    dist_info_dir = f"{DIST_NAME}-{wheel_version}.dist-info"

    readme_path = Path(__file__).resolve().parent.parent / "README.md"
    readme_text = readme_path.read_text(encoding="utf-8")

    metadata = (
        f"Metadata-Version: 2.4\n"
        f"Name: distillery-bin\n"
        f"Version: {wheel_version}\n"
        f"Summary: Distillery CLI repackaged as Python wheels\n"
        f"Home-page: https://github.com/ekristen/distillery\n"
        f"License: MIT\n"
        f"Requires-Python: >=3.9\n"
        f"Description-Content-Type: text/markdown\n"
        f"\n"
        f"{readme_text}"
    )
    entries.append((f"{dist_info_dir}/METADATA", metadata.encode(), False))

    wheel_meta = (
        f"Wheel-Version: 1.0\n"
        f"Generator: build_wheels.py\n"
        f"Root-Is-Purelib: false\n"
        f"Tag: py3-none-{platform_tag}\n"
    )
    entries.append((f"{dist_info_dir}/WHEEL", wheel_meta.encode(), False))

    entry_points = f"[console_scripts]\ndist = {IMPORT_NAME}:main\n"
    entries.append(
        (f"{dist_info_dir}/entry_points.txt", entry_points.encode(), False)
    )

    # Build RECORD
    records: list[str] = []
    for arcname, file_data, _ in entries:
        digest = sha256_digest(file_data)
        records.append(f"{arcname},sha256={digest},{len(file_data)}")
    records.append(f"{dist_info_dir}/RECORD,,")
    record_data = ("\n".join(records) + "\n").encode()
    entries.append((f"{dist_info_dir}/RECORD", record_data, False))

    # Write wheel zip
    wheel_name = f"{DIST_NAME}-{wheel_version}-py3-none-{platform_tag}.whl"
    wheel_path = dist_dir / wheel_name
    with zipfile.ZipFile(wheel_path, "w", zipfile.ZIP_DEFLATED) as whl:
        for arcname, file_data, executable in entries:
            zi = zipfile.ZipInfo(arcname)
            zi.compress_type = zipfile.ZIP_DEFLATED
            zi.external_attr = _EXEC_ATTR if executable else _FILE_ATTR
            whl.writestr(zi, file_data)

    print(f"  Built {wheel_name} ({wheel_path.stat().st_size / 1024 / 1024:.1f} MB)")
    return wheel_path


def main() -> None:
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <version>")
        print(f"Example: {sys.argv[0]} 1.8.11")
        sys.exit(1)

    release_version = sys.argv[1]
    wheel_version = to_pep440(release_version)
    dist_dir = Path("dist")
    dist_dir.mkdir(exist_ok=True)

    if wheel_version != release_version:
        print(f"Building wheels for distillery v{release_version} (PyPI version {wheel_version})\n")
    else:
        print(f"Building wheels for distillery v{release_version}\n")

    asset_cache: dict[str, bytes] = {}
    wheels: list[Path] = []
    for platform_key, info in PLATFORMS.items():
        print(f"[{platform_key}]")
        wheel = build_wheel(release_version, wheel_version, platform_key, info, dist_dir, asset_cache=asset_cache)
        wheels.append(wheel)
        print()

    print(f"Done! {len(wheels)} wheels in {dist_dir}/")
    for w in wheels:
        print(f"  {w.name}")


if __name__ == "__main__":
    main()
