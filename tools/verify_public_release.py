#!/usr/bin/env python3
"""Verify a Project Shadow R1 public-release preview or candidate.

The verifier is read-only. It checks manifests, exact governed hashes,
signature and external-sidecar gates, archive safety, exclusions, and a
recursive high-confidence secret/reference scan. It never publishes.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import io
import json
import re
import stat
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any, Iterable


RELEASE_IDENTITY = "PROJECT SHADOW 1.0 / R1 REFERENCE / BETA-ACTIVE-TESTING / PRELIVE"
ADMISSION_SHA256 = "659d15bf371a1c2b8410d39c040733da43779fbe54730c43140e1d06dc70b424"
ADMISSION_BYTES = 217626
R1_SHA256 = "075b41ea4186b2d2edb0ed246ab7662cf8bbdf3160294e3eca176b9d0857b108"
R1_BYTES = 5442808
COMMONS_SHA256 = "1ffdba41025c0b81da92d0bbb22d0eaa69488cffbc80936365034669110448d7"
COMMONS_BYTES = 1935482
OUTER_SHA256 = "827c13e80f09e3e3065cee4aa0bcc6afbc3e27061b83b7597754b7ea167f68a2"
OLD_MYTH_SHA256 = "270bf07ca0db7c30c4ebcc05ca607bb242937b8879753f932aeaf62696bf0541"
SANITIZED_MYTH_SHA256 = "3c8c8c0d3d9582c76b685c1b685260cc8179478ab310037c858b46257aa314c7"
SANITIZED_MYTH_BYTES = 1418194
SANITIZED_MYTH_FILENAME = (
    "Project_Shadow_Full_Canon_Myth_Sidecar_v0.3.4_"
    "OPTIONAL_EXTERNAL_RESEARCH_2026-08-14.zip"
)
PRIVATE_REPORT_SHA256 = "ee229684a004af384421cf7467bc0d74ccf493aa1b6b75b239a955f1bdbe8b9f"
HISTORICAL_UNADMITTED_SHA256 = "debb5b494e8762df66c3a9803b44f4d7ac2e9335040771477963e73261703e92"
HISTORICAL_PREDECESSOR_SHA256 = "4f57944f021a64d235a3a8b95fe4d5f39212588c3b62ff46dfab6b483cfa1a85"
EXPECTED_BUNDLE_MEDIA_TYPE = "application/vnd.dev.sigstore.bundle.v0.3+json"
EXPECTED_BUNDLE_SHA256 = "a579f1b855ad22eb58be4ece5a580edbff60a171b35517b15ee172e417faaba0"
EXPECTED_BUNDLE_BYTES = 6770
EXPECTED_RECEIPT_SHA256 = "62e3965891b0f0a11aa46b50854f467acef84645faa569419fc79cf1051c1629"
EXPECTED_RECEIPT_BYTES = 1625
EXPECTED_SUCCESSOR_VERSION = "0.3.4"

ADMISSION_PATH = "01_AUTHORITY/PROJECT_SHADOW_FABLE7_SCOPED_MAINTAINER_ADMISSION_RECORD_2026-08-12.json"
R1_PATH = "05_COMPONENTS/R1/Project_Shadow_R1_BETA2_Runtime_Successor_Candidate_2026-08-10.zip"
COMMONS_PATH = "05_COMPONENTS/PRIMITIVE_COMMONS/Project_Shadow_PS-R1-PC-S1_v0.1.0-beta.5_POST_REAUDIT_CORRECTION_CANDIDATE_2026-08-10.zip"
STATUS_PATH = "02_STATUS/PROJECT_SHADOW_PUBLIC_RELEASE_CANDIDATE_STATUS.json"
GATES_PATH = "04_DISCLOSURES/PROJECT_SHADOW_RELEASE_GATES_2026-08-14.json"
SIDECAR_PATH = "07_EXTERNAL_SIDECAR/PROJECT_SHADOW_SANITIZED_MYTH_V0.3.4_REFERENCE.json"
BUNDLE_PATH = "06_SIGNATURE/ADMISSION_RECORD.sigstore.json"
RECEIPT_PATH = "06_SIGNATURE/SIGNATURE_VERIFICATION_RECEIPT.json"

COMMON_EXPECTED_PATHS = frozenset({
    "00_START_HERE.md",
    "01_AUTHORITY/ADMISSION_RECORD_SHA256.txt",
    ADMISSION_PATH,
    STATUS_PATH,
    "03_AUDIT/PROJECT_SHADOW_FABLE7_SANITIZED_AUDIT_DISPOSITION_2026-08-12.json",
    "03_AUDIT/PROJECT_SHADOW_FABLE7_SANITIZED_AUDIT_DISPOSITION_2026-08-12.md",
    "04_DISCLOSURES/ADMISSION_KNOWN_LIMITATIONS_AND_OPEN_GATES_2026-08-12.json",
    "04_DISCLOSURES/ADMISSION_KNOWN_LIMITATIONS_AND_OPEN_GATES_2026-08-12.md",
    GATES_PATH,
    R1_PATH,
    COMMONS_PATH,
    SIDECAR_PATH,
    "LICENSE",
    "LICENSE-DOCS",
    "NOTICE",
    "PACKAGE_MANIFEST.json",
    "RIGHTS_MANIFEST.json",
    "SAFETY_AND_SECRET_SCAN_REPORT.json",
    "SHA256SUMS",
    "tools/verify_public_release.py",
})
CANDIDATE_EXPECTED_PATHS = COMMON_EXPECTED_PATHS | {BUNDLE_PATH, RECEIPT_PATH}
PREVIEW_EXPECTED_PATHS = COMMON_EXPECTED_PATHS | {"06_SIGNATURE/SIGNATURE_GATE_PENDING.json"}

FORBIDDEN_PAYLOAD_HASHES = {
    OUTER_SHA256: "recognized custody payload",
    OLD_MYTH_SHA256: "historical mixed-rights sidecar payload",
    PRIVATE_REPORT_SHA256: "raw private audit payload",
    HISTORICAL_UNADMITTED_SHA256: "historical unadmitted payload",
    HISTORICAL_PREDECESSOR_SHA256: "historical predecessor payload",
    SANITIZED_MYTH_SHA256: "sanitized Myth v0.3.4 payload that must remain external",
}

TEXT_SUFFIXES = {
    "", ".c", ".cfg", ".conf", ".css", ".csv", ".go", ".h", ".html", ".in", ".ini",
    ".java", ".js", ".json", ".jsx", ".md", ".mjs", ".py", ".rs", ".sh",
    ".sql", ".toml", ".ts", ".tsx", ".txt", ".xml", ".yaml", ".yml",
}
FORBIDDEN_AUTHOR = bytes.fromhex("4861726c616e20456c6c69736f6e").decode("ascii")
FORBIDDEN_ENTITY = bytes.fromhex("414d").decode("ascii")
HIGH_CONFIDENCE_SECRET_PATTERNS = (
    ("private-key-pem", re.compile(rb"-----BEGIN (?:[A-Z0-9 ]+ )?PRIVATE KEY-----")),
    ("aws-access-key", re.compile(rb"(?<![A-Z0-9])(?:AKIA|ASIA)[A-Z0-9]{16}(?![A-Z0-9])")),
    ("github-token", re.compile(rb"(?<![A-Za-z0-9_])gh[pousr]_[A-Za-z0-9]{30,}(?![A-Za-z0-9_])")),
    ("slack-token", re.compile(rb"(?<![A-Za-z0-9])xox[baprs]-[A-Za-z0-9-]{20,}(?![A-Za-z0-9])")),
    ("stripe-live-secret", re.compile(rb"(?<![A-Za-z0-9_])sk_live_[A-Za-z0-9]{16,}(?![A-Za-z0-9_])")),
    ("npm-token", re.compile(rb"(?<![A-Za-z0-9_])npm_[A-Za-z0-9]{30,}(?![A-Za-z0-9_])")),
)
MAX_MEMBER_BYTES = 128 * 1024 * 1024
MAX_TOTAL_BYTES = 768 * 1024 * 1024
MAX_DEPTH = 8


class VerificationError(RuntimeError):
    pass


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_json(data: bytes, label: str) -> dict[str, Any]:
    try:
        value = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise VerificationError(f"invalid UTF-8 JSON for {label}: {exc}") from exc
    if not isinstance(value, dict):
        raise VerificationError(f"{label} must be a JSON object")
    return value


def safe_member_name(name: str) -> bool:
    if not name or "\\" in name or name.startswith("/") or re.match(r"^[A-Za-z]:", name):
        return False
    return all(part not in ("", ".", "..") for part in PurePosixPath(name).parts)


def validate_info(info: zipfile.ZipInfo, label: str) -> None:
    if not safe_member_name(info.filename):
        raise VerificationError(f"unsafe ZIP path in {label}: {info.filename!r}")
    mode = (info.external_attr >> 16) & 0xFFFF
    if stat.S_ISLNK(mode):
        raise VerificationError(f"symbolic link in {label}: {info.filename}")
    if info.file_size > MAX_MEMBER_BYTES:
        raise VerificationError(f"oversized ZIP member in {label}: {info.filename}")


def load_target(path: Path) -> dict[str, bytes]:
    if path.is_dir():
        files: dict[str, bytes] = {}
        for item in sorted(path.rglob("*")):
            if item.is_symlink():
                raise VerificationError(f"symbolic link is not allowed: {item}")
            if item.is_file():
                relative = item.relative_to(path).as_posix()
                if not safe_member_name(relative):
                    raise VerificationError(f"unsafe path: {relative}")
                files[relative] = item.read_bytes()
        return files
    if not path.is_file():
        raise VerificationError(f"target does not exist: {path}")
    try:
        with zipfile.ZipFile(path, "r") as archive:
            seen: set[str] = set()
            roots: set[str] = set()
            rows: list[tuple[zipfile.ZipInfo, PurePosixPath]] = []
            for info in archive.infolist():
                validate_info(info, path.name)
                normalized = str(PurePosixPath(info.filename))
                if normalized in seen:
                    raise VerificationError(f"duplicate ZIP member: {normalized}")
                seen.add(normalized)
                posix = PurePosixPath(normalized)
                roots.add(posix.parts[0])
                rows.append((info, posix))
            if len(roots) != 1:
                raise VerificationError("candidate ZIP must contain exactly one root directory")
            root = next(iter(roots))
            files = {}
            for info, posix in rows:
                if info.is_dir():
                    continue
                if len(posix.parts) < 2 or posix.parts[0] != root:
                    raise VerificationError("candidate ZIP member is outside its root directory")
                relative = PurePosixPath(*posix.parts[1:]).as_posix()
                files[relative] = archive.read(info)
            bad = archive.testzip()
            if bad is not None:
                raise VerificationError(f"candidate ZIP CRC failure: {bad}")
            return files
    except zipfile.BadZipFile as exc:
        raise VerificationError(f"target is not a valid ZIP: {exc}") from exc


def parse_sha256sums(data: bytes) -> dict[str, str]:
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise VerificationError("SHA256SUMS is not UTF-8") from exc
    rows: dict[str, str] = {}
    for number, line in enumerate(text.splitlines(), 1):
        match = re.fullmatch(r"([0-9a-f]{64})  (.+)", line)
        if match is None:
            raise VerificationError(f"malformed SHA256SUMS line {number}")
        digest, path = match.groups()
        if not safe_member_name(path) or path in rows:
            raise VerificationError(f"unsafe or duplicate SHA256SUMS path: {path}")
        rows[path] = digest
    return rows


def verify_controls(files: dict[str, bytes]) -> dict[str, Any]:
    if "PACKAGE_MANIFEST.json" not in files or "SHA256SUMS" not in files:
        raise VerificationError("PACKAGE_MANIFEST.json or SHA256SUMS is missing")
    sums = parse_sha256sums(files["SHA256SUMS"])
    expected_sums = set(files) - {"SHA256SUMS"}
    if set(sums) != expected_sums:
        missing = sorted(expected_sums - set(sums))
        extra = sorted(set(sums) - expected_sums)
        raise VerificationError(f"SHA256SUMS coverage mismatch; missing={missing}; extra={extra}")
    for path, expected in sums.items():
        actual = sha256_bytes(files[path])
        if actual != expected:
            raise VerificationError(f"checksum mismatch for {path}: expected {expected}; found {actual}")
    manifest = load_json(files["PACKAGE_MANIFEST.json"], "PACKAGE_MANIFEST.json")
    if manifest.get("schema") != "project-shadow.public-release-package-manifest.v1":
        raise VerificationError("unsupported package manifest schema")
    if manifest.get("release_identity") != RELEASE_IDENTITY:
        raise VerificationError("release identity mismatch")
    rows = manifest.get("files")
    if not isinstance(rows, list):
        raise VerificationError("manifest files array is missing")
    manifest_paths: set[str] = set()
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get("path"), str):
            raise VerificationError("invalid manifest file row")
        path = row["path"]
        if path in manifest_paths or path not in files:
            raise VerificationError(f"duplicate or missing manifest path: {path}")
        manifest_paths.add(path)
        if row.get("bytes") != len(files[path]) or row.get("sha256") != sha256_bytes(files[path]):
            raise VerificationError(f"manifest metadata mismatch: {path}")
    expected_manifest_paths = set(files) - {"PACKAGE_MANIFEST.json", "SHA256SUMS"}
    if manifest_paths != expected_manifest_paths:
        raise VerificationError("PACKAGE_MANIFEST file coverage mismatch")
    if manifest.get("file_count_excluding_controls") != len(rows):
        raise VerificationError("manifest file count mismatch")
    return manifest


def require_exact(files: dict[str, bytes], path: str, expected_sha: str, expected_bytes: int) -> None:
    if path not in files:
        raise VerificationError(f"required file is missing: {path}")
    data = files[path]
    if len(data) != expected_bytes or sha256_bytes(data) != expected_sha:
        raise VerificationError(f"exact governed identity mismatch: {path}")


def text_findings(path: str, data: bytes) -> Iterable[str]:
    if PurePosixPath(path).suffix.lower() not in TEXT_SUFFIXES:
        return
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        yield f"invalid UTF-8 in declared text file: {path}"
        return
    if re.search(re.escape(FORBIDDEN_AUTHOR), text, re.IGNORECASE):
        yield f"forbidden named-author reference: {path}"
    if re.search(rf"(?<![A-Za-z0-9_]){re.escape(FORBIDDEN_ENTITY)}(?![A-Za-z0-9_])", text):
        yield f"forbidden standalone fictional-entity reference: {path}"
    for kind, pattern in HIGH_CONFIDENCE_SECRET_PATTERNS:
        if pattern.search(data):
            yield f"possible secret ({kind}): {path}"


def recursive_scan(path: str, data: bytes, findings: list[str], budget: list[int], depth: int = 0) -> None:
    budget[0] += len(data)
    if budget[0] > MAX_TOTAL_BYTES:
        raise VerificationError("recursive scan byte budget exceeded")
    digest = sha256_bytes(data)
    if digest in FORBIDDEN_PAYLOAD_HASHES:
        findings.append(f"forbidden payload ({FORBIDDEN_PAYLOAD_HASHES[digest]}): {path}")
    findings.extend(text_findings(path, data) or ())
    declared_zip = path.lower().endswith(".zip")
    archive_content = zipfile.is_zipfile(io.BytesIO(data))
    if archive_content and not declared_zip:
        findings.append(f"ZIP content carried under a non-ZIP path: {path}")
    if depth >= MAX_DEPTH:
        if declared_zip or archive_content:
            findings.append(f"archive recursion depth limit reached: {path}")
        return
    if not (declared_zip or archive_content):
        return
    try:
        with zipfile.ZipFile(io.BytesIO(data), "r") as archive:
            seen: set[str] = set()
            for info in sorted(archive.infolist(), key=lambda item: item.filename):
                validate_info(info, path)
                normalized = str(PurePosixPath(info.filename))
                if normalized in seen:
                    raise VerificationError(f"duplicate nested ZIP member in {path}: {normalized}")
                seen.add(normalized)
                if not info.is_dir():
                    recursive_scan(f"{path}!/{normalized}", archive.read(info), findings, budget, depth + 1)
            bad = archive.testzip()
            if bad is not None:
                raise VerificationError(f"nested ZIP CRC failure in {path}: {bad}")
    except zipfile.BadZipFile as exc:
        findings.append(f"invalid nested ZIP: {path}: {exc}")


def verify_scan(files: dict[str, bytes]) -> int:
    findings: list[str] = []
    budget = [0]
    for path in sorted(files):
        recursive_scan(path, files[path], findings, budget)
    if findings:
        raise VerificationError("recursive safety/secret scan failed:\n  - " + "\n  - ".join(findings[:20]))
    return budget[0]


def verify_rights_and_boundaries(files: dict[str, bytes], manifest: dict[str, Any]) -> None:
    rights = load_json(files.get("RIGHTS_MANIFEST.json", b""), "RIGHTS_MANIFEST.json")
    if rights.get("whole_container_blanket_license") is not False:
        raise VerificationError("rights manifest creates or omits the no-blanket-license boundary")
    if rights.get("rights_expanded_by_packaging") is not False:
        raise VerificationError("rights manifest claims expanded rights")
    if rights.get("third_party_rights_or_endorsement_granted") is not False:
        raise VerificationError("rights manifest claims third-party rights or endorsement")
    external = rights.get("external_sanitized_myth_sidecar", {})
    if external.get("embedded") is not False or external.get("licensed_by_this_candidate") is not False:
        raise VerificationError("external sidecar rights boundary is invalid")
    if manifest.get("outer_custody_container_embedded") is not False:
        raise VerificationError("manifest says custody payload is embedded")
    if manifest.get("raw_private_report_embedded") is not False:
        raise VerificationError("manifest says raw private report is embedded")
    if manifest.get("historical_myth_v0_3_3_embedded") is not False:
        raise VerificationError("manifest says historical sidecar payload is embedded")
    if manifest.get("sanitized_myth_successor_embedded") is not False:
        raise VerificationError("manifest says sanitized successor is embedded")
    if manifest.get("publication_authorized") is not False:
        raise VerificationError("candidate must not self-authorize publication")


def verify_bundle_and_receipt(files: dict[str, bytes]) -> dict[str, Any]:
    if BUNDLE_PATH not in files or RECEIPT_PATH not in files:
        raise VerificationError("candidate signature bundle or verification receipt is missing")
    if len(files[BUNDLE_PATH]) != EXPECTED_BUNDLE_BYTES or sha256_bytes(files[BUNDLE_PATH]) != EXPECTED_BUNDLE_SHA256:
        raise VerificationError("candidate does not contain the exact independently verified Sigstore bundle")
    if len(files[RECEIPT_PATH]) != EXPECTED_RECEIPT_BYTES or sha256_bytes(files[RECEIPT_PATH]) != EXPECTED_RECEIPT_SHA256:
        raise VerificationError("candidate does not contain the exact independent verification receipt")
    bundle = load_json(files[BUNDLE_PATH], BUNDLE_PATH)
    if bundle.get("mediaType") != EXPECTED_BUNDLE_MEDIA_TYPE:
        raise VerificationError("unexpected Sigstore bundle media type")
    try:
        digest = base64.b64decode(bundle["messageSignature"]["messageDigest"]["digest"], validate=True).hex()
    except (KeyError, TypeError, ValueError) as exc:
        raise VerificationError("Sigstore bundle has no valid message digest") from exc
    if digest != ADMISSION_SHA256:
        raise VerificationError("Sigstore bundle signs the wrong digest")
    material = bundle.get("verificationMaterial", {})
    if not material.get("tlogEntries"):
        raise VerificationError("Sigstore bundle has no transparency-log entry")
    if not material.get("timestampVerificationData", {}).get("rfc3161Timestamps"):
        raise VerificationError("Sigstore bundle has no RFC3161 timestamp")
    receipt = load_json(files[RECEIPT_PATH], RECEIPT_PATH)
    if receipt.get("schema") != "project-shadow.sigstore-independent-verification-receipt.v1" or receipt.get("status") != "VERIFIED":
        raise VerificationError("independent signature receipt is not VERIFIED")
    if receipt.get("record", {}).get("sha256") != ADMISSION_SHA256:
        raise VerificationError("signature receipt targets the wrong record")
    if receipt.get("sigstore_bundle", {}).get("sha256") != sha256_bytes(files[BUNDLE_PATH]):
        raise VerificationError("signature receipt targets the wrong bundle")
    verification = receipt.get("verification", {})
    if verification.get("cosign_exit_code") != 0 or verification.get("cryptographic_signature_verified") is not True:
        raise VerificationError("signature receipt does not record cryptographic verification")
    if verification.get("transparency_log_verified") is not True:
        raise VerificationError("signature receipt does not record transparency-log verification")
    if verification.get("rfc3161_timestamp_verified") is not True:
        raise VerificationError("signature receipt does not record RFC3161 timestamp verification")
    trusted_root_sha256 = verification.get("trusted_root_sha256")
    if not isinstance(trusted_root_sha256, str) or re.fullmatch(r"[0-9a-f]{64}", trusted_root_sha256) is None:
        raise VerificationError("signature receipt has no valid trusted-root SHA-256")
    effect = receipt.get("governance_effect", {})
    if effect.get("signature_gate_satisfied") is not True or effect.get("external_time_anchor_gate_satisfied") is not True:
        raise VerificationError("signature receipt leaves a gate open")
    if effect.get("public_release_authorized") is not False:
        raise VerificationError("signature receipt must not self-authorize public release")
    return receipt


def verify_sidecar_reference(files: dict[str, bytes], candidate: bool) -> dict[str, Any]:
    if SIDECAR_PATH not in files:
        raise VerificationError("external sanitized sidecar reference is missing")
    reference = load_json(files[SIDECAR_PATH], SIDECAR_PATH)
    if reference.get("embedded") is not False or reference.get("canonical_r1") is not False:
        raise VerificationError("sidecar must remain external and noncanonical")
    if reference.get("enabled_by_default") is not False:
        raise VerificationError("sidecar must remain default-off")
    historical = reference.get("historical_v0_3_3", {})
    if historical.get("sha256") != OLD_MYTH_SHA256 or historical.get("bytes_embedded") is not False:
        raise VerificationError("historical sidecar exclusion boundary is invalid")
    reference_verified = reference.get("status") == "VERIFIED_EXTERNAL_REFERENCE"
    if candidate or reference_verified:
        if not reference_verified:
            raise VerificationError("candidate sidecar reference is not verified")
        if reference.get("filename") != SANITIZED_MYTH_FILENAME:
            raise VerificationError("sidecar reference does not name the exact pinned v0.3.4 artifact")
        if reference.get("version") != EXPECTED_SUCCESSOR_VERSION:
            raise VerificationError("candidate must reference sanitized sidecar version 0.3.4")
        digest = reference.get("sha256")
        if digest != SANITIZED_MYTH_SHA256:
            raise VerificationError("candidate does not reference the exact pinned sanitized successor hash")
        if reference.get("bytes") != SANITIZED_MYTH_BYTES:
            raise VerificationError("candidate does not reference the exact pinned sanitized successor byte count")
    else:
        if reference.get("status") != "PENDING_SANITIZED_SUCCESSOR_HASH":
            raise VerificationError("preview sidecar reference has an unsupported status")
        if any(reference.get(key) is not None for key in ("filename", "sha256", "bytes")):
            raise VerificationError("pending preview sidecar reference must not claim an artifact identity")
    return reference


def run_optional_cosign(files: dict[str, bytes], receipt: dict[str, Any], args: argparse.Namespace) -> None:
    provided = [
        args.cosign,
        args.expected_cosign_sha256,
        args.trusted_root,
        args.expected_trusted_root_sha256,
        args.certificate_identity,
        args.certificate_oidc_issuer,
    ]
    if not any(provided):
        return
    if not all(provided):
        raise VerificationError(
            "--cosign, --expected-cosign-sha256, --trusted-root, "
            "--expected-trusted-root-sha256, --certificate-identity, and "
            "--certificate-oidc-issuer must be supplied together"
        )
    cosign = Path(args.cosign)
    if not cosign.is_file():
        raise VerificationError(f"Cosign executable not found: {cosign}")
    expected_cosign_sha256 = args.expected_cosign_sha256.lower()
    if re.fullmatch(r"[0-9a-f]{64}", expected_cosign_sha256) is None:
        raise VerificationError("--expected-cosign-sha256 must be a SHA-256 hex string")
    if sha256_file(cosign) != expected_cosign_sha256:
        raise VerificationError("Cosign executable hash mismatch")
    trusted_root = Path(args.trusted_root)
    if not trusted_root.is_file():
        raise VerificationError(f"Sigstore trusted root not found: {trusted_root}")
    expected_trusted_root_sha256 = args.expected_trusted_root_sha256.lower()
    if re.fullmatch(r"[0-9a-f]{64}", expected_trusted_root_sha256) is None:
        raise VerificationError("--expected-trusted-root-sha256 must be a SHA-256 hex string")
    if sha256_file(trusted_root) != expected_trusted_root_sha256:
        raise VerificationError("Sigstore trusted-root hash mismatch")
    load_json(trusted_root.read_bytes(), "Sigstore trusted root")
    receipt_verification = receipt.get("verification", {})
    if receipt_verification.get("executable_sha256") != expected_cosign_sha256:
        raise VerificationError("live Cosign hash does not match the independent receipt")
    if receipt_verification.get("trusted_root_sha256") != expected_trusted_root_sha256:
        raise VerificationError("live trusted-root hash does not match the independent receipt")
    with tempfile.TemporaryDirectory(prefix="project-shadow-verify-") as temp:
        temp_path = Path(temp)
        record = temp_path / "admission.json"
        bundle = temp_path / "bundle.json"
        record.write_bytes(files[ADMISSION_PATH])
        bundle.write_bytes(files[BUNDLE_PATH])
        command = [
            str(cosign), "verify-blob", "--bundle", str(bundle),
            "--trusted-root", str(trusted_root),
            "--use-signed-timestamps",
            "--certificate-identity", args.certificate_identity,
            "--certificate-oidc-issuer", args.certificate_oidc_issuer,
            str(record),
        ]
        completed = subprocess.run(command, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if completed.returncode != 0:
            raise VerificationError(f"Cosign verification failed with exit code {completed.returncode}: {completed.stderr.strip()}")
        print("PASS: live Cosign identity/signature/RFC3161 verification")


def verify(path: Path, args: argparse.Namespace) -> tuple[str, int, bool]:
    files = load_target(path)
    manifest = verify_controls(files)
    require_exact(files, ADMISSION_PATH, ADMISSION_SHA256, ADMISSION_BYTES)
    require_exact(files, R1_PATH, R1_SHA256, R1_BYTES)
    require_exact(files, COMMONS_PATH, COMMONS_SHA256, COMMONS_BYTES)
    if manifest.get("admission_record_sha256") != ADMISSION_SHA256:
        raise VerificationError("manifest admission hash mismatch")
    if manifest.get("r1_sha256") != R1_SHA256 or manifest.get("primitive_commons_sha256") != COMMONS_SHA256:
        raise VerificationError("manifest component hash mismatch")
    verify_rights_and_boundaries(files, manifest)
    status = load_json(files.get(STATUS_PATH, b""), STATUS_PATH)
    gates = load_json(files.get(GATES_PATH, b""), GATES_PATH)
    if status.get("release_identity") != RELEASE_IDENTITY:
        raise VerificationError("status release identity mismatch")
    mode = status.get("build_mode")
    candidate = mode == "CANDIDATE"
    if mode not in ("PREVIEW", "CANDIDATE"):
        raise VerificationError(f"unknown build mode: {mode!r}")
    expected_paths = CANDIDATE_EXPECTED_PATHS if candidate else PREVIEW_EXPECTED_PATHS
    if set(files) != expected_paths:
        missing = sorted(expected_paths - set(files))
        unexpected = sorted(set(files) - expected_paths)
        raise VerificationError(f"fixed package-path allowlist mismatch; missing={missing}; unexpected={unexpected}")
    status_publication = status.get("publication_gate", {})
    if (
        status_publication.get("status") != "PENDING_EXACT_CANDIDATE_HASH_AUTHORIZATION"
        or status_publication.get("authorization_is_external_to_candidate") is not True
        or status_publication.get("publication_authorized") is not False
    ):
        raise VerificationError("status publication gate must remain pending, external, and unauthorized")
    nonclaims = status.get("nonclaims", {})
    for key in (
        "deployment_authorized",
        "production_authorized",
        "efficacy_claimed",
        "safety_claimed",
        "certification_claimed",
        "legal_compliance_claimed",
    ):
        if nonclaims.get(key) is not False:
            raise VerificationError(f"status nonclaim boundary is missing or true: {key}")
    sidecar_reference = verify_sidecar_reference(files, candidate)
    sidecar_verified = sidecar_reference.get("status") == "VERIFIED_EXTERNAL_REFERENCE"
    gate_rows = gates.get("candidate_build_gates")
    if not isinstance(gate_rows, list):
        raise VerificationError("candidate build gate rows are missing")
    gate_map = {
        row.get("id"): row.get("satisfied")
        for row in gate_rows
        if isinstance(row, dict)
    }
    if gate_map.get("VERIFIED_SIGSTORE_RECEIPT") is not candidate:
        raise VerificationError("Sigstore gate status is inconsistent with build mode")
    if gate_map.get("SANITIZED_MYTH_V0_3_4_EXACT_EXTERNAL_HASH") is not sidecar_verified:
        raise VerificationError("external sanitized sidecar gate status is inconsistent")
    if candidate:
        if gates.get("candidate_build_gate_satisfied") is not True:
            raise VerificationError("candidate build gates are not satisfied")
        receipt = verify_bundle_and_receipt(files)
        run_optional_cosign(files, receipt, args)
        if manifest.get("status") != "RELEASE_CANDIDATE_AWAITING_EXACT_HASH_AUTHORIZATION":
            raise VerificationError("candidate manifest status is invalid")
    else:
        if gates.get("candidate_build_gate_satisfied") is not False:
            raise VerificationError("preview unexpectedly claims closed candidate gates")
        if not args.allow_preview:
            raise VerificationError("target is a blocked preview; pass --allow-preview only for structural review")
        if manifest.get("status") != "BLOCKED_PREVIEW":
            raise VerificationError("preview manifest status is invalid")
    publication = gates.get("post_build_publication_gate", {})
    if publication.get("satisfied") is not False or publication.get("external_to_candidate") is not True:
        raise VerificationError("publication gate must remain open and external")
    if gates.get("deployment_authorized") is not False or gates.get("production_authorized") is not False:
        raise VerificationError("release gates must not authorize deployment or production")
    scanned = verify_scan(files)
    return mode, scanned, sidecar_verified


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("target", type=Path, help="extracted candidate root or candidate ZIP")
    parser.add_argument("--allow-preview", action="store_true", help="validate a deliberately blocked preview")
    parser.add_argument("--cosign", help="optional Cosign executable for live verification")
    parser.add_argument("--expected-cosign-sha256", help="expected SHA-256 of the optional Cosign executable")
    parser.add_argument("--trusted-root", help="Sigstore TrustedRoot JSON for live verification")
    parser.add_argument("--expected-trusted-root-sha256", help="expected SHA-256 of the Sigstore TrustedRoot JSON")
    parser.add_argument("--certificate-identity", help="exact expected certificate identity for live Cosign verification")
    parser.add_argument("--certificate-oidc-issuer", help="exact expected OIDC issuer for live Cosign verification")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        mode, scanned, sidecar_verified = verify(args.target.resolve(), args)
    except (VerificationError, OSError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    print("PASS: manifest and SHA256SUMS coverage")
    print("PASS: exact admission, R1, and Commons identities")
    print("PASS: exclusions, rights boundaries, archive safety, and recursive secret/reference scan")
    print(f"PASS: recursively scanned {scanned} uncompressed bytes")
    if mode == "PREVIEW":
        if sidecar_verified:
            print("PASS: sanitized Myth v0.3.4 exact hash is pinned externally; payload is not embedded")
            print("BLOCKED AS DESIGNED: verified Sigstore receipt remains open")
        else:
            print("BLOCKED AS DESIGNED: verified Sigstore receipt and sanitized Myth v0.3.4 exact external hash remain open")
    else:
        print("PASS: candidate-build gates")
        print("GATE OPEN AS DESIGNED: separate maintainer exact-candidate-hash publication authorization")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
