#!/usr/bin/env python3
"""Fail-closed verifier for Generic Myth Sidecar v0.2.0.

The outer published SHA-256 remains the release identity. This verifier adds
defence in depth: an exact path inventory, strict checksum coverage, safe ZIP
metadata, pinned immutable content, semantic control validation, and scans for
the non-public predecessor or non-public classification language.
"""
from __future__ import annotations

import hashlib
import json
import re
import stat
import sys
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any

ROOT_NAME = (
    "Project_Shadow_Generic_Myth_Sidecar_v0.2.0_"
    "OPTIONAL_PUBLIC_COMPANION_2026-08-17"
)
FIXED_TIMESTAMP = (2026, 8, 17, 0, 0, 0)
OLD_PREDECESSOR_SHA256 = (
    "4d8481ed8f6af3e04d86a5c2de7e94aad47a591e1ce9c8757bbb4b0a397b90bb"
)
OLD_PREDECESSOR_SIZE_BYTES = 29763
APACHE_2_LICENSE_SHA256 = (
    "8c6db340475136df3c1201d458fa5755698eace76e510471ecc9d857d6083dac"
)
MAX_MEMBER_BYTES = 1_000_000
MAX_TOTAL_BYTES = 2_000_000

EXPECTED_PATHS = frozenset({
    "BUILD_RECEIPT.json",
    "CHANGELOG.md",
    "CONTROL_BOUNDARY.md",
    "LICENSE",
    "LICENSE-DOCS",
    "NEGATIVE_TEST_RESULTS.json",
    "NOTICE",
    "PACKAGE_INVENTORY.json",
    "PACKAGE_MANIFEST.json",
    "PREDECESSOR_CUSTODY.json",
    "README_FIRST.md",
    "RIGHTS_AND_PROVENANCE.md",
    "RIGHTS_SCAN_RESULT.json",
    "SHA256SUMS",
    "STATUS_AND_NONAUTHORITY.md",
    "TEST_RESULTS.json",
    "myth_sidecar.py",
    "tests/__init__.py",
    "tests/test_myth_sidecar.py",
    "tools/build_release.py",
    "tools/rights_scan.py",
    "tools/run_negative_verifier_tests.py",
    "tools/verify_package.py",
})

# Filled only for immutable, non-generated members. SHA256SUMS binds every
# member; these pins additionally prevent a resealed archive from substituting
# expected-path content. The verifier cannot self-pin, so its published outer
# archive hash remains the trust anchor.
PINNED_SHA256: dict[str, str] = {
    "CHANGELOG.md": "ccb0f4dfd526a3b2d1ce3cc52515b5611ba9b74573d5885e8f5db414b0a98b22",
    "CONTROL_BOUNDARY.md": "86094cf86808aa3f44aee39b6b8ab8a7e6797c47d7f03f468583f5a5487f355c",
    "LICENSE": "8c6db340475136df3c1201d458fa5755698eace76e510471ecc9d857d6083dac",
    "LICENSE-DOCS": "305d3725873a52f0620f4fcec8b2fa87798bcff22b05fdf94ab645037c164cc5",
    "NOTICE": "098f995db445de9c4f77ff7137ea6883239dc7bd1f76d4be7ee40280572934d5",
    "PACKAGE_INVENTORY.json": "c52c8796e03003a06389d34bd99e8840ff7f0b7fad8ed80ee648f8f86338f861",
    "PACKAGE_MANIFEST.json": "1bef9d75d5f4b3927f5b23bffd53f5aad6741c7b5dbc1ee4258b3ff95c524667",
    "PREDECESSOR_CUSTODY.json": "bc9a25ef3c2ba628bbdf5cdff1c159ac0d5e224629dfcfa1c1041914a1b83c2e",
    "README_FIRST.md": "442ea580d93978d0d7344e1031f52b9c6ed3a29c95fd1cc24f74cc8369059ed3",
    "RIGHTS_AND_PROVENANCE.md": "e35ff2a57c9c03e81751ae3b20b335722ca17a0108cad1cb145b83149288278a",
    "STATUS_AND_NONAUTHORITY.md": "ccd5e5b2e61164725da3ac9c7465ba7e558c3a4c45ac3eca8fc47fa924f62baf",
    "myth_sidecar.py": "eb7e9ce43394b2b624aaf3989935153ac6d1b7a71aa10f01e2f691fe8d0f6c8f",
    "tests/__init__.py": "01ba4719c80b6fe911b091a7c05124b64eeece964e09c058ef8f9805daca546b",
    "tests/test_myth_sidecar.py": "5cb0015d8305b312857f286eab27059922a6aa1b8f04c755056b8ef5ccb2f245",
    "tools/build_release.py": "14644f6a4a65d5552aa0bc4ff20257fe0ff3e2e07c23ecc59f4913343f9cc33f",
    "tools/rights_scan.py": "ee8b9675f3d20786f53baf59811cfd625baf820b51ea0cc28646b269738abe5b",
    "tools/run_negative_verifier_tests.py": "319902bb3f19641f0cebe3dcbf79b70e7c5088f7385831b73a2904a0b1b56691",
}

