#!/usr/bin/env python3
"""Read-only verifier for Project Shadow R1.0.1 outer directories or ZIPs."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
import stat
import sys
import zipfile
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Any


TITLE = "Project Shadow 1.0.1 — R1 Reference Packaging Correction"
ROOT = "Project_Shadow_R1.0.1_Public_Reference_2026-08-17"
ARCHIVE = f"{ROOT}.zip"
TAG = "r1.0.1-2026-08-17"
FIXED_ZIP_TIME = (2026, 8, 17, 0, 0, 0)

INNER_ROOT = "Project_Shadow_R1.0.1_Runtime_Family_Myth_Decoupled_2026-08-17"
INNER_FILENAME = f"{INNER_ROOT}.zip"
INNER_EXPECTED_INVENTORY_PATH = "08_VERIFICATION/EXPECTED_FILE_INVENTORY.json"
INNER_EXPECTED_INVENTORY_SHA256 = "4cdc1611bf11d56694b4868eebbc705e339a0b6a76455d4cd75374fb0b7b0c22"
INNER_EXPECTED_FILE_COUNT = 85
ADMITTED_INNER_BYTES = 5_463_189
ADMITTED_INNER_SHA256 = "c8c32b12432c954b1a6f852c0c9f81bbbd40167e936be057d4c3de1a0aa3a623"
OLD_INNER_FILENAME = "Project_Shadow_R1_BETA2_Runtime_Successor_Candidate_2026-08-10.zip"
OLD_INNER_SHA256 = "075b41ea4186b2d2edb0ed246ab7662cf8bbdf3160294e3eca176b9d0857b108"
OLD_INNER_BYTES = 5_442_808

PC_FILENAME = "Project_Shadow_PS-R1-PC-S1_v0.1.0-beta.5_POST_REAUDIT_CORRECTION_CANDIDATE_2026-08-10.zip"
PC_SHA256 = "1ffdba41025c0b81da92d0bbb22d0eaa69488cffbc80936365034669110448d7"
PC_BYTES = 1_935_482

OLD_OUTER_FILENAME = "Project_Shadow_R1_Public_Release_Candidate_2026-08-14.zip"
OLD_OUTER_SHA256 = "2f8fe1530b6a83294d15011df95853aaecf08fa4dba756f0c2e91dd089e1b1ec"
OLD_OUTER_BYTES = 7_679_812
OLD_OUTER_TAG = "r1-2026-08-14"

REMOVED_MYTH_FILENAME = "Project_Shadow_R1_Myth_Sidecar_Generic_v0.1.1_PRIVATE_2026-08-07.zip"
REMOVED_MYTH_SHA256 = "4d8481ed8f6af3e04d86a5c2de7e94aad47a591e1ce9c8757bbb4b0a397b90bb"
REMOVED_MYTH_BYTES = 29_763

GENERIC = {
    "filename": "Project_Shadow_Generic_Myth_Sidecar_v0.2.0_OPTIONAL_PUBLIC_COMPANION_2026-08-17.zip",
    "bytes": 93_676,
    "sha256": "6e7a362d4135f9d626dcfef463bfb1f7166226b3cf8a4c02a953ab39af1538bf",
    "tag": "generic-myth-v0.2.0",
    "version": "0.2.0",
    "mixed_rights": False,
}
FULL_CANON = {
    "filename": "Project_Shadow_Full_Canon_Myth_Sidecar_v0.3.5_OPTIONAL_PUBLIC_COMPANION_2026-08-17.zip",
    "bytes": 1_428_812,
    "sha256": "2b55867fe7c502a0defd8d6f2e9b53fbd1caaf1b0f225a438bd45b04a3e7bae2",
    "tag": "myth-v0.3.5",
    "version": "0.3.5",
    "mixed_rights": True,
}

ACTIVE_PREFIXES = (
    "02_EDITIONS/",
    "03_PS_LANGUAGE/",
    "04_PYTHON_REFERENCES/",
    "05_KERNELS/",
    "06_PROMPTS/",
)
MAX_MEMBERS = 50_000
MAX_UNCOMPRESSED = 1_500_000_000
MAX_RECURSION = 8
HEX64 = re.compile(r"^[0-9a-f]{64}$")

OUTER_PENDING_INVENTORY = frozenset(
    {
        "00_START_HERE.md",
        "01_AUTHORITY/INNER_ADMISSION_SLOT.json",
        "02_STATUS/PUBLIC_REFERENCE_STATUS.json",
        "03_AUDIT/R1_1.0.1_DESCENDANT_BYTE_IDENTITY_MAP.json",
        "03_AUDIT/OUTER_BUILD_RECEIPT.json",
        "04_CORRECTION/CAPA_PS-R1-PRIVATE-MYTH-PUBLIC-BOUNDARY-001.json",
        "04_CORRECTION/CORRECTION_NOTICE.md",
        f"05_COMPONENTS/R1/{INNER_FILENAME}",
        f"05_COMPONENTS/PRIMITIVE_COMMONS/{PC_FILENAME}",
        "06_EXTERNAL_SIDECARS/GENERIC_MYTH_V0.2.0_REFERENCE.json",
        "06_EXTERNAL_SIDECARS/FULL_CANON_MYTH_V0.3.5_REFERENCE.json",
        "07_HISTORICAL/PRESERVED_AUGUST_14_R1_REFERENCE.json",
        "LICENSE",
        "LICENSE-DOCS",
        "NOTICE",
        "RIGHTS_MANIFEST.json",
        "SAFETY_AND_SECRET_SCAN_REPORT.json",
        "tools/verify_outer_release.py",
        "PACKAGE_MANIFEST.json",
        "SHA256SUMS",
    }
)
OUTER_BOUND_INVENTORY = OUTER_PENDING_INVENTORY | {
    "01_AUTHORITY/INNER_EXACT_HASH_MAINTAINER_ADMISSION.json"
}
FORBIDDEN_CURRENT_CLASSIFICATION_TOKENS = (
    b"PRIVATE_" + b"INTERNAL",
    b"EXCLUDED_" + b"FROM_PUBLIC",
    b'"public_manufacture_' + b'eligible":false',
    b'"public_manufacture_' + b'eligible": false',
)
INNER_SEMANTIC_EXCLUDED_PREFIXES = ("07_EXTERNAL_SIDECARS/", "11_HISTORICAL/")


class VerificationError(RuntimeError):
    """A verification control failed."""


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_member_name(name: str) -> None:
    if not name or "\\" in name or name.startswith("/"):
        raise VerificationError(f"unsafe ZIP member name: {name!r}")
    path = PurePosixPath(name.rstrip("/"))
    if not path.parts or any(part in {"", ".", ".."} for part in path.parts):
        raise VerificationError(f"unsafe ZIP member name: {name!r}")


def safe_infos(archive: zipfile.ZipFile) -> list[zipfile.ZipInfo]:
    infos = archive.infolist()
    if len(infos) > MAX_MEMBERS:
        raise VerificationError("ZIP member count exceeds safety limit")
    total = 0
    seen: set[str] = set()
    for info in infos:
        validate_member_name(info.filename)
        if info.filename in seen:
            raise VerificationError(f"duplicate ZIP member: {info.filename}")
        seen.add(info.filename)
        mode = (info.external_attr >> 16) & 0xFFFF
        if stat.S_ISLNK(mode):
            raise VerificationError(f"symlink ZIP member rejected: {info.filename}")
        total += info.file_size
        if total > MAX_UNCOMPRESSED:
            raise VerificationError("ZIP uncompressed size exceeds safety limit")
    return infos


def one_zip_root(archive: zipfile.ZipFile) -> str:
    roots = {
        PurePosixPath(info.filename.rstrip("/")).parts[0]
        for info in safe_infos(archive)
    }
    if len(roots) != 1:
        raise VerificationError(f"ZIP must contain exactly one root: {sorted(roots)}")
    return next(iter(roots))


class PackageReader:
    """Read-only abstraction over a package directory or outer ZIP."""

    def __init__(self, source: Path):
        self.source = source
        self.archive: zipfile.ZipFile | None = None
        self.archive_bytes: bytes | None = None
        self.root = ROOT
        self.deterministic_metadata_verified = False
        if source.is_dir():
            if source.name != ROOT:
                raise VerificationError(f"directory root must be named {ROOT}")
            self.kind = "directory"
            self._files = {
                path.relative_to(source).as_posix()
                for path in source.rglob("*")
                if path.is_file()
            }
            for path in source.rglob("*"):
                if path.is_symlink():
                    raise VerificationError(f"symlink rejected in directory package: {path}")
        elif source.is_file():
            if source.name != ARCHIVE:
                raise VerificationError(f"outer ZIP must be named {ARCHIVE}")
            self.kind = "zip"
            self.archive_bytes = source.read_bytes()
            self.archive = zipfile.ZipFile(io.BytesIO(self.archive_bytes))
            root = one_zip_root(self.archive)
            if root != ROOT:
                raise VerificationError(f"outer ZIP root must be {ROOT}, found {root}")
            infos = safe_infos(self.archive)
            self._files = {
                PurePosixPath(info.filename).relative_to(root).as_posix()
                for info in infos
                if not info.is_dir()
            }
            for info in infos:
                if info.is_dir():
                    continue
                mode = (info.external_attr >> 16) & 0xFFFF
                if info.date_time != FIXED_ZIP_TIME:
                    raise VerificationError(f"non-deterministic timestamp on {info.filename}")
                if stat.S_IMODE(mode) != 0o644 or not stat.S_ISREG(mode):
                    raise VerificationError(f"non-deterministic mode on {info.filename}: {oct(mode)}")
                if info.compress_type != zipfile.ZIP_DEFLATED:
                    raise VerificationError(f"non-deterministic compression on {info.filename}")
            self.deterministic_metadata_verified = True
        else:
            raise VerificationError(f"package path not found: {source}")

    def files(self) -> set[str]:
        return set(self._files)

    def read(self, relative: str) -> bytes:
        if relative not in self._files:
            raise VerificationError(f"missing package file: {relative}")
        if self.kind == "directory":
            return (self.source / PurePosixPath(relative)).read_bytes()
        assert self.archive is not None
        return self.archive.read(f"{ROOT}/{relative}")

    def close(self) -> None:
        if self.archive is not None:
            self.archive.close()


def read_json(reader: PackageReader, path: str) -> dict[str, Any]:
    try:
        value = json.loads(reader.read(path))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise VerificationError(f"invalid UTF-8 JSON: {path}") from exc
    if not isinstance(value, dict):
        raise VerificationError(f"expected JSON object: {path}")
    return value


def parse_sums(data: bytes) -> dict[str, str]:
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise VerificationError("SHA256SUMS is not UTF-8") from exc
    result: dict[str, str] = {}
    for number, line in enumerate(text.splitlines(), start=1):
        match = re.fullmatch(r"([0-9a-f]{64})  ([^\r\n]+)", line)
        if not match:
            raise VerificationError(f"invalid SHA256SUMS line {number}")
        digest, path = match.groups()
        validate_member_name(path)
        if path in result:
            raise VerificationError(f"duplicate SHA256SUMS path: {path}")
        result[path] = digest
    return result


def verify_sums(reader: PackageReader) -> None:
    sums = parse_sums(reader.read("SHA256SUMS"))
    expected = reader.files() - {"SHA256SUMS"}
    if set(sums) != expected:
        missing = sorted(expected - set(sums))
        extra = sorted(set(sums) - expected)
        raise VerificationError(f"SHA256SUMS coverage mismatch; missing={missing}, extra={extra}")
    for path, expected_hash in sums.items():
        if sha256_bytes(reader.read(path)) != expected_hash:
            raise VerificationError(f"SHA256SUMS mismatch: {path}")


def exact_outer_inventory_mode(paths: set[str]) -> str:
    """Match the actual package against a code-owned, authority-specific set."""
    if paths == OUTER_PENDING_INVENTORY:
        return "PENDING"
    if paths == OUTER_BOUND_INVENTORY:
        return "BOUND"
    allowed_union = OUTER_BOUND_INVENTORY
    missing = sorted(OUTER_PENDING_INVENTORY - paths)
    extra = sorted(paths - allowed_union)
    if not extra and paths - OUTER_PENDING_INVENTORY:
        extra = sorted(paths - OUTER_PENDING_INVENTORY)
    raise VerificationError(
        f"code-owned exact outer file inventory mismatch; missing={missing}, extra={extra}"
    )


def verify_inner_exact_inventory(inner_data: bytes) -> set[str]:
    try:
        archive = zipfile.ZipFile(io.BytesIO(inner_data))
    except zipfile.BadZipFile as exc:
        raise VerificationError("corrected inner component is not a ZIP") from exc
    with archive:
        root = one_zip_root(archive)
        if root != INNER_ROOT:
            raise VerificationError(f"corrected inner root mismatch: {root}")
        files = {
            PurePosixPath(info.filename).relative_to(root).as_posix(): archive.read(info)
            for info in safe_infos(archive)
            if not info.is_dir()
        }
    inventory_raw = files.get(INNER_EXPECTED_INVENTORY_PATH)
    if inventory_raw is None or sha256_bytes(inventory_raw) != INNER_EXPECTED_INVENTORY_SHA256:
        raise VerificationError("inner code-owned exact inventory hash mismatch")
    try:
        inventory = json.loads(inventory_raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise VerificationError("invalid inner exact inventory JSON") from exc
    paths = inventory.get("paths")
    if (
        inventory.get("schema") != "project-shadow.exact-file-inventory.v1"
        or inventory.get("status") != "EXACT_PATH_SET_REQUIRED_NO_UNINDEXED_FILES"
        or inventory.get("expected_file_count") != INNER_EXPECTED_FILE_COUNT
        or not isinstance(paths, list)
        or len(paths) != INNER_EXPECTED_FILE_COUNT
        or len(set(paths)) != INNER_EXPECTED_FILE_COUNT
        or set(paths) != set(files)
    ):
        raise VerificationError("inner exact file inventory does not match the code-frozen 85-path package")
    if "SHA256SUMS" not in files:
        raise VerificationError("inner SHA256SUMS is missing")
    sums = parse_sums(files["SHA256SUMS"])
    expected_sum_paths = set(files) - {"SHA256SUMS"}
    if set(sums) != expected_sum_paths:
        raise VerificationError("inner SHA256SUMS does not have exact full-file coverage")
    for path, expected_hash in sums.items():
        if sha256_bytes(files[path]) != expected_hash:
            raise VerificationError(f"inner SHA256SUMS mismatch: {path}")
    return set(files)


def scan_classification_payload(
    data: bytes,
    label: str,
    *,
    depth: int = 0,
    budget: list[int] | None = None,
) -> tuple[int, int]:
    if budget is None:
        budget = [0, 0]
    budget[0] += 1
    budget[1] += len(data)
    if budget[0] > MAX_MEMBERS or budget[1] > MAX_UNCOMPRESSED:
        raise VerificationError("current-payload semantic scan safety budget exceeded")
    for token in FORBIDDEN_CURRENT_CLASSIFICATION_TOKENS:
        if token in data:
            raise VerificationError(
                f"nonpublic classification token at {label}: {token.decode('ascii')}"
            )
    if not data.startswith(b"PK\x03\x04"):
        return 1, len(data)
    if depth >= MAX_RECURSION:
        raise VerificationError(f"current-payload semantic recursion limit exceeded at {label}")
    try:
        archive = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile as exc:
        raise VerificationError(f"ZIP-signature payload is malformed at {label}") from exc
    members = 1
    unpacked = len(data)
    with archive:
        for info in safe_infos(archive):
            if info.is_dir():
                continue
            child_members, child_bytes = scan_classification_payload(
                archive.read(info),
                f"{label}!/{info.filename}",
                depth=depth + 1,
                budget=budget,
            )
            members += child_members
            unpacked += child_bytes
    return members, unpacked


def scan_all_current_inner_payloads(inner_data: bytes) -> tuple[int, int]:
    members = 0
    unpacked = 0
    budget = [0, 0]
    with zipfile.ZipFile(io.BytesIO(inner_data)) as archive:
        root = one_zip_root(archive)
        for info in safe_infos(archive):
            if info.is_dir():
                continue
            relative = PurePosixPath(info.filename).relative_to(root).as_posix()
            if relative.startswith(INNER_SEMANTIC_EXCLUDED_PREFIXES):
                continue
            child_members, child_bytes = scan_classification_payload(
                archive.read(info),
                relative,
                budget=budget,
            )
            members += child_members
            unpacked += child_bytes
    return members, unpacked


def scan_outer_current_controls(reader: PackageReader) -> tuple[int, int]:
    members = 0
    unpacked = 0
    budget = [0, 0]
    excluded_prefixes = (
        "05_COMPONENTS/R1/",
        "05_COMPONENTS/PRIMITIVE_COMMONS/",
        "06_EXTERNAL_SIDECARS/",
        "07_HISTORICAL/",
    )
    for path in sorted(reader.files()):
        if path.startswith(excluded_prefixes):
            continue
        child_members, child_bytes = scan_classification_payload(
            reader.read(path),
            path,
            budget=budget,
        )
        members += child_members
        unpacked += child_bytes
    return members, unpacked


def active_rows(index: dict[str, Any]) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    for row in index.get("artifacts", []):
        path = row.get("path")
        if isinstance(path, str) and path.startswith(ACTIVE_PREFIXES):
            if path in rows:
                raise VerificationError(f"duplicate active artifact path: {path}")
            rows[path] = row
    if index.get("active_descendant_count") != 27 or len(rows) != 27:
        raise VerificationError(f"corrected inner does not expose exactly 27 active descendants: {len(rows)}")
    return rows


def nested_inner(inner_data: bytes) -> tuple[dict[str, Any], dict[str, dict[str, Any]], str]:
    try:
        archive = zipfile.ZipFile(io.BytesIO(inner_data))
    except zipfile.BadZipFile as exc:
        raise VerificationError("inner R1 component is not a ZIP") from exc
    with archive:
        root = one_zip_root(archive)
        if root != INNER_ROOT:
            raise VerificationError(f"corrected inner root mismatch: {root}")
        try:
            index = json.loads(archive.read(f"{root}/08_VERIFICATION/ARTIFACT_INDEX.json"))
            package_manifest = json.loads(archive.read(f"{root}/PACKAGE_MANIFEST.json"))
        except (KeyError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise VerificationError("corrected inner controls are missing or invalid") from exc
        rows = active_rows(index)
        for path, row in rows.items():
            try:
                payload = archive.read(f"{root}/{path}")
            except KeyError as exc:
                raise VerificationError(f"corrected inner indexed payload is missing: {path}") from exc
            if len(payload) != row.get("bytes") or sha256_bytes(payload) != row.get("sha256"):
                raise VerificationError(f"corrected inner index identity mismatch: {path}")
    required = {
        "active_descendant_count": 27,
        "private_myth_member_removed": True,
        "operational_artifact_bytes_changed": 0,
    }
    for key, expected in required.items():
        if package_manifest.get(key) != expected:
            raise VerificationError(f"corrected inner PACKAGE_MANIFEST requires {key}={expected!r}")
    if package_manifest.get("public_manufacture_eligible") is False:
        raise VerificationError("corrected inner PACKAGE_MANIFEST forbids public manufacture")
    return index, rows, root


def semantic_walk(value: Any, location: str) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            key_lower = str(key).lower()
            if key_lower == "public_manufacture_eligible" and child is False:
                raise VerificationError(f"active manifest has public_manufacture_eligible=false at {location}.{key}")
            semantic_walk(child, f"{location}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            semantic_walk(child, f"{location}[{index}]")
    elif isinstance(value, str) and value.upper() in {
        "PRIVATE_" + "INTERNAL",
        "EXCLUDED_" + "FROM_PUBLIC",
    }:
        raise VerificationError(f"active manifest has forbidden semantic value {value!r} at {location}")


def is_active_manifest_path(name: str) -> bool:
    parts = [part.upper() for part in PurePosixPath(name).parts]
    excluded = {"HISTORICAL", "HISTORY", "EVIDENCE", "AUDIT", "RECEIPTS", "ADMISSION"}
    if any(part in excluded for part in parts[:-1]):
        return False
    basename = parts[-1]
    return basename in {"PACKAGE_MANIFEST.JSON", "MANIFEST.JSON"}


def verify_active_manifest_semantics(inner_data: bytes, rows: dict[str, dict[str, Any]], root: str) -> int:
    checked = 0
    with zipfile.ZipFile(io.BytesIO(inner_data)) as inner:
        for path in sorted(rows):
            if not path.lower().endswith(".zip"):
                continue
            artifact = inner.read(f"{root}/{path}")
            try:
                child = zipfile.ZipFile(io.BytesIO(artifact))
            except zipfile.BadZipFile as exc:
                raise VerificationError(f"active indexed ZIP is invalid: {path}") from exc
            with child:
                for info in safe_infos(child):
                    if info.is_dir() or not is_active_manifest_path(info.filename):
                        continue
                    try:
                        manifest = json.loads(child.read(info))
                    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                        raise VerificationError(f"invalid active manifest JSON: {path}!/{info.filename}") from exc
                    semantic_walk(manifest, f"{path}!/{info.filename}")
                    checked += 1
    return checked


def recursive_forbidden_scan(
    data: bytes,
    forbidden: set[str],
    label: str,
    *,
    depth: int = 0,
    budget: list[int] | None = None,
) -> tuple[int, int]:
    if budget is None:
        budget = [0, 0]
    if depth > MAX_RECURSION:
        raise VerificationError(f"nested ZIP recursion limit exceeded at {label}")
    try:
        archive = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile:
        return 0, 0
    members = 0
    unpacked = 0
    with archive:
        for info in safe_infos(archive):
            if info.is_dir():
                continue
            payload = archive.read(info)
            budget[0] += 1
            budget[1] += len(payload)
            if budget[0] > MAX_MEMBERS or budget[1] > MAX_UNCOMPRESSED:
                raise VerificationError("recursive scan safety budget exceeded")
            digest = sha256_bytes(payload)
            if digest in forbidden:
                raise VerificationError(f"forbidden embedded payload {digest} at {label}!/{info.filename}")
            members += 1
            unpacked += len(payload)
            if info.filename.lower().endswith(".zip"):
                child_count, child_bytes = recursive_forbidden_scan(
                    payload,
                    forbidden,
                    f"{label}!/{info.filename}",
                    depth=depth + 1,
                    budget=budget,
                )
                members += child_count
                unpacked += child_bytes
    return members, unpacked


def validate_external_reference(value: dict[str, Any], expected: dict[str, Any]) -> None:
    for key in ("filename", "bytes", "sha256", "tag", "version", "mixed_rights"):
        if value.get(key) != expected[key]:
            raise VerificationError(f"external sidecar reference mismatch: {key}")
    requirements = {
        "canonical_r1": False,
        "default_enabled": False,
        "embedded": False,
        "feedback_into_r1": False,
        "operational_authority": False,
        "optional": True,
        "production_deployment": "HARD_OFF",
        "relationship_to_r1": "SEPARATE_OPTIONAL_PUBLIC_COMPANION",
        "required_for_r1": False,
        "terminal_only": True,
    }
    for key, expected_value in requirements.items():
        if value.get(key) != expected_value:
            raise VerificationError(f"external sidecar boundary mismatch: {key}")


def validate_inner_sidecar_references(inner_data: bytes) -> None:
    references = (
        (
            "07_EXTERNAL_SIDECARS/PROJECT_SHADOW_GENERIC_MYTH_REFERENCE.json",
            GENERIC,
        ),
        (
            "07_EXTERNAL_SIDECARS/PROJECT_SHADOW_FULL_CANON_MYTH_V0.3.5_REFERENCE.json",
            FULL_CANON,
        ),
    )
    with zipfile.ZipFile(io.BytesIO(inner_data)) as archive:
        root = one_zip_root(archive)
        for relative, expected in references:
            try:
                value = json.loads(archive.read(f"{root}/{relative}"))
            except (KeyError, UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise VerificationError(f"invalid corrected inner sidecar reference: {relative}") from exc
            for key in ("filename", "bytes", "sha256", "version", "mixed_rights"):
                if value.get(key) != expected[key]:
                    raise VerificationError(
                        f"corrected inner sidecar reference mismatch: {relative}:{key}"
                    )
            boundary = {
                "authority_effect_on_r1": "NONE",
                "authorizes": False,
                "default_enabled": False,
                "included_in_r1": False,
                "operational_authority": False,
                "publication_status": "EXTERNAL_TO_THIS_FAMILY",
                "relationship_to_r1": "SEPARATE_OPTIONAL_COMPANION",
                "required_for_r1": False,
                "terminal_only": True,
            }
            for key, expected_value in boundary.items():
                if value.get(key) != expected_value:
                    raise VerificationError(
                        f"corrected inner sidecar boundary mismatch: {relative}:{key}"
                    )


def validate_admission_record(data: bytes, inner_hash: str, inner_size: int) -> None:
    try:
        record = json.loads(data)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise VerificationError("invalid embedded inner admission record") from exc
    if not isinstance(record, dict):
        raise VerificationError("embedded inner admission record must be a JSON object")
    expected_top_keys = {
        "schema",
        "decision",
        "inner",
        "maintainer_confirmation",
        "non_authorizations",
    }
    if set(record) != expected_top_keys:
        raise VerificationError(
            "embedded inner admission record has unexpected or missing top-level keys"
        )
    if inner_hash != ADMITTED_INNER_SHA256 or inner_size != ADMITTED_INNER_BYTES:
        raise VerificationError(
            "inner admission applies only to the exact maintainer-admitted artifact"
        )
    expected_statement = (
        "I admit the exact Myth-free R1.0.1 inner family—5,463,189 bytes, SHA-256 "
        "c8c32b12432c954b1a6f852c0c9f81bbbd40167e936be057d4c3de1a0aa3a623—for R1.0.1 "
        "reference packaging. Its 27 active descendants are byte-identical to the August 14 "
        "predecessor, no Myth payload is embedded, and this admission does not authorize production, "
        "deployment, or publication."
    )
    if record.get("schema") != "project-shadow.r1.0.1-inner-exact-hash-maintainer-admission.v1":
        raise VerificationError("unsupported inner admission record schema")
    if record.get("decision") != "ADMIT_EXACT_HASH_FOR_R1.0.1_REFERENCE_PACKAGING":
        raise VerificationError("inner admission record has wrong decision")
    inner = record.get("inner")
    expected_inner_keys = {
        "filename",
        "bytes",
        "sha256",
        "active_descendant_count",
        "operational_descendant_bytes_changed",
        "myth_payload_embedded",
    }
    if not isinstance(inner, dict) or set(inner) != expected_inner_keys:
        raise VerificationError("inner admission record has unexpected or missing inner keys")
    expected_inner = {
        "filename": INNER_FILENAME,
        "bytes": ADMITTED_INNER_BYTES,
        "sha256": ADMITTED_INNER_SHA256,
        "active_descendant_count": 27,
        "operational_descendant_bytes_changed": 0,
        "myth_payload_embedded": False,
    }
    for key, expected_value in expected_inner.items():
        if inner.get(key) != expected_value:
            raise VerificationError(f"inner admission record mismatch: inner.{key}")
    confirmation = record.get("maintainer_confirmation")
    if not isinstance(confirmation, dict) or set(confirmation) != {
        "confirmed_by",
        "confirmed_at",
        "statement",
    }:
        raise VerificationError(
            "inner admission record has unexpected or missing maintainer_confirmation keys"
        )
    if not isinstance(confirmation.get("confirmed_by"), str) or not confirmation["confirmed_by"].strip():
        raise VerificationError("inner admission record has no confirmed_by")
    confirmed_at = confirmation.get("confirmed_at")
    if not isinstance(confirmed_at, str):
        raise VerificationError("inner admission record has no UTC confirmed_at")
    try:
        datetime.strptime(confirmed_at, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError as exc:
        raise VerificationError(
            "inner admission confirmed_at must be strict UTC RFC3339 seconds"
        ) from exc
    if confirmation.get("statement") != expected_statement:
        raise VerificationError("inner admission record statement mismatch")
    if record.get("non_authorizations") != {
        "production_authorized": False,
        "deployment_authorized": False,
        "publication_authorized": False,
    }:
        raise VerificationError("inner admission record changed a non-authorization")


def verify_package(source: Path) -> dict[str, Any]:
    checks: list[str] = []
    reader = PackageReader(source)
    try:
        inventory_mode = exact_outer_inventory_mode(reader.files())
        checks.append(f"CODE_OWNED_EXACT_OUTER_INVENTORY_PASS;MODE={inventory_mode}")
        verify_sums(reader)
        checks.append("SHA256SUMS_FULL_COVERAGE_PASS")

        manifest = read_json(reader, "PACKAGE_MANIFEST.json")
        fixed = {
            "schema": "project-shadow.r1.0.1-public-reference-package-manifest.v1",
            "release_identity": TITLE,
            "root": ROOT,
            "tag": TAG,
            "active_descendant_count": 27,
            "operational_descendant_bytes_changed": 0,
            "myth_payloads_embedded": 0,
            "publication_authorized": False,
        }
        for key, expected in fixed.items():
            if manifest.get(key) != expected:
                raise VerificationError(f"PACKAGE_MANIFEST mismatch: {key}")
        if manifest.get("capa") != {
            "id": "PS-R1-PRIVATE-MYTH-PUBLIC-BOUNDARY-001",
            "status": "IMPLEMENTED_PENDING_EFFECTIVENESS",
        }:
            raise VerificationError("PACKAGE_MANIFEST CAPA status mismatch")
        expected_inventory_count = (
            len(OUTER_BOUND_INVENTORY) if inventory_mode == "BOUND" else len(OUTER_PENDING_INVENTORY)
        )
        if manifest.get("exact_file_inventory_count") != expected_inventory_count:
            raise VerificationError("PACKAGE_MANIFEST exact file inventory count mismatch")
        listed = {
            row.get("path"): (row.get("bytes"), row.get("sha256"))
            for row in manifest.get("files", [])
        }
        expected_listed = reader.files() - {"PACKAGE_MANIFEST.json", "SHA256SUMS"}
        if set(listed) != expected_listed:
            raise VerificationError("PACKAGE_MANIFEST file coverage mismatch")
        for path, (size, digest) in listed.items():
            data = reader.read(path)
            if len(data) != size or sha256_bytes(data) != digest:
                raise VerificationError(f"PACKAGE_MANIFEST file identity mismatch: {path}")
        checks.append("PACKAGE_MANIFEST_PASS")

        inner_path = f"05_COMPONENTS/R1/{INNER_FILENAME}"
        inner_data = reader.read(inner_path)
        inner_expected = manifest.get("components", {}).get("inner_r1", {})
        inner_hash = sha256_bytes(inner_data)
        if (
            inner_expected.get("filename") != INNER_FILENAME
            or inner_expected.get("bytes") != len(inner_data)
            or inner_expected.get("sha256") != inner_hash
            or not HEX64.fullmatch(inner_hash)
        ):
            raise VerificationError("corrected inner component exact identity mismatch")
        index, rows, inner_root = nested_inner(inner_data)
        inner_inventory = verify_inner_exact_inventory(inner_data)
        validate_inner_sidecar_references(inner_data)
        if len(inner_inventory) != INNER_EXPECTED_FILE_COUNT:
            raise VerificationError("corrected inner exact inventory count mismatch")
        semantic_members, semantic_bytes = scan_all_current_inner_payloads(inner_data)
        semantic_count = verify_active_manifest_semantics(inner_data, rows, inner_root)
        checks.append(
            "INNER_EXACT_INVENTORY_85_AND_CURRENT_SEMANTICS_PASS;"
            f"CURRENT_MEMBERS={semantic_members};CURRENT_BYTES={semantic_bytes};"
            f"ACTIVE_MANIFESTS_CHECKED={semantic_count}"
        )
        checks.append("INNER_ACTIVE_DESCENDANTS_27_PASS")

        pc_path = f"05_COMPONENTS/PRIMITIVE_COMMONS/{PC_FILENAME}"
        pc_data = reader.read(pc_path)
        if len(pc_data) != PC_BYTES or sha256_bytes(pc_data) != PC_SHA256:
            raise VerificationError("Primitive Commons beta.5 is not frozen byte-exact")
        if manifest.get("components", {}).get("primitive_commons_beta5") != {
            "bytes": PC_BYTES,
            "filename": PC_FILENAME,
            "sha256": PC_SHA256,
        }:
            raise VerificationError("Primitive Commons manifest identity mismatch")
        checks.append("PRIMITIVE_COMMONS_BETA5_EXACT_PASS")

        identity = read_json(reader, "03_AUDIT/R1_1.0.1_DESCENDANT_BYTE_IDENTITY_MAP.json")
        if (
            identity.get("active_descendant_count") != 27
            or identity.get("comparison_result") != "27_OF_27_BYTE_IDENTICAL"
            or identity.get("operational_descendant_bytes_changed") != 0
        ):
            raise VerificationError("descendant byte-identity summary mismatch")
        mapped = {row.get("path"): row for row in identity.get("active_descendants", [])}
        if set(mapped) != set(rows) or len(mapped) != 27:
            raise VerificationError("descendant byte-identity map coverage mismatch")
        for path, current in rows.items():
            row = mapped[path]
            if (
                row.get("bytes") != current.get("bytes")
                or row.get("sha256") != current.get("sha256")
                or row.get("predecessor_bytes") != current.get("bytes")
                or row.get("predecessor_sha256") != current.get("sha256")
                or row.get("status") != "BYTE_IDENTICAL_TO_AUGUST_14_ACTIVE_DESCENDANT"
            ):
                raise VerificationError(f"descendant byte-identity map mismatch: {path}")
        predecessor = identity.get("predecessor_inner", {})
        if predecessor != {
            "bytes": OLD_INNER_BYTES,
            "filename": OLD_INNER_FILENAME,
            "sha256": OLD_INNER_SHA256,
        }:
            raise VerificationError("predecessor inner identity mismatch")
        removed = identity.get("removed_non_active_payload", {})
        if removed != {
            "bytes": REMOVED_MYTH_BYTES,
            "embedded_in_successor": False,
            "filename": REMOVED_MYTH_FILENAME,
            "sha256": REMOVED_MYTH_SHA256,
        }:
            raise VerificationError("removed generic Myth identity mismatch")
        checks.append("DESCENDANT_BYTE_IDENTITY_27_OF_27_PASS")

        generic_ref = read_json(reader, "06_EXTERNAL_SIDECARS/GENERIC_MYTH_V0.2.0_REFERENCE.json")
        full_ref = read_json(reader, "06_EXTERNAL_SIDECARS/FULL_CANON_MYTH_V0.3.5_REFERENCE.json")
        validate_external_reference(generic_ref, GENERIC)
        validate_external_reference(full_ref, FULL_CANON)
        checks.append("OPTIONAL_EXTERNAL_SIDECAR_REFERENCES_PASS")

        historical = read_json(reader, "07_HISTORICAL/PRESERVED_AUGUST_14_R1_REFERENCE.json")
        expected_historical = {
            "archive_embedded": False,
            "bytes": OLD_OUTER_BYTES,
            "filename": OLD_OUTER_FILENAME,
            "preservation": "IMMUTABLE_HISTORICAL_RELEASE_EVIDENCE",
            "sha256": OLD_OUTER_SHA256,
            "superseded": True,
            "supersession_scope": "PACKAGING_BOUNDARY_ONLY",
            "tag": OLD_OUTER_TAG,
        }
        for key, expected in expected_historical.items():
            if historical.get(key) != expected:
                raise VerificationError(f"historical predecessor reference mismatch: {key}")
        checks.append("HISTORICAL_PREDECESSOR_REFERENCE_ONLY_PASS")

        capa = read_json(reader, "04_CORRECTION/CAPA_PS-R1-PRIVATE-MYTH-PUBLIC-BOUNDARY-001.json")
        if (
            capa.get("capa_id") != "PS-R1-PRIVATE-MYTH-PUBLIC-BOUNDARY-001"
            or capa.get("status") != "IMPLEMENTED_PENDING_EFFECTIVENESS"
            or capa.get("closure_state") != "NOT_CLOSED"
            or capa.get("historical_august_14_archive_mutated") is not False
        ):
            raise VerificationError("CAPA state is not implemented-pending-effectiveness/not-closed")
        checks.append("CAPA_IMPLEMENTED_PENDING_EFFECTIVENESS_PASS")

        slot = read_json(reader, "01_AUTHORITY/INNER_ADMISSION_SLOT.json")
        authority = slot.get("status")
        admission_path = "01_AUTHORITY/INNER_EXACT_HASH_MAINTAINER_ADMISSION.json"
        if slot.get("inner") != {
            "active_descendant_count": 27,
            "bytes": len(inner_data),
            "filename": INNER_FILENAME,
            "sha256": inner_hash,
        }:
            raise VerificationError("inner authority slot exact identity mismatch")
        if authority == "PENDING_EXACT_HASH_MAINTAINER_ADMISSION":
            if inventory_mode != "PENDING":
                raise VerificationError("pending authority slot disagrees with code-owned outer inventory")
            if slot.get("admission_record_embedded") is not False or admission_path in reader.files():
                raise VerificationError("pending inner authority slot unexpectedly embeds a record")
            expected_status = "NONPUBLISHABLE_PENDING_INNER_EXACT_HASH_ADMISSION"
            release_state = "PASS_NONPUBLISHABLE_PENDING_INNER_AUTHORITY"
        elif authority == "BOUND_EXACT_HASH_MAINTAINER_ADMISSION":
            if inventory_mode != "BOUND":
                raise VerificationError("bound authority slot disagrees with code-owned outer inventory")
            if slot.get("admission_record_embedded") is not True or admission_path not in reader.files():
                raise VerificationError("bound inner authority slot is missing its record")
            admission = reader.read(admission_path)
            if sha256_bytes(admission) != slot.get("admission_record_sha256"):
                raise VerificationError("inner admission record hash mismatch")
            validate_admission_record(admission, inner_hash, len(inner_data))
            expected_status = "AWAITING_EXTERNAL_EXACT_HASH_PUBLIC_RELEASE_AUTHORIZATION"
            release_state = "PASS_AWAITING_EXTERNAL_OUTER_AUTHORIZATION"
        else:
            raise VerificationError(f"unknown inner authority status: {authority!r}")
        status = read_json(reader, "02_STATUS/PUBLIC_REFERENCE_STATUS.json")
        if status.get("status") != expected_status or manifest.get("status") != expected_status:
            raise VerificationError("authority mode and package status disagree")
        if status.get("inner_authority_gate") != authority:
            raise VerificationError("status inner authority gate mismatch")
        outer_gate = status.get("outer_publication_gate", {})
        if outer_gate != {
            "authorization_is_external_to_archive": True,
            "publication_authorized": False,
            "status": "PENDING_EXACT_OUTER_ZIP_HASH_AUTHORIZATION_AFTER_BUILD",
        }:
            raise VerificationError("outer publication gate must remain external and pending")
        if any("OUTER" in PurePosixPath(path).name.upper() and "AUTHORIZATION" in PurePosixPath(path).name.upper() for path in reader.files()):
            raise VerificationError("outer exact-hash authorization must not be embedded")
        checks.append(f"AUTHORITY_BOUNDARY_PASS;INNER={authority};OUTER=PENDING_EXTERNAL")

        outer_semantic_members, outer_semantic_bytes = scan_outer_current_controls(reader)
        checks.append(
            "OUTER_CURRENT_CONTROL_SEMANTICS_PASS;"
            f"MEMBERS={outer_semantic_members};BYTES={outer_semantic_bytes}"
        )

        forbidden = {
            REMOVED_MYTH_SHA256,
            GENERIC["sha256"],
            FULL_CANON["sha256"],
            OLD_OUTER_SHA256,
        }
        scan_members = 0
        scan_bytes = 0
        budget = [0, 0]
        for path in sorted(reader.files()):
            payload = reader.read(path)
            digest = sha256_bytes(payload)
            if digest in forbidden:
                raise VerificationError(f"forbidden exact payload embedded as {path}")
            if path.lower().endswith(".zip"):
                count, size = recursive_forbidden_scan(payload, forbidden, path, budget=budget)
                scan_members += count
                scan_bytes += size
        checks.append(f"RECURSIVE_FORBIDDEN_PAYLOAD_SCAN_PASS;MEMBERS={scan_members};BYTES={scan_bytes}")

        safety = read_json(reader, "SAFETY_AND_SECRET_SCAN_REPORT.json")
        if safety.get("status") != "PASS" or safety.get("findings") != []:
            raise VerificationError("embedded safety report is not PASS with zero findings")
        checks.append("EMBEDDED_SAFETY_REPORT_PASS")

        return {
            "authority_state": authority,
            "checks": checks,
            "deterministic_zip_metadata_verified": reader.deterministic_metadata_verified,
            "integrity": "PASS",
            "outer_bytes": source.stat().st_size if source.is_file() else None,
            "outer_sha256": sha256_file(source) if source.is_file() else None,
            "release_state": release_state,
            "source": str(source),
            "status": "PASS",
            "tag": TAG,
        }
    finally:
        reader.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("package", help=f"{ROOT} directory or {ARCHIVE}")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        report = verify_package(Path(args.package).resolve())
    except (VerificationError, OSError, zipfile.BadZipFile, json.JSONDecodeError) as exc:
        report = {"status": "FAIL", "integrity": "FAIL", "error": str(exc)}
        print(json.dumps(report, indent=2, sort_keys=True))
        return 1
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
