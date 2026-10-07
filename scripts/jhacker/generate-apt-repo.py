#!/usr/bin/env python3
"""Generate a minimal Debian-style apt repository metadata for Jhacker Terminal.

For a directory of .deb files, this script:
  * parses each ar archive manually (stdlib only),
  * extracts control.tar.xz with the tarfile module and parses the `control` file,
  * copies each deb into <repo-root>/pool/<filename> (dedupes identical filenames),
  * writes <repo-root>/dists/jhacker/main/binary-<arch>/Packages (+ .gz) per arch,
  * writes <repo-root>/dists/jhacker/Release.

Usage:
    python3 generate-apt-repo.py --debs <dir-with-debs-recursive> --out <repo-root-dir>

The repo is unsigned and intended to be used with [trusted=yes] in sources.list.
Filenames may contain '+' and are kept literal everywhere.

Stdlib only; runs on GitHub Actions ubuntu-latest runners.
"""

import argparse
import gzip
import hashlib
import os
import shutil
import sys
import tarfile
import tempfile
from datetime import datetime, timezone
from email.utils import format_datetime
from io import BytesIO

ARCHES = ["aarch64", "arm", "i686", "x86_64"]

# Fields carried over from the control file into the Packages stanza, in order.
FIELD_ORDER = [
    "Package",
    "Version",
    "Architecture",
    "Maintainer",
    "Installed-Size",
    "Depends",
    "Pre-Depends",
    "Recommends",
    "Suggests",
    "Conflicts",
    "Breaks",
    "Replaces",
    "Provides",
    "Section",
    "Priority",
    "Homepage",
    "Description",
]

COMPUTED_FIELDS = ["Filename", "Size", "MD5sum", "SHA1", "SHA256"]


# --------------------------------------------------------------------------- #
# ar archive parsing                                                          #
# --------------------------------------------------------------------------- #
def read_ar_members(deb_path):
    """Yield (name, data) for each member of an ar archive. No external tools."""
    members = []
    with open(deb_path, "rb") as f:
        magic = f.read(8)
        if magic != b"!<arch>\n":
            raise ValueError(f"not an ar archive: {deb_path}")
        while True:
            header = f.read(60)
            if not header:
                break  # normal EOF
            if len(header) < 60:
                raise ValueError(f"truncated ar header in {deb_path}")
            name = header[0:16].decode("ascii").strip()
            # GNU ar pads long names via "//" table; BSD style "#1/<len>" prefix.
            # Termux debs use plain short names; handle BSD form just in case.
            if name.startswith("#1/"):
                namelen = int(name[3:].strip())
                name = f.read(namelen).decode("ascii").rstrip("\x00")
                data_size = int(header[48:58].decode("ascii").strip()) - namelen
            else:
                name = name.rstrip("/")
                data_size = int(header[48:58].decode("ascii").strip())
            data = f.read(data_size)
            if len(data) < data_size:
                raise ValueError(f"truncated member {name!r} in {deb_path}")
            # No terminator follows member data in ar; only 2-byte alignment padding.
            if data_size % 2 == 1:
                f.read(1)  # 2-byte alignment padding
            members.append((name, data))
    return members


def find_control_member(members, deb_path):
    for name, data in members:
        if name == "control.tar.xz":
            return data
        # Tolerate other compressions if they ever appear.
        if name in ("control.tar.gz", "control.tar.zst", "control.tar"):
            return data
    raise ValueError(f"no control.tar.* member found in {deb_path}")


def read_control_file(control_tar_data, deb_path):
    """Extract the `control` file from control.tar.* bytes."""
    mode = "r:*"  # auto-detect compression (xz/gz/bz2/none)
    try:
        with tarfile.open(fileobj=BytesIO(control_tar_data), mode=mode) as tf:
            for member in tf.getmembers():
                base = os.path.basename(member.name)
                if base == "control" and member.isfile():
                    extracted = tf.extractfile(member)
                    if extracted is None:
                        continue
                    return extracted.read().decode("utf-8", errors="replace")
    except tarfile.TarError as e:
        raise ValueError(f"cannot read control.tar.* in {deb_path}: {e}")
    raise ValueError(f"no `control` file inside control.tar.* of {deb_path}")


def parse_control(text):
    """Parse Debian control fields, handling continuation lines (start with space)."""
    fields = {}
    current = None
    for raw_line in text.splitlines():
        line = raw_line.rstrip("\r")
        if not line.strip():
            continue
        if line[0] in (" ", "\t") and current is not None:
            # Continuation: RFC822 style, fold into previous field preserving newline.
            fields[current] += "\n" + line
        elif ":" in line:
            key, _, value = line.partition(":")
            key = key.strip()
            value = value.strip()
            fields[key] = value
            current = key
        # else: ignore malformed line
    return fields


# --------------------------------------------------------------------------- #
# package processing                                                          #
# --------------------------------------------------------------------------- #
def arch_from_filename(filename):
    """Return arch from `<name>_<version>_<arch>.deb`, or None if unknown.

    Note: `x86_64` itself contains an underscore, so match the longest known
    arch suffix instead of splitting on the last underscore.
    """
    if not filename.endswith(".deb"):
        return None
    stem = filename[:-4]
    for arch in sorted(ARCHES + ["all"], key=len, reverse=True):
        if stem.endswith("_" + arch):
            return arch
    return None