HISTORICAL_HASH_REFERENCE_PATHS = frozenset({
    "BUILD_RECEIPT.json",
    "PACKAGE_MANIFEST.json",
    "PREDECESSOR_CUSTODY.json",
    "RIGHTS_AND_PROVENANCE.md",
    "tools/build_release.py",
    "tools/verify_package.py",
})
CLASSIFICATION_SCAN_EXEMPT_PATHS = frozenset({
    # Verification tools contain the forbidden strings solely as negative-test
    # signatures. Their bytes are inventory-bound and pinned where self-
    # reference permits.
    "tools/run_negative_verifier_tests.py",
    "tools/verify_package.py",
})
CLASSIFICATION_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("PRIVATE", re.compile(r"\bprivate\b", re.IGNORECASE)),
    ("INTERNAL", re.compile(r"\binternal\b", re.IGNORECASE)),
    ("EXCLUDED", re.compile(r"\bexcluded\b", re.IGNORECASE)),
    (
        "PUBLIC_MANUFACTURE_FALSE",
        re.compile(
            r"(?:public[ _-]*manufactur(?:e|ing)|\"public_manufacture\")"
            r"\s*(?:[:=]|is)?\s*(?:false|no|0)",
            re.IGNORECASE,
        ),
    ),
)

EXPECTED_NEGATIVE_CASES = (
    "checksum_duplicate_entry",
    "extra_benign_resealed",
    "extra_classified_resealed",
    "license_marker_removed_resealed",
    "malformed_controls_resealed",
    "malformed_json_resealed",
    "old_predecessor_bytes_resealed",
    "rights_marker_removed_resealed",
    "zip_duplicate_path",
    "zip_symlink",
    "zip_traversal",
)

Finding = dict[str, object]


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def add(findings: list[Finding], code: str, path: str | None = None,
        detail: object | None = None) -> None:
    item: Finding = {"code": code}
    if path is not None:
        item["path"] = path
    if detail is not None:
        item["detail"] = detail
    findings.append(item)


def normalize(findings: list[Finding]) -> list[Finding]:
    unique = {
        json.dumps(item, sort_keys=True, separators=(",", ":")): item
        for item in findings
    }
    return [unique[key] for key in sorted(unique)]


def strict_json(raw: bytes, path: str, findings: list[Finding]) -> Any | None:
    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in items:
            if key in result:
                raise ValueError(f"duplicate key: {key}")
            result[key] = value
        return result

    def constant(value: str) -> None:
        raise ValueError(f"non-finite constant: {value}")

    try:
        text = raw.decode("utf-8")
        return json.loads(text, object_pairs_hook=pairs, parse_constant=constant)
    except (UnicodeError, ValueError, json.JSONDecodeError) as exc:
        add(findings, "JSON_INVALID", path, str(exc))
        return None


