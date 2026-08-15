#!/usr/bin/env python3
"""Read-only CI verification for the Project Shadow public evidence surface.

This tool validates evidence already present in the repository and, with
``--online``, redownloads the exact public assets and checks public links.  It
has no publication, release-editing, tagging, or repository-write capability.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path, PurePosixPath
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
PUBLICATION_MANIFEST = ROOT / "PUBLICATION_MANIFEST.json"
PUBLIC_STATUS = ROOT / "PUBLIC_RELEASE_STATUS_2026-08-14.json"
AUTHORIZATION = ROOT / "governance" / "RELEASE_AUTHORIZATION_2026-08-14.json"
PUBLIC_REDOWNLOAD = (
    ROOT / "governance" / "PUBLIC_REDOWNLOAD_VERIFICATION_2026-08-15.json"
)
POST_PUBLICATION_ATTESTATION = (
    ROOT / "governance" / "POST_PUBLICATION_ATTESTATION_2026-08-15.json"
)
SIDECAR_REFERENCE = (
    ROOT / "governance" / "PROJECT_SHADOW_SANITIZED_MYTH_V0.3.4_REFERENCE.json"
)
R1_PACKAGE_MANIFEST = ROOT / "governance" / "R1_PACKAGE_MANIFEST.json"
R1_RELEASE_GATES = (
    ROOT / "governance" / "PROJECT_SHADOW_RELEASE_GATES_2026-08-14.json"
)
SIGNATURE_RECEIPT = (
    ROOT
    / "governance"
    / "PROJECT_SHADOW_SIGNATURE_INDEPENDENT_VERIFICATION_RECEIPT_2026-08-14.json"
)
SIGNATURE_BUNDLE = (
    ROOT
    / "governance"
    / "PROJECT_SHADOW_FABLE7_SCOPED_MAINTAINER_ADMISSION_RECORD_2026-08-12.json.sigstore.json"
)
VERIFICATION_GUIDE = ROOT / "docs" / "VERIFY_RELEASES.md"
CONTINUITY_POLICY = ROOT / "governance" / "MAINTAINER_CONTINUITY.md"
SHA256SUMS = ROOT / "SHA256SUMS"
HISTORICAL_PUBLIC_COMMIT = "93bde4f2fd4b7b8824622150a03a14cbf5b4b30e"
REKOR_LOG_INDEX = "2465982078"
REKOR_ENTRY_UUID = (
    "108e9186e8c5677a5ce4e9ea6d6aaf7b7a6aabe12b6a3f0d9202da3ede22684"
    "c3c90780f2f313a79"
)
REKOR_LOOKUP_URL = f"https://search.sigstore.dev/?logIndex={REKOR_LOG_INDEX}"
COSIGN_SHA256 = "4629c757b7618056f8ddd7e2625ae9fdd94c0372a65049520bc7d9df9efc7f71"
TRUSTED_ROOT_SHA256 = "6494e21ea73fa7ee769f85f57d5a3e6a08725eae1e38c755fc3517c9e6bc0b66"
AUTHORIZATION_RECEIPT_URL = (
    "https://github.com/PauseBeforeHarmProtocol/Project-Shadow/blob/"
    f"{HISTORICAL_PUBLIC_COMMIT}/governance/RELEASE_AUTHORIZATION_2026-08-14.md"
)
AUTHORIZATION_JSON_URL = (
    "https://github.com/PauseBeforeHarmProtocol/Project-Shadow/blob/"
    f"{HISTORICAL_PUBLIC_COMMIT}/governance/RELEASE_AUTHORIZATION_2026-08-14.json"
)
RELEASE_NOTES = {
    "myth-v0.3.4": ROOT / "release-notes" / "MYTH_SIDECAR_v0.3.4.md",
    "r1-2026-08-14": ROOT / "release-notes" / "PROJECT_SHADOW_R1_2026-08-14.md",
}
AUTHORIZATION_KEYS = {
    "OPTIONAL_EXTERNAL_RESEARCH_SIDECAR": "optional_external_myth_sidecar_v0_3_4",
    "R1_REFERENCE": "r1_reference",
}
PUBLIC_SITE_URLS = (
    "https://projectshadow.frylock117.chatgpt.site",
    "https://pausebeforeharm.frylock117.chatgpt.site",
    "https://civicqa.frylock117.chatgpt.site",
    "https://americanrepairmanual.frylock117.chatgpt.site",
    "https://therecord.frylock117.chatgpt.site",
    "https://almsivi.frylock117.chatgpt.site",
)
USER_AGENT = "Project-Shadow-read-only-evidence-verifier/1.0"
MAX_LINK_RESPONSE_BYTES = 2 * 1024 * 1024

BOOLEAN_CLAIM_KEYS = (
    "deployment_authorized",
    "operational_deployment_authorized",
    "production_authorized",
    "efficacy_claimed",
    "safety_claimed",
    "certification_claimed",
    "legal_compliance_claimed",
)
REQUIRED_NONCLAIM_KEYS = (
    "operational_deployment_authorized",
    "production_authorized",
    "efficacy_claimed",
    "safety_claimed",
    "certification_claimed",
    "legal_compliance_claimed",
)
POSITIVE_CLAIM_PATTERNS = (
    re.compile(r"\bproduction[- ]ready\b", re.IGNORECASE),
    re.compile(r"\bproduction[- ]grade\b", re.IGNORECASE),
    re.compile(r"\b(?:is|are|was|were)\s+production\s+software\b", re.IGNORECASE),
    re.compile(
        r"\b(?:authorized|approved|cleared)\s+(?:for\s+)?"
        r"(?:production|operational deployment)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:proven|guaranteed|certified|validated)\s+(?:to be\s+)?safe\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:proven|guaranteed|validated)\s+(?:to be\s+)?"
        r"(?:effective|efficacious)\b",
        re.IGNORECASE,
    ),
    re.compile(r"\b(?:is|are|was|were)\s+(?:safe|effective|efficacious)\b", re.IGNORECASE),
    re.compile(r"\bsafe\s+for\s+(?:production|operational deployment)\b", re.IGNORECASE),
    re.compile(
        r"\bmeets?\s+(?:all\s+)?(?:safety|efficacy|certification|legal compliance)\s+"
        r"(?:requirements?|standards?)\b",
        re.IGNORECASE,
    ),
    re.compile(r"\b(?:is|are|was|were)\s+(?:officially\s+)?certified\b", re.IGNORECASE),
    re.compile(
        r"\b(?:legally " r"compliant|complies with all (?:applicable )?laws|"
        r"legal compliance (?:is )?(?:certified|guaranteed))\b",
        re.IGNORECASE,
    ),
)
NEGATION_MARKERS = (
    "not ",
    "no ",
    "never ",
    "without ",
    "does not ",
    "do not ",
    "must not ",
    "isn't ",
    "aren't ",
    "ineligible for ",
)


class EvidenceError(RuntimeError):
    pass


class RejectRedirects(urllib.request.HTTPRedirectHandler):
    """Keep the read-only GitHub API token on its exact request origin."""

    def redirect_request(self, req: Any, fp: Any, code: int, msg: str, headers: Any, newurl: str) -> None:
        return None


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise EvidenceError(f"invalid JSON: {path.relative_to(ROOT)}: {exc}") from exc


def require_object(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise EvidenceError(f"{label} must be a JSON object")
    return value


def worktree_files() -> list[Path]:
    try:
        completed = subprocess.run(
            [
                "git",
                "ls-files",
                "-z",
                "--cached",
                "--others",
                "--exclude-standard",
            ],
            cwd=ROOT,
            check=True,
            stdout=subprocess.PIPE,
        )
    except (OSError, subprocess.CalledProcessError):
        return sorted(path for path in ROOT.rglob("*") if path.is_file() and ".git" not in path.parts)
    return [ROOT / raw.decode("utf-8") for raw in completed.stdout.split(b"\0") if raw]


def parse_all_json() -> int:
    json_paths = sorted(path for path in worktree_files() if path.suffix.lower() == ".json")
    if not json_paths:
        raise EvidenceError("repository contains no JSON evidence")
    for path in json_paths:
        load_json(path)
    return len(json_paths)


def parse_sha256sums(path: Path) -> dict[str, str]:
    rows: dict[str, str] = {}
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError) as exc:
        raise EvidenceError(f"could not read SHA256SUMS: {exc}") from exc
    for number, line in enumerate(lines, 1):
        if not line:
            continue
        match = re.fullmatch(r"([0-9a-f]{64})  (.+)", line)
        if match is None:
            raise EvidenceError(f"malformed SHA256SUMS line {number}")
        digest, filename = match.groups()
        if (
            filename in rows
            or PurePosixPath(filename).name != filename
            or filename in ("", ".", "..")
        ):
            raise EvidenceError(f"unsafe or duplicate SHA256SUMS filename: {filename!r}")
        rows[filename] = digest
    return rows


def release_rows(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    rows = manifest.get("releases")
    if not isinstance(rows, list) or not rows:
        raise EvidenceError("PUBLICATION_MANIFEST.json has no release rows")
    if not all(isinstance(row, dict) for row in rows):
        raise EvidenceError("PUBLICATION_MANIFEST.json contains an invalid release row")
    typed_rows = list(rows)
    orders = [row.get("order") for row in typed_rows]
    if orders != list(range(1, len(typed_rows) + 1)):
        raise EvidenceError("release order must be consecutive and already sorted")
    tags = [row.get("tag") for row in typed_rows]
    if len(tags) != len(set(tags)) or any(not isinstance(tag, str) for tag in tags):
        raise EvidenceError("release tags must be unique strings")
    return typed_rows


def validate_asset_row(row: dict[str, Any], repository: str) -> dict[str, Any]:
    asset = row.get("asset")
    if not isinstance(asset, dict):
        raise EvidenceError(f"release {row.get('tag')!r} has no asset object")
    filename = asset.get("filename")
    digest = asset.get("sha256")
    size = asset.get("bytes")
    url = asset.get("download_url")
    if not isinstance(filename, str) or PurePosixPath(filename).name != filename:
        raise EvidenceError(f"release {row.get('tag')!r} has an unsafe asset filename")
    if not isinstance(digest, str) or re.fullmatch(r"[0-9a-f]{64}", digest) is None:
        raise EvidenceError(f"release {row.get('tag')!r} has an invalid SHA-256")
    if not isinstance(size, int) or isinstance(size, bool) or size <= 0:
        raise EvidenceError(f"release {row.get('tag')!r} has an invalid byte count")
    expected_url = (
        f"https://github.com/{repository}/releases/download/"
        f"{urllib.parse.quote(str(row.get('tag')), safe='')}/"
        f"{urllib.parse.quote(filename, safe='._-')}"
    )
    if url != expected_url:
        raise EvidenceError(
            f"release {row.get('tag')!r} download URL mismatch: {url!r}"
        )
    return asset


def check_nonclaims(label: str, nonclaims: Any) -> None:
    if not isinstance(nonclaims, dict):
        raise EvidenceError(f"{label} has no nonclaims object")
    for key in REQUIRED_NONCLAIM_KEYS:
        if nonclaims.get(key) is not False:
            raise EvidenceError(f"{label} must explicitly set nonclaim false: {key}")
    if "deployment_authorized" in nonclaims and nonclaims["deployment_authorized"] is not False:
        raise EvidenceError(f"{label} nonclaim must be false: deployment_authorized")


def validate_resolved_publication_state(
    rows: list[dict[str, Any]],
    authorization: dict[str, Any],
    gates: dict[str, Any],
) -> None:
    """Cross-check the derived publication truth against its source records."""
    status = require_object(load_json(PUBLIC_STATUS), PUBLIC_STATUS.name)
    redownload = require_object(load_json(PUBLIC_REDOWNLOAD), PUBLIC_REDOWNLOAD.name)
    attestation = require_object(
        load_json(POST_PUBLICATION_ATTESTATION),
        POST_PUBLICATION_ATTESTATION.name,
    )

    if status.get("schema") != "project-shadow.public-release-status.v1":
        raise EvidenceError("unsupported derived public-release status schema")
    if status.get("derived_record") is not True:
        raise EvidenceError("public-release status is not marked as derived")
    if status.get("release_identity") != "PROJECT SHADOW 1.0 / R1 REFERENCE / BETA-ACTIVE-TESTING / PRELIVE":
        raise EvidenceError("derived public-release identity mismatch")
    check_nonclaims("derived public-release status", status.get("nonclaims"))
    if {
        key: status["nonclaims"].get(key) for key in REQUIRED_NONCLAIM_KEYS
    } != {
        key: authorization["nonclaims"].get(key) for key in REQUIRED_NONCLAIM_KEYS
    }:
        raise EvidenceError("derived nonclaims do not match the authorization receipt")
    if status.get("nonclaims", {}).get("source") != {
        "path": "governance/RELEASE_AUTHORIZATION_2026-08-14.json",
        "json_pointer": "/nonclaims",
    }:
        raise EvidenceError("derived nonclaim source pointer is invalid")

    source_gate = gates.get("post_build_publication_gate")
    derived_gate = status.get("candidate_internal_publication_gate")
    if not isinstance(source_gate, dict) or not isinstance(derived_gate, dict):
        raise EvidenceError("candidate or derived publication gate is missing")
    if (
        source_gate.get("satisfied") is not False
        or source_gate.get("external_to_candidate") is not True
        or derived_gate.get("satisfied_inside_candidate") is not False
        or derived_gate.get("external_to_candidate") is not True
        or derived_gate.get("open_by_design") is not True
        or derived_gate.get("preserved_without_modification") is not True
        or derived_gate.get("id") != source_gate.get("id")
        or derived_gate.get("source") != {
            "path": "governance/PROJECT_SHADOW_RELEASE_GATES_2026-08-14.json",
            "json_pointer": "/post_build_publication_gate",
        }
    ):
        raise EvidenceError("derived status rewrites or misstates the preserved candidate gate")

    derived_authorization = status.get("separate_human_authorization")
    if not isinstance(derived_authorization, dict) or (
        derived_authorization.get("present") is not True
        or derived_authorization.get("status") != authorization.get("status")
        or derived_authorization.get("source") != {
            "path": "governance/RELEASE_AUTHORIZATION_2026-08-14.json",
            "json_pointer": "/status",
        }
    ):
        raise EvidenceError("derived status misstates the separate human authorization")
    resolution = status.get("resolution")
    if not isinstance(resolution, dict) or (
        resolution.get("exact_public_artifacts_published") is not True
        or resolution.get("publication_status") != "PUBLISHED"
    ):
        raise EvidenceError("derived status does not record the resolved publication state")
    required_resolution_sources = {
        "governance/PROJECT_SHADOW_RELEASE_GATES_2026-08-14.json",
        "governance/RELEASE_AUTHORIZATION_2026-08-14.json",
        "PUBLICATION_MANIFEST.json",
        "SHA256SUMS",
        "governance/PUBLIC_REDOWNLOAD_VERIFICATION_2026-08-15.json",
    }
    if set(resolution.get("source_records", [])) != required_resolution_sources:
        raise EvidenceError("derived publication source-record set is invalid")

    if redownload.get("schema") != "project-shadow.public-redownload-verification.v1":
        raise EvidenceError("unsupported public-redownload receipt schema")
    if redownload.get("status") != "VERIFIED":
        raise EvidenceError("public-redownload receipt is not VERIFIED")
    method = redownload.get("method")
    if not isinstance(method, dict) or (
        method.get("anonymous_download") is not True
        or method.get("followed_redirects") is not True
        or method.get("hash_algorithm") != "SHA-256"
        or method.get("transport") != "HTTPS"
    ):
        raise EvidenceError("public-redownload receipt method is incomplete")
    check_nonclaims("public-redownload receipt", redownload.get("nonclaims"))

    redownload_rows = redownload.get("artifacts")
    status_rows = status.get("public_artifacts")
    if not isinstance(redownload_rows, list) or not isinstance(status_rows, list):
        raise EvidenceError("derived status or redownload receipt has no artifact rows")
    redownload_by_filename = {
        row.get("filename"): row for row in redownload_rows if isinstance(row, dict)
    }
    status_by_role = {
        row.get("role"): row for row in status_rows if isinstance(row, dict)
    }
    if len(redownload_by_filename) != len(rows) or len(status_by_role) != len(rows):
        raise EvidenceError("derived status/redownload artifact coverage mismatch")

    for row in rows:
        role = row["role"]
        asset = row["asset"]
        resolved = status_by_role.get(role)
        observed = redownload_by_filename.get(asset["filename"])
        if not isinstance(resolved, dict) or not isinstance(observed, dict):
            raise EvidenceError(f"missing resolved/redownload artifact row for {role}")
        expected_resolved = {
            "filename": asset["filename"],
            "bytes": asset["bytes"],
            "sha256": asset["sha256"],
            "download_url": asset["download_url"],
            "tag": row["tag"],
            "canonical_r1": row["canonical_r1"],
        }
        if any(resolved.get(key) != value for key, value in expected_resolved.items()):
            raise EvidenceError(f"derived artifact identity mismatch for {role}")
        if resolved.get("published") is not True or resolved.get("public_redownload_identity_verified") is not True:
            raise EvidenceError(f"derived publication/redownload state is not complete for {role}")
        manifest_index = rows.index(row)
        redownload_index = redownload_rows.index(observed)
        if resolved.get("source") != {
            "path": "PUBLICATION_MANIFEST.json",
            "json_pointer": f"/releases/{manifest_index}",
        }:
            raise EvidenceError(f"derived manifest source pointer mismatch for {role}")
        if resolved.get("redownload_verification_source") != {
            "path": "governance/PUBLIC_REDOWNLOAD_VERIFICATION_2026-08-15.json",
            "json_pointer": f"/artifacts/{redownload_index}",
        }:
            raise EvidenceError(f"derived redownload source pointer mismatch for {role}")
        expected_observed = {
            "bytes_expected": asset["bytes"],
            "bytes_observed": asset["bytes"],
            "sha256_expected": asset["sha256"],
            "sha256_observed": asset["sha256"],
            "canonical_download_url": asset["download_url"],
            "identity_verified": True,
            "http_status": 200,
        }
        if any(observed.get(key) != value for key, value in expected_observed.items()):
            raise EvidenceError(f"public-redownload identity mismatch for {role}")

    if attestation.get("schema") != "project-shadow.post-publication-attestation.v1":
        raise EvidenceError("unsupported post-publication attestation schema")
    if attestation.get("status") != "ATTESTED":
        raise EvidenceError("post-publication attestation is not ATTESTED")
    check_nonclaims("post-publication attestation", attestation.get("nonclaims"))
    historical = attestation.get("historical_publication_state")
    if not isinstance(historical, dict) or (
        historical.get("original_public_repository_commit") != HISTORICAL_PUBLIC_COMMIT
        or historical.get("original_public_repository_commit_signature_status") != "UNSIGNED_HISTORICAL_FACT"
        or historical.get("original_public_repository_commit_rewritten") is not False
        or historical.get("released_tags_rewritten") is not False
        or historical.get("released_artifacts_replaced_or_renamed") is not False
    ):
        raise EvidenceError("post-publication attestation misstates historical custody")
    binding = attestation.get("signature_binding")
    if not isinstance(binding, dict) or (
        binding.get("method") != "GITHUB_VERIFIED_SIGNATURE_ON_INTRODUCING_MAIN_COMMIT"
        or binding.get("status") != "BOUND_WHEN_INTRODUCING_MAIN_COMMIT_IS_VERIFIED"
    ):
        raise EvidenceError("post-publication attestation signature binding is invalid")
    required_attestation_sources = {
        "PUBLIC_RELEASE_STATUS_2026-08-14.json",
        "PUBLICATION_MANIFEST.json",
        "governance/RELEASE_AUTHORIZATION_2026-08-14.json",
        "governance/PUBLIC_REDOWNLOAD_VERIFICATION_2026-08-15.json",
    }
    if set(attestation.get("resolved_state_sources", [])) != required_attestation_sources:
        raise EvidenceError("post-publication attestation source-record set is invalid")
    attested_rows = attestation.get("published_artifacts")
    if not isinstance(attested_rows, list) or len(attested_rows) != len(rows):
        raise EvidenceError("post-publication attestation artifact coverage mismatch")
    for order, (manifest_row, attested) in enumerate(zip(rows, attested_rows), 1):
        if not isinstance(attested, dict):
            raise EvidenceError("post-publication attestation contains an invalid artifact row")
        asset = manifest_row["asset"]
        if (
            attested.get("publication_order") != order
            or attested.get("tag") != manifest_row["tag"]
            or attested.get("filename") != asset["filename"]
            or attested.get("bytes") != asset["bytes"]
            or attested.get("sha256") != asset["sha256"]
            or attested.get("asset_download_url") != asset["download_url"]
            or attested.get("tag_object_type") != "LIGHTWEIGHT_TAG_REF"
            or attested.get("tag_signature_status") != "UNSIGNED_HISTORICAL_FACT"
            or attested.get("tag_target_commit") != HISTORICAL_PUBLIC_COMMIT
        ):
            raise EvidenceError(f"post-publication attestation mismatch at order {order}")


def require_document_markers(label: str, path: Path, markers: Iterable[str]) -> str:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise EvidenceError(f"could not read {label}: {exc}") from exc
    for marker in markers:
        if marker not in text:
            raise EvidenceError(f"required custody marker missing from {label}: {marker!r}")
    return text


def validate_public_documentation() -> None:
    """Keep the published verification and continuity instructions fail-closed."""
    bundle = require_object(load_json(SIGNATURE_BUNDLE), SIGNATURE_BUNDLE.name)
    material = bundle.get("verificationMaterial")
    entries = material.get("tlogEntries") if isinstance(material, dict) else None
    if not isinstance(entries, list) or len(entries) != 1 or not isinstance(entries[0], dict):
        raise EvidenceError("Sigstore bundle must contain exactly one Rekor entry")
    if str(entries[0].get("logIndex")) != REKOR_LOG_INDEX:
        raise EvidenceError("documented Rekor log index does not match the preserved bundle")

    cryptographic_markers = (
        REKOR_LOG_INDEX,
        REKOR_ENTRY_UUID,
        REKOR_LOOKUP_URL,
        "cosign verify-blob",
        "--trusted-root",
        "--use-signed-timestamps",
        COSIGN_SHA256,
        TRUSTED_ROOT_SHA256,
        "pausebeforeharmprotocol_PBHP@protonmail.com",
        "https://github.com/login/oauth",
        "raw command does not",
    )
    require_document_markers(
        "verification guide",
        VERIFICATION_GUIDE,
        cryptographic_markers,
    )
    require_document_markers(
        "R1 release notes",
        RELEASE_NOTES["r1-2026-08-14"],
        cryptographic_markers
        + (AUTHORIZATION_RECEIPT_URL, AUTHORIZATION_JSON_URL),
    )
    require_document_markers(
        "Myth release notes",
        RELEASE_NOTES["myth-v0.3.4"],
        (
            "Myth v0.3.3",
            "ACKNOWLEDGE_ONLY",
            "separate, later human exact-hash decision",
            AUTHORIZATION_RECEIPT_URL,
            AUTHORIZATION_JSON_URL,
        ),
    )

    require_document_markers(
        "maintainer continuity policy",
        CONTINUITY_POLICY,
        (
            "Phillip Linstrum is the sole current human authority",
            "No co-maintainer, alternate release authority, or successor is designated",
            "AI systems, CI jobs",
            "may not authorize publication",
            "2026-10-13",
            "Staleness is a fail-closed continuity state",
        ),
    )
    require_document_markers(
        "repository README",
        ROOT / "README.md",
        ("governance/MAINTAINER_CONTINUITY.md",),
    )
    require_document_markers(
        "governance README",
        ROOT / "governance" / "README.md",
        ("MAINTAINER_CONTINUITY.md",),
    )


def verify_repository_metadata() -> list[dict[str, Any]]:
    manifest = require_object(load_json(PUBLICATION_MANIFEST), "PUBLICATION_MANIFEST.json")
    authorization = require_object(load_json(AUTHORIZATION), AUTHORIZATION.name)
    sidecar_reference = require_object(load_json(SIDECAR_REFERENCE), SIDECAR_REFERENCE.name)
    r1_manifest = require_object(load_json(R1_PACKAGE_MANIFEST), R1_PACKAGE_MANIFEST.name)
    gates = require_object(load_json(R1_RELEASE_GATES), R1_RELEASE_GATES.name)
    signature_receipt = require_object(load_json(SIGNATURE_RECEIPT), SIGNATURE_RECEIPT.name)
    sums = parse_sha256sums(SHA256SUMS)

    if manifest.get("schema") != "project-shadow.publication-manifest.v1":
        raise EvidenceError("unsupported publication manifest schema")
    repository = manifest.get("repository")
    if repository != "PauseBeforeHarmProtocol/Project-Shadow":
        raise EvidenceError("unexpected repository identity")
    check_nonclaims("publication manifest", manifest.get("nonclaims"))

    if authorization.get("schema") != "project-shadow.public-release-authorization-receipt.v1":
        raise EvidenceError("unsupported release-authorization schema")
    if authorization.get("status") != "AUTHORIZED_FOR_PUBLIC_RELEASE":
        raise EvidenceError("separate human release authorization is not present")
    if authorization.get("cryptographic_signature_claimed_for_this_receipt") is not False:
        raise EvidenceError("authorization receipt overstates its cryptographic status")
    check_nonclaims("release authorization", authorization.get("nonclaims"))
    authorized_artifacts = authorization.get("artifacts")
    if not isinstance(authorized_artifacts, dict):
        raise EvidenceError("release authorization has no artifacts object")

    rows = release_rows(manifest)
    expected_sums: dict[str, str] = {}
    canonical_rows = [row for row in rows if row.get("canonical_r1") is True]
    if len(canonical_rows) != 1 or canonical_rows[0].get("role") != "R1_REFERENCE":
        raise EvidenceError("publication manifest must identify exactly one canonical R1")
    if rows[-1] is not canonical_rows[0]:
        raise EvidenceError("canonical R1 must remain last in publication order")

    for row in rows:
        tag = row.get("tag")
        role = row.get("role")
        if tag not in RELEASE_NOTES:
            raise EvidenceError(f"no pinned release-notes file for tag {tag!r}")
        if role not in AUTHORIZATION_KEYS:
            raise EvidenceError(f"unknown release role: {role!r}")
        asset = validate_asset_row(row, repository)
        expected_sums[asset["filename"]] = asset["sha256"]
        authorization_row = authorized_artifacts.get(AUTHORIZATION_KEYS[role])
        if not isinstance(authorization_row, dict):
            raise EvidenceError(f"authorization has no artifact row for {role}")
        for key in ("filename", "bytes", "sha256"):
            if authorization_row.get(key) != asset[key]:
                raise EvidenceError(f"authorization mismatch for {role}: {key}")
        if authorization_row.get("publication_authorized") is not True:
            raise EvidenceError(f"exact human publication authorization absent for {role}")

        note = RELEASE_NOTES[tag].read_text(encoding="utf-8")
        for expected in (
            str(tag),
            asset["filename"],
            asset["sha256"],
            f"{asset['bytes']:,}",
        ):
            if expected not in note:
                raise EvidenceError(f"release notes for {tag} omit {expected!r}")
        if not note.lstrip().startswith("**"):
            raise EvidenceError(f"release notes for {tag} lack a bold first-line warning")
        if "automatically generated" not in note or "Source code (zip)" not in note:
            raise EvidenceError(f"release notes for {tag} omit the source-archive warning")
        if re.search(
            r"publish this release after|mark it as the latest release|publish this sidecar first",
            note,
            re.IGNORECASE,
        ):
            raise EvidenceError(f"release notes for {tag} retain a completed operator instruction")

    if sums != expected_sums:
        raise EvidenceError(
            f"SHA256SUMS/release-manifest mismatch: expected={expected_sums}; found={sums}"
        )

    sidecar_rows = [
        row for row in rows if row.get("role") == "OPTIONAL_EXTERNAL_RESEARCH_SIDECAR"
    ]
    if len(sidecar_rows) != 1:
        raise EvidenceError("publication manifest must identify exactly one Myth sidecar")
    sidecar_row = sidecar_rows[0]
    sidecar_asset = sidecar_row["asset"]
    if (
        sidecar_row.get("canonical_r1") is not False
        or sidecar_row.get("enabled_by_default") is not False
        or sidecar_reference.get("embedded") is not False
        or sidecar_reference.get("canonical_r1") is not False
        or sidecar_reference.get("enabled_by_default") is not False
        or sidecar_reference.get("publication_authorized_by_this_candidate") is not False
    ):
        raise EvidenceError("Myth sidecar external/default-off/nonauthorizing boundary failed")
    for key in ("filename", "bytes", "sha256"):
        if sidecar_reference.get(key) != sidecar_asset[key]:
            raise EvidenceError(f"external Myth reference mismatch: {key}")
    for key in (
        "outer_custody_container_embedded",
        "raw_private_report_embedded",
        "historical_myth_v0_3_3_embedded",
        "sanitized_myth_successor_embedded",
        "publication_authorized",
    ):
        if r1_manifest.get(key) is not False:
            raise EvidenceError(f"preserved R1 package boundary failed: {key}")
    publication_gate = gates.get("post_build_publication_gate")
    if not isinstance(publication_gate, dict):
        raise EvidenceError("preserved R1 has no post-build publication gate")
    if (
        publication_gate.get("satisfied") is not False
        or publication_gate.get("external_to_candidate") is not True
    ):
        raise EvidenceError("preserved candidate publication gate was rewritten")
    governance_effect = signature_receipt.get("governance_effect")
    if not isinstance(governance_effect, dict) or governance_effect.get("public_release_authorized") is not False:
        raise EvidenceError("signature receipt must remain nonauthorizing")
    validate_resolved_publication_state(rows, authorization, gates)
    validate_public_documentation()
    return rows


def line_is_negated(line: str, start: int) -> bool:
    prefix = line[max(0, start - 64):start].lower()
    boundary = max(prefix.rfind(mark) for mark in (".", ";", ":"))
    local_prefix = prefix[boundary + 1:]
    return any(marker in local_prefix for marker in NEGATION_MARKERS)


def prohibited_claim_findings(paths: Iterable[Path] | None = None) -> list[str]:
    findings: list[str] = []
    candidates = paths if paths is not None else worktree_files()
    for path in sorted(candidates):
        if path.suffix.lower() not in {
            ".cff", ".cfg", ".conf", ".html", ".json", ".md", ".py",
            ".toml", ".txt", ".xml", ".yaml", ".yml",
        }:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            raise EvidenceError(f"could not scan {path.relative_to(ROOT)}: {exc}") from exc
        relative = path.relative_to(ROOT).as_posix() if path.is_relative_to(ROOT) else str(path)
        for number, line in enumerate(text.splitlines(), 1):
            # The single explicit marker is reserved for a mutation fixture that
            # proves a forbidden boolean is rejected. It is line-scoped rather
            # than a blanket path exemption.
            if (
                relative == "tests/test_verify_repository_evidence.py"
                and "# permitted-claim-mutation-fixture" in line
            ):
                continue
            for key in BOOLEAN_CLAIM_KEYS:
                if re.search(
                    rf'"{re.escape(key)}"\s*:\s*true\b',
                    line,
                    re.IGNORECASE,
                ):
                    findings.append(f"{relative}:{number}: {key}=true")
            for pattern in POSITIVE_CLAIM_PATTERNS:
                for match in pattern.finditer(line):
                    if not line_is_negated(line, match.start()):
                        findings.append(
                            f"{relative}:{number}: unsupported claim: {match.group(0)!r}"
                        )
    return findings


def request(url: str) -> Any:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != "https" or not parsed.netloc:
        raise EvidenceError(f"refusing non-HTTPS URL: {url}")
    headers = {"User-Agent": USER_AGENT}
    if parsed.netloc == "api.github.com":
        headers["Accept"] = "application/vnd.github+json"
        token = os.environ.get("GITHUB_TOKEN")
        if token:
            headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, headers=headers)
    try:
        if parsed.netloc == "api.github.com":
            response = urllib.request.build_opener(RejectRedirects).open(req, timeout=30)
        else:
            response = urllib.request.urlopen(req, timeout=30)
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise EvidenceError(f"URL check failed for {url}: {exc}") from exc
    final_url = response.geturl()
    final = urllib.parse.urlparse(final_url)
    if final.scheme != "https" or not final.netloc:
        response.close()
        raise EvidenceError(f"refusing non-HTTPS redirect for {url}: {final_url}")
    return response


def download_and_hash(asset: dict[str, Any], destination: Path) -> Path:
    destination.mkdir(parents=True, exist_ok=True)
    output = destination / asset["filename"]
    digest = hashlib.sha256()
    count = 0
    with request(asset["download_url"]) as response, output.open("wb") as handle:
        header = response.headers.get("Content-Length")
        if header is not None:
            try:
                advertised = int(header)
            except ValueError as exc:
                raise EvidenceError(f"invalid Content-Length for {asset['filename']}") from exc
            if advertised != asset["bytes"]:
                raise EvidenceError(
                    f"Content-Length mismatch for {asset['filename']}: "
                    f"expected {asset['bytes']}; found {advertised}"
                )
        while True:
            block = response.read(1024 * 1024)
            if not block:
                break
            count += len(block)
            if count > asset["bytes"]:
                raise EvidenceError(f"oversized release download: {asset['filename']}")
            digest.update(block)
            handle.write(block)
    if count != asset["bytes"] or digest.hexdigest() != asset["sha256"]:
        raise EvidenceError(
            f"release download identity mismatch for {asset['filename']}: "
            f"bytes={count}; sha256={digest.hexdigest()}"
        )
    return output


def check_link(url: str) -> None:
    with request(url) as response:
        status = getattr(response, "status", None)
        if status is not None and not 200 <= status < 400:
            raise EvidenceError(f"unexpected HTTP {status} for {url}")
        response.read(MAX_LINK_RESPONSE_BYTES + 1)


def fetch_public_json(url: str) -> dict[str, Any]:
    if urllib.parse.urlparse(url).netloc != "api.github.com":
        raise EvidenceError(f"refusing non-GitHub API JSON URL: {url}")
    with request(url) as response:
        body = response.read(MAX_LINK_RESPONSE_BYTES + 1)
    if len(body) > MAX_LINK_RESPONSE_BYTES:
        raise EvidenceError(f"GitHub API response exceeds bounded size: {url}")
    try:
        value = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise EvidenceError(f"invalid GitHub release API response: {url}: {exc}") from exc
    if not isinstance(value, dict):
        raise EvidenceError(f"GitHub release API response is not an object: {url}")
    return value


def normalize_release_body(value: str) -> str:
    return value.replace("\r\n", "\n").replace("\r", "\n").rstrip()


def verify_live_release_metadata(rows: list[dict[str, Any]]) -> None:
    repository = "PauseBeforeHarmProtocol/Project-Shadow"
    for row in rows:
        tag = row["tag"]
        release = fetch_public_json(
            f"https://api.github.com/repos/{repository}/releases/tags/{tag}"
        )
        note = RELEASE_NOTES[tag].read_text(encoding="utf-8")
        if (
            release.get("tag_name") != tag
            or release.get("name") != row.get("title")
            or release.get("draft") is not False
            or release.get("prerelease") is not False
            or not isinstance(release.get("body"), str)
            or normalize_release_body(release["body"]) != normalize_release_body(note)
        ):
            raise EvidenceError(f"live GitHub release metadata/body mismatch for {tag}")
        assets = release.get("assets")
        if not isinstance(assets, list):
            raise EvidenceError(f"live GitHub release has no asset list for {tag}")
        primary = [
            asset for asset in assets
            if isinstance(asset, dict) and asset.get("name") == row["asset"]["filename"]
        ]
        if len(primary) != 1:
            raise EvidenceError(f"live GitHub release primary-asset coverage mismatch for {tag}")
        live_asset = primary[0]
        expected_asset = row["asset"]
        if (
            live_asset.get("size") != expected_asset["bytes"]
            or live_asset.get("digest") != f"sha256:{expected_asset['sha256']}"
            or live_asset.get("browser_download_url") != expected_asset["download_url"]
        ):
            raise EvidenceError(f"live GitHub primary-asset identity mismatch for {tag}")

    latest = fetch_public_json(
        f"https://api.github.com/repos/{repository}/releases/latest"
    )
    if latest.get("tag_name") != rows[-1]["tag"] or rows[-1].get("canonical_r1") is not True:
        raise EvidenceError("canonical R1 is not the latest GitHub release")


def fetch_public_page(url: str) -> str:
    with request(url) as response:
        status = getattr(response, "status", None)
        if status is not None and not 200 <= status < 400:
            raise EvidenceError(f"unexpected HTTP {status} for {url}")
        body = response.read(MAX_LINK_RESPONSE_BYTES + 1)
    if len(body) > MAX_LINK_RESPONSE_BYTES:
        raise EvidenceError(f"public page exceeds bounded verification size: {url}")
    try:
        return body.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise EvidenceError(f"public page is not UTF-8: {url}") from exc


def verify_public_site_release_links(rows: list[dict[str, Any]]) -> None:
    canonical_release = "https://projectshadow.frylock117.chatgpt.site/release"
    for index, url in enumerate(PUBLIC_SITE_URLS):
        page = fetch_public_page(url)
        expected = 'href="/release"' if index == 0 else canonical_release
        if expected not in page:
            raise EvidenceError(f"public site omits canonical release link: {url}")

    release_page = fetch_public_page(canonical_release)
    for row in rows:
        asset = row["asset"]
        for expected in (asset["download_url"], asset["sha256"]):
            if expected not in release_page:
                raise EvidenceError(
                    f"canonical public release page omits {row['role']} identity: {expected}"
                )


def verify_online(rows: list[dict[str, Any]], destination: Path) -> None:
    downloaded: dict[str, Path] = {}
    repository = "PauseBeforeHarmProtocol/Project-Shadow"
    for row in rows:
        asset = row["asset"]
        downloaded[row["role"]] = download_and_hash(asset, destination)
        release_url = f"https://github.com/{repository}/releases/tag/{row['tag']}"
        check_link(release_url)
    verify_live_release_metadata(rows)
    verify_public_site_release_links(rows)

    r1 = downloaded.get("R1_REFERENCE")
    if r1 is None:
        raise EvidenceError("downloaded assets do not include canonical R1")
    completed = subprocess.run(
        [
            sys.executable,
            "-I",
            "-S",
            "-B",
            str(ROOT / "tools" / "verify_public_release.py"),
            str(r1),
        ],
        cwd=ROOT,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    if completed.returncode != 0:
        raise EvidenceError(
            "positive verification of the exact public R1 failed:\n" + completed.stdout
        )
    print(completed.stdout.rstrip())


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--online",
        action="store_true",
        help="redownload exact assets and check release/public-site URLs",
    )
    parser.add_argument(
        "--download-dir",
        type=Path,
        help="destination for online release downloads (required with --online)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.online != (args.download_dir is not None):
        print("FAIL: --online and --download-dir must be supplied together", file=sys.stderr)
        return 2
    try:
        json_count = parse_all_json()
        rows = verify_repository_metadata()
        findings = prohibited_claim_findings()
        if findings:
            raise EvidenceError(
                "unsupported production/safety/efficacy/certification/legal claims:\n  - "
                + "\n  - ".join(findings)
            )
        if args.online:
            verify_online(rows, args.download_dir.resolve())
    except EvidenceError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    print(f"PASS: parsed {json_count} repository JSON files")
    print("PASS: publication manifest, checksums, notes, and human authorization agree")
    print("PASS: derived publication status, redownload receipt, and attestation agree")
    print("PASS: Myth remains external, default-off, noncanonical, and nonauthorizing")
    print("PASS: preserved candidate and signature records remain non-self-authorizing")
    print("PASS: nonclaim scan")
    if args.online:
        print("PASS: exact public assets, release URLs, and six public-site release links")
    else:
        print("INFO: network verification skipped (use --online --download-dir DIR)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