def sha256_of_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def process_deb(deb_path, pool_dir, seen_filenames, packages_by_arch):
    filename = os.path.basename(deb_path)
    arch = arch_from_filename(filename)
    if arch is None:
        print(f"  SKIP (arch not recognized in filename): {filename}", file=sys.stderr)
        return

    members = read_ar_members(deb_path)
    control_tar = find_control_member(members, deb_path)
    control_text = read_control_file(control_tar, deb_path)
    fields = parse_control(control_text)
    if "Package" not in fields or "Version" not in fields:
        print(f"  SKIP (control lacks Package/Version): {filename}", file=sys.stderr)
        return

    # Dedupe across CI shards: first identical filename wins.
    if filename in seen_filenames:
        print(f"  DEDUPE (already have): {filename}", file=sys.stderr)
        return
    seen_filenames.add(filename)

    pool_path = os.path.join(pool_dir, filename)
    if not os.path.exists(pool_path):
        shutil.copy2(deb_path, pool_path)
        print(f"  pooled: {filename}")
    else:
        print(f"  pool already has: {filename} (reusing)")

    target_arches = ARCHES if arch == "all" else [arch]
    for target_arch in target_arches:
        packages_by_arch[target_arch].append(
            {"filename": filename, "pool_path": pool_path, "fields": fields,
             "deb_arch": arch}
        )


# --------------------------------------------------------------------------- #
# output writers                                                              #
# --------------------------------------------------------------------------- #
def write_packages(repo_root, packages_by_arch):
    for arch in ARCHES:
        pkgs = sorted(
            packages_by_arch[arch],
            key=lambda p: (p["fields"].get("Package", ""), p["fields"].get("Version", "")),
        )
        bin_dir = os.path.join(repo_root, "dists", "jhacker", "main", f"binary-{arch}")
        os.makedirs(bin_dir, exist_ok=True)
        packages_path = os.path.join(bin_dir, "Packages")
        with open(packages_path, "w", encoding="utf-8") as out:
            for p in pkgs:
                fields = p["fields"]
                stanza = []
                for key in FIELD_ORDER:
                    if key in fields:
                        value = fields[key]
                        if "\n" in value:
                            # First line after "Key:", continuation lines keep leading space.
                            first, rest = value.split("\n", 1)
                            value = first + "\n" + rest
                        stanza.append(f"{key}: {value}")
                size = os.path.getsize(p["pool_path"])
                with open(p["pool_path"], "rb") as f:
                    data = f.read()
                stanza.append(f"Filename: pool/{p['filename']}")
                stanza.append(f"Size: {size}")
                stanza.append(f"MD5sum: {hashlib.md5(data).hexdigest()}")
                stanza.append(f"SHA1: {hashlib.sha1(data).hexdigest()}")
                stanza.append(f"SHA256: {hashlib.sha256(data).hexdigest()}")
                out.write("\n".join(stanza) + "\n\n")
        # Packages.gz next to Packages (mtime=0 for reproducible output).
        with open(packages_path, "rb") as f_in:
            raw = f_in.read()
        with gzip.GzipFile(packages_path + ".gz", "wb", mtime=0) as f_out:
            f_out.write(raw)
        print(f"  wrote {packages_path} ({len(pkgs)} packages)")


def write_release(repo_root):
    release_dir = os.path.join(repo_root, "dists", "jhacker")
    os.makedirs(release_dir, exist_ok=True)
    date_str = format_datetime(datetime.now(timezone.utc))
    content = (
        "Origin: Jhacker Terminal\n"
        "Label: Jhacker\n"
        "Suite: jhacker\n"
        "Codename: jhacker\n"
        f"Date: {date_str}\n"
        "Components: main\n"
        "Architectures: aarch64 arm i686 x86_64\n"
        "Description: Jhacker Terminal package repository\n"
    )
    path = os.path.join(release_dir, "Release")
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"  wrote {path}")


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Generate apt repo metadata (dists/jhacker) from .deb files."
    )
    parser.add_argument("--debs", required=True, help="directory with .deb files (searched recursively)")
    parser.add_argument("--out", required=True, help="repo root directory to write into")
    args = parser.parse_args(argv)

    debs_dir = args.debs
    repo_root = args.out
    if not os.path.isdir(debs_dir):
        parser.error(f"--debs is not a directory: {debs_dir}")

    pool_dir = os.path.join(repo_root, "pool")
    os.makedirs(pool_dir, exist_ok=True)

    deb_files = []
    for dirpath, _dirnames, filenames in os.walk(debs_dir):
        for fn in filenames:
            if fn.endswith(".deb"):
                deb_files.append(os.path.join(dirpath, fn))
    deb_files.sort()
    print(f"found {len(deb_files)} .deb file(s) under {debs_dir}")

    seen_filenames = set()
    packages_by_arch = {arch: [] for arch in ARCHES}
    for deb_path in deb_files:
        try:
            process_deb(deb_path, pool_dir, seen_filenames, packages_by_arch)
        except Exception as e:  # keep going past one bad deb
            print(f"  ERROR on {deb_path}: {e}", file=sys.stderr)

    write_packages(repo_root, packages_by_arch)
    write_release(repo_root)
    print("done.")


if __name__ == "__main__":
    main()