def parse_sums(raw: bytes, findings: list[Finding]) -> dict[str, str] | None:
    try:
        text = raw.decode("utf-8")
    except UnicodeError as exc:
        add(findings, "CHECKSUM_FILE_NOT_UTF8", "SHA256SUMS", str(exc))
        return None
    if not text.endswith("\n"):
        add(findings, "CHECKSUM_FILE_NO_FINAL_NEWLINE", "SHA256SUMS")
    output: dict[str, str] = {}
    previous = ""
    for number, line in enumerate(text.splitlines(), 1):
        match = re.fullmatch(r"([0-9a-f]{64})  (.+)", line)
        if match is None:
            add(findings, "CHECKSUM_LINE_MALFORMED", "SHA256SUMS", number)
            continue
        digest_value, name = match.groups()
        path = PurePosixPath(name)
        if (
            path.is_absolute()
            or ".." in path.parts
            or "." in path.parts
            or "\\" in name
            or "\x00" in name
            or name.startswith("/")
            or "//" in name
        ):
            add(findings, "CHECKSUM_PATH_UNSAFE", name, number)
            continue
        if name in output:
            add(findings, "CHECKSUM_PATH_DUPLICATE", name, number)
            continue
        if previous and name <= previous:
            add(findings, "CHECKSUM_PATH_NOT_STRICTLY_SORTED", name, number)
        previous = name
        output[name] = digest_value
    return output


def expect_equal(value: Any, expected: Any, path: str,
                 findings: list[Finding]) -> None:
    if type(value) is not type(expected) or value != expected:
        add(findings, "SEMANTIC_MISMATCH", path, {"expected": expected, "actual": value})


def require_markers(files: dict[str, bytes], path: str, markers: tuple[str, ...],
                    findings: list[Finding]) -> None:
    raw = files.get(path)
    if raw is None:
        return
    try:
        text = raw.decode("utf-8")
    except UnicodeError as exc:
        add(findings, "TEXT_NOT_UTF8", path, str(exc))
        return
    normalized = " ".join(text.split())
    for marker in markers:
        if " ".join(marker.split()) not in normalized:
            add(findings, "REQUIRED_MARKER_MISSING", path, marker)


def validate_inventory(files: dict[str, bytes], findings: list[Finding]) -> None:
    actual = set(files)
    for path in sorted(EXPECTED_PATHS - actual):
        add(findings, "INVENTORY_MISSING", path)
    for path in sorted(actual - EXPECTED_PATHS):
        add(findings, "INVENTORY_EXTRA", path)
    raw = files.get("PACKAGE_INVENTORY.json")
    if raw is None:
        return
    value = strict_json(raw, "PACKAGE_INVENTORY.json", findings)
    expected = {
        "authorizes": False,
        "path_count": len(EXPECTED_PATHS),
        "paths": sorted(EXPECTED_PATHS),
        "root_name": ROOT_NAME,
        "schema": "project-shadow.generic-myth-sidecar-path-inventory.v1",
    }
    if value is not None:
        expect_equal(value, expected, "PACKAGE_INVENTORY.json", findings)


def validate_checksums(files: dict[str, bytes], findings: list[Finding]) -> None:
    raw = files.get("SHA256SUMS")
    if raw is None:
        return
    listed = parse_sums(raw, findings)
    if listed is None:
        return
    actual_paths = set(files) - {"SHA256SUMS"}
    for path in sorted(actual_paths - set(listed)):
        add(findings, "CHECKSUM_ENTRY_MISSING", path)
    for path in sorted(set(listed) - actual_paths):
        add(findings, "CHECKSUM_ENTRY_EXTRA", path)
    for path in sorted(actual_paths & set(listed)):
        actual = sha(files[path])
        if listed[path] != actual:
            add(findings, "CHECKSUM_MISMATCH", path, {
                "expected": listed[path], "actual": actual,
            })


def validate_pins(files: dict[str, bytes], findings: list[Finding]) -> None:
    for path, expected in sorted(PINNED_SHA256.items()):
        raw = files.get(path)
        if raw is not None and sha(raw) != expected:
            add(findings, "PINNED_CONTENT_MISMATCH", path, {
                "expected": expected, "actual": sha(raw),
            })


def validate_semantics(files: dict[str, bytes], findings: list[Finding]) -> None:
    manifest = strict_json(files["PACKAGE_MANIFEST.json"], "PACKAGE_MANIFEST.json", findings) \
        if "PACKAGE_MANIFEST.json" in files else None
    expected_manifest = {
        "authority": {"action_authority": "NONE", "authorizes": False,
                      "exact_hash_admitted_into_r1": False, "production_authorized": False},
        "boundaries": {
            "changes_operational_result": False, "default_off": True,
            "feedback_allowed": False, "gate_input_eligible": False,
            "model_context_eligible": False, "operational_receipt_embedded": False,
            "production_deployment_eligible": False, "routing_input_eligible": False,
            "score_input_eligible": False, "terminal_only": True,
            "terminal_processing_states": ["NONACTION_COMPLETE", "SIMULATION_READY"],
            "tool_argument_eligible": False,
        },
        "component_id": "PROJECT_SHADOW_GENERIC_MYTH_SIDECAR",
        "distribution": {"canonical_r1_component": False,
                         "public_distribution_permitted_for_eligible_original_material": True,
                         "release_profile": "OPTIONAL_PUBLIC_COMPANION", "required_for_r1": False},
        "generic_registers": ["Caregiver", "Clockmaker", "Poet"],
        "predecessor": {
            "custody_identifier": "PROJECT_SHADOW_GENERIC_MYTH_SIDECAR_V0.1.1_HISTORICAL",
            "sha256": OLD_PREDECESSOR_SHA256,
            "status_not_inherited": "EARLIER_NONPUBLIC_STATUS_BOUNDARY", "version": "0.1.1",
        },
        "rights": {"code": "Apache-2.0", "documentation_and_data": "CC-BY-4.0",
                   "named_third_party_expressive_material_included": False},
        "schema": "project-shadow.generic-myth-sidecar-package-manifest.v2",
        "status": "OPTIONAL_PUBLIC_COMPANION_DEFAULT_OFF_TERMINAL_ONLY_NONAUTHORIZING",
        "tests": {"expected_unit_tests": 32, "status": "GENERATED_BY_DETERMINISTIC_BUILD"},
        "version": "0.2.0",
    }
    if manifest is not None:
        expect_equal(manifest, expected_manifest, "PACKAGE_MANIFEST.json", findings)
    custody = strict_json(files["PREDECESSOR_CUSTODY.json"], "PREDECESSOR_CUSTODY.json", findings) \
        if "PREDECESSOR_CUSTODY.json" in files else None
    expected_custody = {
        "changes_operational_authority": False,
        "predecessor_custody_identifier": "PROJECT_SHADOW_GENERIC_MYTH_SIDECAR_V0.1.1_HISTORICAL",
        "predecessor_sha256": OLD_PREDECESSOR_SHA256,
        "predecessor_size_bytes": OLD_PREDECESSOR_SIZE_BYTES,
        "relationship": "LICENSED_SUCCESSOR_WITH_CORRECTED_PUBLIC_DISTRIBUTION_BOUNDARY",
        "schema": "project-shadow.generic-myth-sidecar-predecessor-custody.v1",
        "successor_version": "0.2.0",
    }
    if custody is not None:
        expect_equal(custody, expected_custody, "PREDECESSOR_CUSTODY.json", findings)
    test_result = strict_json(files["TEST_RESULTS.json"], "TEST_RESULTS.json", findings) \
        if "TEST_RESULTS.json" in files else None
    expected_test_result = {
        "authorizes": False, "default_off": True, "feedback_allowed": False,
        "production_deployment_eligible": False,
        "schema": "project-shadow.generic-myth-sidecar-test-result.v2",
        "status": "PASS", "terminal_only": True, "unit_tests": 32,
    }
    if test_result is not None:
        expect_equal(test_result, expected_test_result, "TEST_RESULTS.json", findings)
    build = strict_json(files["BUILD_RECEIPT.json"], "BUILD_RECEIPT.json", findings) \
        if "BUILD_RECEIPT.json" in files else None
    expected_build = {
        "archive_compression": "ZIP_STORED",
        "archive_timestamp": "2026-08-17T00:00:00Z_DECLARED_FIXED_FOR_REPRODUCIBILITY",
        "authorizes": False, "deterministic_sorted_paths": True,
        "expected_unit_tests": 32, "negative_verifier_tests": len(EXPECTED_NEGATIVE_CASES),
        "negative_verifier_tests_status": "PASS", "predecessor_sha256": OLD_PREDECESSOR_SHA256,
        "rights_scan_status": "PASS",
        "schema": "project-shadow.generic-myth-sidecar-build-receipt.v2",
        "status": "PASS", "unit_test_status": "PASS", "version": "0.2.0",
    }
    if build is not None:
        expect_equal(build, expected_build, "BUILD_RECEIPT.json", findings)
    rights = strict_json(files["RIGHTS_SCAN_RESULT.json"], "RIGHTS_SCAN_RESULT.json", findings) \
        if "RIGHTS_SCAN_RESULT.json" in files else None
    if rights is not None:
        expected_rights = {
            "authorizes": False, "binary_expressive_assets_found": 0, "files_scanned": 19,
            "findings": [], "named_third_party_material_claim": "NONE_INCLUDED_BY_PACKAGE_DESIGN",
            "schema": "project-shadow.generic-myth-rights-scan.v1", "status": "PASS",
        }
        expect_equal(rights, expected_rights, "RIGHTS_SCAN_RESULT.json", findings)
    negative = strict_json(files["NEGATIVE_TEST_RESULTS.json"], "NEGATIVE_TEST_RESULTS.json", findings) \
        if "NEGATIVE_TEST_RESULTS.json" in files else None
    if negative is not None:
        expected_negative = {
            "all_mutations_rejected": True, "authorizes": False, "baseline_status": "PASS",
            "cases": [{"case": name, "status": "REJECTED_AS_EXPECTED"}
                      for name in EXPECTED_NEGATIVE_CASES],
            "negative_cases": len(EXPECTED_NEGATIVE_CASES),
            "schema": "project-shadow.generic-myth-sidecar-negative-verifier-tests.v1",
            "status": "PASS",
        }
        expect_equal(negative, expected_negative, "NEGATIVE_TEST_RESULTS.json", findings)
    if "LICENSE" in files and sha(files["LICENSE"]) != APACHE_2_LICENSE_SHA256:
        add(findings, "LICENSE_HASH_MISMATCH", "LICENSE", {
            "expected": APACHE_2_LICENSE_SHA256, "actual": sha(files["LICENSE"]),
        })
    require_markers(files, "LICENSE-DOCS", (
        "Creative Commons Attribution 4.0 International (CC BY 4.0)",
        "applies only to eligible original material",
        "implies no endorsement, certification, production authorization, efficacy, or safety",
    ), findings)
    require_markers(files, "NOTICE", (
        "optional public companion",
        "default-off, terminal-only, nonauthorizing, no-feedback, outside canonical R1",
        "ineligible for production deployment", "supplies no certification",
    ), findings)
    require_markers(files, "RIGHTS_AND_PROVENANCE.md", (
        "Apache License 2.0", "Creative Commons Attribution 4.0 International",
        "generic original registers only", "retained as historical custody evidence",
        "earlier non-public status metadata is not carried forward",
    ), findings)
    require_markers(files, "CONTROL_BOUNDARY.md", (
        "Default off; explicit opt-in is required.",
        "Terminal only: `SIMULATION_READY` or `NONACTION_COMPLETE`.",
        "Nonauthorizing: `authorizes=false`, `action_authority=NONE`.",
        "No feedback to the operational result or Project Shadow runtime.",
        "No production deployment eligibility.",
    ), findings)
    require_markers(files, "STATUS_AND_NONAUTHORITY.md", (
        "optional\nstandalone Project Shadow companion",
        "does not make it part\nof canonical R1",
        "supplies no\nauthority, evidence, approval, instruction, capability, or permission to act",
    ), findings)


def validate_content_scans(files: dict[str, bytes], findings: list[Finding]) -> None:
    for path, raw in sorted(files.items()):
        if path == "SHA256SUMS":
            continue
        digest = sha(raw)
        if digest == OLD_PREDECESSOR_SHA256:
            add(findings, "OLD_PREDECESSOR_ARCHIVE_PRESENT", path, {
                "sha256": digest, "size_bytes": len(raw),
            })
        if (OLD_PREDECESSOR_SHA256.encode("ascii") in raw
                and path not in HISTORICAL_HASH_REFERENCE_PATHS):
            add(findings, "OLD_HASH_REFERENCE_OUTSIDE_EXEMPTION", path)
        if path in CLASSIFICATION_SCAN_EXEMPT_PATHS:
            continue
        try:
            text = raw.decode("utf-8")
        except UnicodeError as exc:
            add(findings, "CONTENT_NOT_UTF8", path, str(exc))
            continue
        for label, pattern in CLASSIFICATION_PATTERNS:
            if pattern.search(text):
                add(findings, "NONPUBLIC_CLASSIFICATION_TOKEN", path, label)


def validate_payload(files: dict[str, bytes], findings: list[Finding]) -> list[Finding]:
    validate_inventory(files, findings)
    validate_checksums(files, findings)
    validate_pins(files, findings)
    validate_semantics(files, findings)
    validate_content_scans(files, findings)
    return normalize(findings)


def read_tree(root: Path, findings: list[Finding]) -> dict[str, bytes]:
    files: dict[str, bytes] = {}
    if root.name != ROOT_NAME:
        add(findings, "ROOT_NAME_MISMATCH", root.name, ROOT_NAME)
    try:
        entries = sorted(root.rglob("*"), key=lambda item: item.relative_to(root).as_posix())
    except OSError as exc:
        add(findings, "TREE_ENUMERATION_ERROR", str(root), str(exc))
        return files
    for entry in entries:
        relative = entry.relative_to(root).as_posix()
        try:
            mode = entry.lstat().st_mode
        except OSError as exc:
            add(findings, "TREE_LSTAT_ERROR", relative, str(exc))
            continue
        if stat.S_ISLNK(mode):
            add(findings, "TREE_SYMLINK", relative)
            continue
        if stat.S_ISDIR(mode):
            continue
        if not stat.S_ISREG(mode):
            add(findings, "TREE_NONREGULAR_MEMBER", relative, oct(mode))
            continue
        size = entry.stat().st_size
        if size > MAX_MEMBER_BYTES:
            add(findings, "TREE_MEMBER_TOO_LARGE", relative, size)
            continue
        try:
            files[relative] = entry.read_bytes()
        except OSError as exc:
            add(findings, "TREE_READ_ERROR", relative, str(exc))
    total = sum(map(len, files.values()))
    if total > MAX_TOTAL_BYTES:
        add(findings, "TREE_TOTAL_TOO_LARGE", detail=total)
    return files


def verify_tree(root: Path) -> list[Finding]:
    findings: list[Finding] = []
    files = read_tree(root, findings)
    return validate_payload(files, findings)


def safe_zip_relative(name: str, findings: list[Finding]) -> str | None:
    if "\x00" in name:
        add(findings, "ZIP_PATH_NUL", name)
        return None
    if "\\" in name:
        add(findings, "ZIP_PATH_BACKSLASH", name)
        return None
    if name.startswith("/") or name.endswith("/") or "//" in name:
        add(findings, "ZIP_PATH_NONCANONICAL", name)
        return None
    parts = name.split("/")
    if any(part in {"", ".", ".."} for part in parts):
        add(findings, "ZIP_PATH_TRAVERSAL", name)
        return None
    if not parts or parts[0] != ROOT_NAME or len(parts) < 2:
        add(findings, "ZIP_ROOT_MISMATCH", name, ROOT_NAME)
        return None
    relative = "/".join(parts[1:])
    path = PurePosixPath(relative)
    if path.is_absolute() or path.as_posix() != relative:
        add(findings, "ZIP_PATH_NONCANONICAL", name)
        return None
    return relative


def verify_zip(path: Path) -> list[Finding]:
    findings: list[Finding] = []
    files: dict[str, bytes] = {}
    seen_raw: set[str] = set()
    seen_relative: set[str] = set()
    total = 0
    try:
        with zipfile.ZipFile(path) as archive:
            if archive.comment:
                add(findings, "ZIP_ARCHIVE_COMMENT_PRESENT")
            infos = archive.infolist()
            if not infos:
                add(findings, "ZIP_EMPTY")
            for info in infos:
                name = info.filename
                if name in seen_raw:
                    add(findings, "ZIP_DUPLICATE_RAW_PATH", name)
                seen_raw.add(name)
                relative = safe_zip_relative(name, findings)
                if relative is None:
                    continue
                if relative in seen_relative:
                    add(findings, "ZIP_DUPLICATE_NORMALIZED_PATH", relative)
                    continue
                seen_relative.add(relative)
                mode = info.external_attr >> 16
                kind = stat.S_IFMT(mode)
                if kind == stat.S_IFLNK:
                    add(findings, "ZIP_SYMLINK", relative)
                    continue
                if kind != stat.S_IFREG:
                    add(findings, "ZIP_NONREGULAR_MEMBER", relative, oct(mode))
                    continue
                expected_permissions = 0o755 if relative.endswith(".py") else 0o644
                if stat.S_IMODE(mode) != expected_permissions:
                    add(findings, "ZIP_MODE_MISMATCH", relative, {
                        "expected": oct(expected_permissions),
                        "actual": oct(stat.S_IMODE(mode)),
                    })
                if info.create_system != 3:
                    add(findings, "ZIP_CREATE_SYSTEM_MISMATCH", relative, info.create_system)
                if info.date_time != FIXED_TIMESTAMP:
                    add(findings, "ZIP_TIMESTAMP_MISMATCH", relative, list(info.date_time))
                if info.compress_type != zipfile.ZIP_STORED:
                    add(findings, "ZIP_COMPRESSION_MISMATCH", relative, info.compress_type)
                if info.flag_bits & 0x1:
                    add(findings, "ZIP_ENCRYPTED_MEMBER", relative)
                if info.extra:
                    add(findings, "ZIP_MEMBER_EXTRA_FIELD", relative)
                if info.comment:
                    add(findings, "ZIP_MEMBER_COMMENT_PRESENT", relative)
                if info.file_size > MAX_MEMBER_BYTES:
                    add(findings, "ZIP_MEMBER_TOO_LARGE", relative, info.file_size)
                    continue
                total += info.file_size
                if total > MAX_TOTAL_BYTES:
                    add(findings, "ZIP_TOTAL_TOO_LARGE", detail=total)
                    continue
                try:
                    files[relative] = archive.read(info)
                except (OSError, RuntimeError, zipfile.BadZipFile) as exc:
                    add(findings, "ZIP_MEMBER_READ_ERROR", relative, str(exc))
    except (OSError, zipfile.BadZipFile) as exc:
        add(findings, "ZIP_OPEN_ERROR", str(path), f"{type(exc).__name__}:{exc}")
        return normalize(findings)
    return validate_payload(files, findings)


def main() -> int:
    path = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    findings = verify_tree(path) if path.is_dir() else verify_zip(path)
    result = {
        "schema": "project-shadow.package-verification.v3",
        "status": "PASS" if not findings else "FAIL",
        "findings": findings,
        "inventory_path_count": len(EXPECTED_PATHS),
        "old_predecessor_embedded": any(
            item.get("code") == "OLD_PREDECESSOR_ARCHIVE_PRESENT" for item in findings
        ),
        "authorizes": False,
    }
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0 if not findings else 1


if __name__ == "__main__":
    raise SystemExit(main())
