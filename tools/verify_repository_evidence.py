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
CURRENT_STATUS = ROOT / "PUBLIC_RELEASE_STATUS_2026-08-17.json"
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
FULL_CANON_V035_REFERENCE = (
    ROOT / "governance" / "PROJECT_SHADOW_MYTH_V0.3.5_PUBLIC_RELEASE_REFERENCE.json"
)
FULL_CANON_V035_PUBLICATION = (
    ROOT / "governance" / "MYTH_V0.3.5_PUBLICATION_RECORD_2026-08-17.json"
)
GENERIC_REFERENCE = (
    ROOT / "governance" / "PROJECT_SHADOW_GENERIC_MYTH_v0.2.0_PUBLIC_RELEASE_REFERENCE.json"
)
GENERIC_TEST_RECORD = (
    ROOT / "governance" / "GENERIC_MYTH_v0.2.0_BUILD_AND_TEST_REPORT_2026-08-17.json"
)
GENERIC_AUTHORIZATION = (
    ROOT
    / "governance"
    / "GENERIC_MYTH_v0.2.0_EXACT_HASH_PUBLIC_RELEASE_AUTHORIZATION_2026-08-17.json"
)
INNER_ADMISSION = (
    ROOT / "governance" / "R1_0_1_INNER_EXACT_HASH_ADMISSION_2026-08-17.json"
)
OUTER_AUTHORIZATION = (
    ROOT / "governance" / "R1_0_1_OUTER_RELEASE_AUTHORIZATION_2026-08-17.json"
)
CAPA_RECORD = (
    ROOT / "governance" / "CAPA_PS-R1-PRIVATE-MYTH-PUBLIC-BOUNDARY-001_2026-08-17.json"
)
CURRENT_REDOWNLOAD = (
    ROOT / "governance" / "R1_0_1_PUBLIC_REDOWNLOAD_VERIFICATION_2026-08-17.json"
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
    "myth-v0.3.5": ROOT / "release-notes" / "MYTH_SIDECAR_v0.3.5.md",
    "generic-myth-v0.2.0": ROOT / "release-notes" / "GENERIC_MYTH_SIDECAR_v0.2.0.md",
    "r1.0.1-2026-08-17": ROOT / "release-notes" / "PROJECT_SHADOW_R1_0_1_2026-08-17.md",
}
AUTHORIZATION_KEYS = {
    "OPTIONAL_EXTERNAL_RESEARCH_SIDECAR": "optional_external_myth_sidecar_v0_3_4",
    "R1_REFERENCE": "r1_reference",
}
PUBLISHED_STATES = {
    "PUBLISHED",
    "PUBLISHED_HISTORICAL",
    "PUBLISHED_HISTORICAL_SUPERSEDED",
}
PENDING_IDENTITY_TOKENS = {
    "generic_bytes": "<" "GENERIC_BYTES" ">",
    "generic_sha256": "<" "GENERIC_SHA256" ">",
    "inner_bytes": "<" "INNER_BYTES" ">",
    "inner_sha256": "<" "INNER_SHA256" ">",
    "outer_bytes": "<" "OUTER_BYTES" ">",
    "outer_sha256": "<" "OUTER_SHA256" ">",
}
GENERIC_FINAL = {
    "filename": "Project_Shadow_Generic_Myth_Sidecar_v0.2.0_OPTIONAL_PUBLIC_COMPANION_2026-08-17.zip",
    "bytes": 93_676,
    "sha256": "6e7a362d4135f9d626dcfef463bfb1f7166226b3cf8a4c02a953ab39af1538bf",
}
INNER_FINAL = {
    "filename": "Project_Shadow_R1.0.1_Runtime_Family_Myth_Decoupled_2026-08-17.zip",
    "bytes": 5_463_189,
    "sha256": "c8c32b12432c954b1a6f852c0c9f81bbbd40167e936be057d4c3de1a0aa3a623",
}
OUTER_FINAL = {
    "filename": "Project_Shadow_R1.0.1_Public_Reference_2026-08-17.zip",
    "bytes": 5_731_663,
    "sha256": "6f6f1e16d5e9a20e62403f14af7ce8629ce2d702528fb7f80aaf4a14deb7a1d1",
}
GATE_1_CONFIRMED_BY = "Phillip Linstrum"
GATE_1_CONFIRMED_AT = "2026-08-18T00:09:39Z"
GENERIC_AUTHORIZATION_STATEMENT = (
    "I authorize this exact Generic Myth Sidecar v0.2.0—93,676 bytes, SHA-256 "
    "6e7a362d4135f9d626dcfef463bfb1f7166226b3cf8a4c02a953ab39af1538bf—for "
    "public release on GitHub and Hugging Face as a separate optional, default-off, "
    "terminal-only, nonauthorizing companion."
)
INNER_ADMISSION_STATEMENT = (
    "I admit the exact Myth-free R1.0.1 inner family—5,463,189 bytes, SHA-256 "
    "c8c32b12432c954b1a6f852c0c9f81bbbd40167e936be057d4c3de1a0aa3a623—for "
    "R1.0.1 reference packaging. Its 27 active descendants are byte-identical to the "
    "August 14 predecessor, no Myth payload is embedded, and this admission does not "
    "authorize production, deployment, or publication."
)
OUTER_AUTHORIZATION_CONFIRMED_AT = "2026-08-18T01:35:04Z"
OUTER_AUTHORIZATION_STATEMENT = (
    "I authorize Project_Shadow_R1.0.1_Public_Reference_2026-08-17.zip—5,731,663 "
    "bytes, SHA-256 6f6f1e16d5e9a20e62403f14af7ce8629ce2d702528fb7f80aaf4a14deb7a1d1, "
    "tag r1.0.1-2026-08-17—for public release on GitHub and Hugging Face. I also "
    "authorize the verified GitHub repository update and corresponding updates and "
    "deployments across all six GPT Sites. This does not authorize production or "
    "operational deployment."
)
RELEASE_PLACEHOLDER_RE = re.compile(
    r"<(?:GENERIC|INNER|OUTER)_[A-Z0-9_]+>"
)
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
            stderr=subprocess.DEVNULL,
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
    if "identity_placeholders" in asset:
        raise EvidenceError(
            f"concrete release {row.get('tag')!r} retains identity_placeholders"
        )
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


def validate_pending_asset_row(
    row: dict[str, Any],
    repository: str,
    *,
    expected_bytes_token: str,
    expected_sha256_token: str,
) -> dict[str, Any]:
    """Validate an explicit fail-closed prepublication identity placeholder."""
    asset = row.get("asset")
    if not isinstance(asset, dict):
        raise EvidenceError(f"pending release {row.get('tag')!r} has no asset object")
    filename = asset.get("filename")
    url = asset.get("download_url")
    if not isinstance(filename, str) or PurePosixPath(filename).name != filename:
        raise EvidenceError(f"pending release {row.get('tag')!r} has an unsafe filename")
    if asset.get("bytes") is not None or asset.get("sha256") is not None:
        raise EvidenceError(
            f"pending release {row.get('tag')!r} must keep exact identity null"
        )
    placeholders = asset.get("identity_placeholders")
    if placeholders != {
        "bytes": expected_bytes_token,
        "sha256": expected_sha256_token,
    }:
        raise EvidenceError(f"pending release {row.get('tag')!r} placeholder mismatch")
    expected_url = (
        f"https://github.com/{repository}/releases/download/"
        f"{urllib.parse.quote(str(row.get('tag')), safe='')}/"
        f"{urllib.parse.quote(filename, safe='._-')}"
    )
    if url != expected_url:
        raise EvidenceError(f"pending release {row.get('tag')!r} URL mismatch")
    return asset


def phase_name(value: str) -> str:
    normalized = value.upper()
    if normalized not in {"PREPUBLICATION", "POSTPUBLICATION"}:
        raise EvidenceError(f"unsupported verification phase: {value!r}")
    return normalized


def published_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [row for row in rows if row.get("publication_state") in PUBLISHED_STATES]


def release_placeholder_findings(paths: Iterable[Path] | None = None) -> list[str]:
    findings: list[str] = []
    candidates = paths if paths is not None else worktree_files()
    for path in sorted(candidates):
        if path.suffix.lower() not in {".json", ".md", ".txt", ".yml", ".yaml"}:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            raise EvidenceError(f"could not scan placeholder file {path}: {exc}") from exc
        relative = path.relative_to(ROOT).as_posix() if path.is_relative_to(ROOT) else str(path)
        for match in RELEASE_PLACEHOLDER_RE.finditer(text):
            findings.append(f"{relative}:{match.group(0)}")
    return findings


def require_pending_tokens() -> None:
    required = {
        PUBLICATION_MANIFEST: (
            PENDING_IDENTITY_TOKENS["generic_bytes"],
            PENDING_IDENTITY_TOKENS["generic_sha256"],
            PENDING_IDENTITY_TOKENS["outer_bytes"],
            PENDING_IDENTITY_TOKENS["outer_sha256"],
        ),
        GENERIC_REFERENCE: (
            PENDING_IDENTITY_TOKENS["generic_bytes"],
            PENDING_IDENTITY_TOKENS["generic_sha256"],
        ),
        GENERIC_TEST_RECORD: (
            PENDING_IDENTITY_TOKENS["generic_bytes"],
            PENDING_IDENTITY_TOKENS["generic_sha256"],
        ),
        INNER_ADMISSION: (
            PENDING_IDENTITY_TOKENS["inner_bytes"],
            PENDING_IDENTITY_TOKENS["inner_sha256"],
        ),
        OUTER_AUTHORIZATION: (
            PENDING_IDENTITY_TOKENS["outer_bytes"],
            PENDING_IDENTITY_TOKENS["outer_sha256"],
        ),
        RELEASE_NOTES["generic-myth-v0.2.0"]: (
            PENDING_IDENTITY_TOKENS["generic_bytes"],
            PENDING_IDENTITY_TOKENS["generic_sha256"],
        ),
        RELEASE_NOTES["r1.0.1-2026-08-17"]: (
            PENDING_IDENTITY_TOKENS["inner_bytes"],
            PENDING_IDENTITY_TOKENS["inner_sha256"],
            PENDING_IDENTITY_TOKENS["outer_bytes"],
            PENDING_IDENTITY_TOKENS["outer_sha256"],
        ),
    }
    for path, tokens in required.items():
        text = path.read_text(encoding="utf-8")
        for token in tokens:
            if token not in text:
                raise EvidenceError(
                    f"prepublication placeholder missing from {path.relative_to(ROOT)}: {token}"
                )


def check_nonclaims(label: str, nonclaims: Any) -> None:
    if not isinstance(nonclaims, dict):
        raise EvidenceError(f"{label} has no nonclaims object")
    for key in REQUIRED_NONCLAIM_KEYS:
        if nonclaims.get(key) is not False:
            raise EvidenceError(f"{label} must explicitly set nonclaim false: {key}")
    if "deployment_authorized" in nonclaims and nonclaims["deployment_authorized"] is not False:
        raise EvidenceError(f"{label} nonclaim must be false: deployment_authorized")


def require_exact_identity(label: str, artifact: Any, expected: dict[str, Any]) -> None:
    if not isinstance(artifact, dict):
        raise EvidenceError(f"{label} artifact is missing")
    for key in ("filename", "bytes", "sha256"):
        if artifact.get(key) != expected[key]:
            raise EvidenceError(f"{label} exact identity mismatch: {key}")
    if "identity_placeholders" in artifact:
        raise EvidenceError(f"{label} retains identity placeholders")


def validate_gate_1_authority(
    generic_authorization: dict[str, Any],
    inner_admission: dict[str, Any],
) -> None:
    if (
        generic_authorization.get("schema")
        != "project-shadow.generic-myth-sidecar-v0.2.0-exact-hash-public-release-authorization.v1"
        or generic_authorization.get("decision")
        != "AUTHORIZE_EXACT_HASH_OPTIONAL_PUBLIC_RELEASE"
    ):
        raise EvidenceError("Generic Myth exact-hash authorization is incomplete")
    require_exact_identity(
        "Generic Myth authorization",
        generic_authorization.get("artifact"),
        GENERIC_FINAL,
    )
    generic_artifact = generic_authorization["artifact"]
    if (
        generic_artifact.get("version") != "0.2.0"
        or generic_artifact.get("role") != "SEPARATE_OPTIONAL_COMPANION"
        or generic_artifact.get("default_enabled") is not False
        or generic_artifact.get("terminal_only") is not True
        or generic_artifact.get("operational_authority") is not False
    ):
        raise EvidenceError("Generic Myth authorized boundary mismatch")
    scope = generic_authorization.get("publication_scope")
    if not isinstance(scope, dict) or (
        scope.get("github_authorized") is not True
        or scope.get("hugging_face_authorized") is not True
        or scope.get("part_of_or_required_by_r1") is not False
        or scope.get("production_authorized") is not False
        or scope.get("operational_deployment_authorized") is not False
    ):
        raise EvidenceError("Generic Myth authorization scope mismatch")
    generic_confirmation = generic_authorization.get("maintainer_confirmation")
    if not isinstance(generic_confirmation, dict) or (
        generic_confirmation.get("confirmed_by") != GATE_1_CONFIRMED_BY
        or generic_confirmation.get("confirmed_at") != GATE_1_CONFIRMED_AT
        or generic_confirmation.get("statement") != GENERIC_AUTHORIZATION_STATEMENT
    ):
        raise EvidenceError("Generic Myth maintainer confirmation wording mismatch")

    if (
        inner_admission.get("schema")
        != "project-shadow.r1.0.1-inner-exact-hash-maintainer-admission.v1"
        or inner_admission.get("decision")
        != "ADMIT_EXACT_HASH_FOR_R1.0.1_REFERENCE_PACKAGING"
    ):
        raise EvidenceError("R1.0.1 final inner admission is incomplete")
    require_exact_identity("R1.0.1 admitted inner", inner_admission.get("inner"), INNER_FINAL)
    inner = inner_admission["inner"]
    if (
        inner.get("active_descendant_count") != 27
        or inner.get("operational_descendant_bytes_changed") != 0
        or inner.get("myth_payload_embedded") is not False
    ):
        raise EvidenceError("R1.0.1 inner invariants failed")
    inner_confirmation = inner_admission.get("maintainer_confirmation")
    if not isinstance(inner_confirmation, dict) or (
        inner_confirmation.get("confirmed_by") != GATE_1_CONFIRMED_BY
        or inner_confirmation.get("confirmed_at") != GATE_1_CONFIRMED_AT
        or inner_confirmation.get("statement") != INNER_ADMISSION_STATEMENT
    ):
        raise EvidenceError("R1.0.1 inner maintainer confirmation wording mismatch")
    if inner_admission.get("non_authorizations") != {
        "production_authorized": False,
        "deployment_authorized": False,
        "publication_authorized": False,
    }:
        raise EvidenceError("R1.0.1 inner admission broadened authority")


def validate_final_generic_tests(record: dict[str, Any]) -> None:
    require_exact_identity("Generic Myth test record", record.get("final_artifact"), GENERIC_FINAL)
    results = record.get("final_results")
    if not isinstance(results, dict) or (
        record.get("status") != "PASS"
        or results.get("unit_tests") != 32
        or results.get("unit_test_status") != "PASS"
        or results.get("adversarial_mutation_tests_passed") != 11
        or results.get("deterministic_rebuilds") != 2
        or results.get("deterministic_rebuilds_byte_identical") is not True
        or results.get("exact_path_inventory") != "23/23_NO_EXTRAS"
        or results.get("source_tree_checksum_verifier") != "PASS"
        or results.get("packed_checksum_verifier") != "PASS"
        or results.get("rights_asset_scan") != "PASS"
        or results.get("rights_files_scanned") != 19
        or results.get("zip_integrity") != "PASS"
    ):
        raise EvidenceError("Generic Myth final test evidence mismatch")


def validate_outer_authority(record: dict[str, Any]) -> None:
    if (
        record.get("schema")
        != "project-shadow.r1.0.1-outer-exact-hash-public-release-authorization.v1"
        or record.get("decision") != "AUTHORIZE_EXACT_HASH_PUBLIC_RELEASE"
    ):
        raise EvidenceError("R1.0.1 exact-hash publication authorization absent")
    require_exact_identity("R1.0.1 outer authorization", record.get("outer"), OUTER_FINAL)
    outer = record["outer"]
    if (
        outer.get("title")
        != "Project Shadow 1.0.1 — R1 Reference Packaging Correction"
        or outer.get("tag") != "r1.0.1-2026-08-17"
        or record.get("authorized_actions")
        != {
            "github_release": True,
            "hugging_face_release": True,
            "verified_github_repository_update": True,
            "six_gpt_site_updates_and_deployments": True,
        }
        or record.get("non_authorizations")
        != {
            "production_authorized": False,
            "operational_deployment_authorized": False,
        }
    ):
        raise EvidenceError("R1.0.1 outer authorization scope mismatch")
    confirmation = record.get("maintainer_confirmation")
    if not isinstance(confirmation, dict) or (
        confirmation.get("confirmed_by") != GATE_1_CONFIRMED_BY
        or confirmation.get("confirmed_at") != OUTER_AUTHORIZATION_CONFIRMED_AT
        or confirmation.get("statement") != OUTER_AUTHORIZATION_STATEMENT
    ):
        raise EvidenceError("R1.0.1 outer maintainer confirmation wording mismatch")


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


def validate_public_documentation(
    phase: str = "PREPUBLICATION",
    *,
    pending_identities: bool = False,
) -> None:
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
            "older generic Myth v0.1.1",
            "separate",
            "Off is the default",
            AUTHORIZATION_RECEIPT_URL,
            AUTHORIZATION_JSON_URL,
        ),
    )
    require_document_markers(
        "Full-Canon Myth v0.3.5 release notes",
        RELEASE_NOTES["myth-v0.3.5"],
        (
            "myth-v0.3.5",
            "2b55867fe7c502a0defd8d6f2e9b53fbd1caaf1b0f225a438bd45b04a3e7bae2",
            "optional",
            "default-off",
        ),
    )
    generic_markers = [
        "generic-myth-v0.2.0",
        "never embedded in R1.0.1",
        "No production or operational deployment is authorized",
    ]
    r1_markers = [
        "r1.0.1-2026-08-17",
        "7a557efad953cbafd9e3ea9eb29b2d3e3e1bc6ab99dcf6b9ae7a99c487b0754d",
        "R1.0.1 contains no Myth payload",
    ]
    if phase_name(phase) == "PREPUBLICATION" and pending_identities:
        generic_markers.extend(
            (
                PENDING_IDENTITY_TOKENS["generic_bytes"],
                PENDING_IDENTITY_TOKENS["generic_sha256"],
            )
        )
        r1_markers.extend(
            (
                PENDING_IDENTITY_TOKENS["inner_sha256"],
                PENDING_IDENTITY_TOKENS["outer_sha256"],
            )
        )
    require_document_markers(
        "Generic Myth v0.2.0 release notes",
        RELEASE_NOTES["generic-myth-v0.2.0"],
        generic_markers,
    )
    require_document_markers(
        "R1.0.1 release notes",
        RELEASE_NOTES["r1.0.1-2026-08-17"],
        r1_markers,
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
    if phase_name(phase) == "POSTPUBLICATION":
        require_document_markers(
            "repository README",
            ROOT / "README.md",
            (
                "POSTPUBLICATION",
                "CLOSED_EFFECTIVE",
                "r1.0.1-2026-08-17",
                "generic-myth-v0.2.0",
            ),
        )
        require_document_markers(
            "release index",
            ROOT / "RELEASES.md",
            (
                "POSTPUBLICATION",
                "r1.0.1-2026-08-17",
                "generic-myth-v0.2.0",
            ),
        )


def validate_current_redownload(
    record: dict[str, Any],
    by_tag: dict[str, dict[str, Any]],
) -> None:
    if record.get("schema") != "project-shadow.r1.0.1-public-redownload-verification.v1":
        raise EvidenceError("unsupported R1.0.1 redownload schema")
    if record.get("status") != "VERIFIED" or record.get("anonymous_download") is not True:
        raise EvidenceError("R1.0.1 redownload record is not anonymous/VERIFIED")
    check_nonclaims("R1.0.1 redownload record", record.get("nonclaims"))
    observations = record.get("observations")
    if not isinstance(observations, list):
        raise EvidenceError("R1.0.1 redownload observations missing")
    expected: dict[tuple[str, str], dict[str, Any]] = {}
    for tag, role in (
        ("generic-myth-v0.2.0", "OPTIONAL_GENERIC_COMPANION"),
        ("r1.0.1-2026-08-17", "R1_REFERENCE_CORRECTED"),
    ):
        asset = by_tag[tag]["asset"]
        expected[(role, "GITHUB")] = asset
        expected[(role, "HUGGING_FACE")] = asset
    observed_keys: set[tuple[str, str]] = set()
    for row in observations:
        if not isinstance(row, dict):
            raise EvidenceError("invalid R1.0.1 redownload observation")
        key = (str(row.get("role")), str(row.get("host")))
        asset = expected.get(key)
        if asset is None or key in observed_keys:
            raise EvidenceError(f"unexpected/duplicate redownload observation: {key}")
        observed_keys.add(key)
        if (
            row.get("filename") != asset["filename"]
            or row.get("bytes_expected") != asset["bytes"]
            or row.get("bytes_observed") != asset["bytes"]
            or row.get("sha256_expected") != asset["sha256"]
            or row.get("sha256_observed") != asset["sha256"]
            or row.get("identity_verified") is not True
        ):
            raise EvidenceError(f"redownload identity mismatch: {key}")
    if observed_keys != set(expected):
        raise EvidenceError("redownload record lacks GitHub/Hugging Face coverage")


def verify_repository_metadata(phase: str = "PREPUBLICATION") -> list[dict[str, Any]]:
    phase = phase_name(phase)
    manifest = require_object(load_json(PUBLICATION_MANIFEST), "PUBLICATION_MANIFEST.json")
    authorization = require_object(load_json(AUTHORIZATION), AUTHORIZATION.name)
    sidecar_reference = require_object(load_json(SIDECAR_REFERENCE), SIDECAR_REFERENCE.name)
    r1_manifest = require_object(load_json(R1_PACKAGE_MANIFEST), R1_PACKAGE_MANIFEST.name)
    gates = require_object(load_json(R1_RELEASE_GATES), R1_RELEASE_GATES.name)
    signature_receipt = require_object(load_json(SIGNATURE_RECEIPT), SIGNATURE_RECEIPT.name)
    current_status = require_object(load_json(CURRENT_STATUS), CURRENT_STATUS.name)
    full_canon_reference = require_object(
        load_json(FULL_CANON_V035_REFERENCE), FULL_CANON_V035_REFERENCE.name
    )
    full_canon_publication = require_object(
        load_json(FULL_CANON_V035_PUBLICATION), FULL_CANON_V035_PUBLICATION.name
    )
    generic_reference = require_object(load_json(GENERIC_REFERENCE), GENERIC_REFERENCE.name)
    generic_tests = require_object(load_json(GENERIC_TEST_RECORD), GENERIC_TEST_RECORD.name)
    generic_authorization = require_object(
        load_json(GENERIC_AUTHORIZATION), GENERIC_AUTHORIZATION.name
    )
    inner_admission = require_object(load_json(INNER_ADMISSION), INNER_ADMISSION.name)
    outer_authorization = require_object(
        load_json(OUTER_AUTHORIZATION), OUTER_AUTHORIZATION.name
    )
    capa = require_object(load_json(CAPA_RECORD), CAPA_RECORD.name)

    if manifest.get("schema") != "project-shadow.publication-manifest.v2":
        raise EvidenceError("unsupported publication manifest schema")
    if manifest.get("repository") != "PauseBeforeHarmProtocol/Project-Shadow":
        raise EvidenceError("unexpected repository identity")
    if manifest.get("publication_phase") != phase:
        raise EvidenceError(
            f"manifest phase mismatch: expected {phase}; "
            f"found {manifest.get('publication_phase')!r}"
        )
    check_nonclaims("publication manifest", manifest.get("nonclaims"))
    rows = release_rows(manifest)
    expected_tags = [
        "myth-v0.3.4",
        "r1-2026-08-14",
        "myth-v0.3.5",
        "generic-myth-v0.2.0",
        "r1.0.1-2026-08-17",
    ]
    if [row.get("tag") for row in rows] != expected_tags:
        raise EvidenceError("publication manifest release lineage/order mismatch")
    current_r1 = [
        row for row in rows
        if row.get("canonical_r1") is True and row.get("current") is True
    ]
    if len(current_r1) != 1 or current_r1[0].get("tag") != "r1.0.1-2026-08-17":
        raise EvidenceError("manifest must identify R1.0.1 as the sole current R1")
    if rows[-1] is not current_r1[0]:
        raise EvidenceError("corrected current R1 must remain last in publication order")

    by_tag = {str(row["tag"]): row for row in rows}
    for row in rows:
        tag = str(row.get("tag"))
        if tag not in RELEASE_NOTES:
            raise EvidenceError(f"no pinned release-notes file for tag {tag!r}")
        state = row.get("publication_state")
        if state in PUBLISHED_STATES:
            asset = validate_asset_row(row, manifest["repository"])
            identity_markers = (
                asset["filename"],
                asset["sha256"],
                f"{asset['bytes']:,}",
            )
        elif tag in {"generic-myth-v0.2.0", "r1.0.1-2026-08-17"} and phase == (
            "PREPUBLICATION"
        ):
            pending = row.get("asset", {}).get("bytes") is None
            if pending:
                prefix = "generic" if tag == "generic-myth-v0.2.0" else "outer"
                asset = validate_pending_asset_row(
                    row,
                    manifest["repository"],
                    expected_bytes_token=PENDING_IDENTITY_TOKENS[f"{prefix}_bytes"],
                    expected_sha256_token=PENDING_IDENTITY_TOKENS[f"{prefix}_sha256"],
                )
                identity_markers = (
                    asset["filename"],
                    PENDING_IDENTITY_TOKENS[f"{prefix}_bytes"],
                    PENDING_IDENTITY_TOKENS[f"{prefix}_sha256"],
                )
            else:
                allowed_concrete_states = (
                    {"AUTHORIZED_FOR_PUBLIC_RELEASE", "READY_TO_PUBLISH"}
                    if tag == "generic-myth-v0.2.0"
                    else {"PENDING_EXACT_HASH_AUTHORIZATION", "READY_TO_PUBLISH"}
                )
                if state not in allowed_concrete_states:
                    raise EvidenceError(
                        f"concrete prepublication identity has invalid authority state: {tag}"
                    )
                asset = validate_asset_row(row, manifest["repository"])
                identity_markers = (
                    asset["filename"],
                    asset["sha256"],
                    f"{asset['bytes']:,}",
                )
        else:
            raise EvidenceError(f"release {tag!r} has invalid state for phase {phase}")

        note = RELEASE_NOTES[tag].read_text(encoding="utf-8")
        for expected in (tag,) + identity_markers:
            if expected not in note:
                raise EvidenceError(f"release notes for {tag} omit {expected!r}")
        if not note.lstrip().startswith("**"):
            raise EvidenceError(f"release notes for {tag} lack a bold first-line warning")
        if tag == "myth-v0.3.5":
            source_warning_present = (
                "automatically generated source archive" in note
                and "repackaged copy" in note
            )
        else:
            source_warning_present = (
                "automatically generated" in note and "Source code (zip)" in note
            )
        if not source_warning_present:
            raise EvidenceError(f"release notes for {tag} omit the source-archive warning")

    # Preserve and validate the original two-artifact publication as a closed,
    # historical evidence set. New rows never rewrite its authorization.
    if authorization.get("schema") != "project-shadow.public-release-authorization-receipt.v1":
        raise EvidenceError("unsupported historical release-authorization schema")
    if authorization.get("status") != "AUTHORIZED_FOR_PUBLIC_RELEASE":
        raise EvidenceError("historical human release authorization is missing")
    if authorization.get("cryptographic_signature_claimed_for_this_receipt") is not False:
        raise EvidenceError("historical authorization overstates cryptographic status")
    check_nonclaims("historical release authorization", authorization.get("nonclaims"))
    authorized_artifacts = authorization.get("artifacts")
    if not isinstance(authorized_artifacts, dict):
        raise EvidenceError("historical release authorization has no artifacts object")
    historical_rows = [by_tag["myth-v0.3.4"], by_tag["r1-2026-08-14"]]
    expected_sums: dict[str, str] = {}
    for row in historical_rows:
        asset = row["asset"]
        expected_sums[asset["filename"]] = asset["sha256"]
        key = AUTHORIZATION_KEYS[row["role"]]
        authorization_row = authorized_artifacts.get(key)
        if not isinstance(authorization_row, dict):
            raise EvidenceError(f"historical authorization missing {row['role']}")
        for field in ("filename", "bytes", "sha256"):
            if authorization_row.get(field) != asset[field]:
                raise EvidenceError(
                    f"historical authorization mismatch for {row['role']}: {field}"
                )
        if authorization_row.get("publication_authorized") is not True:
            raise EvidenceError(f"historical publication authorization absent for {row['role']}")
    if parse_sha256sums(SHA256SUMS) != expected_sums:
        raise EvidenceError("historical SHA256SUMS must remain the original two-artifact set")

    old_sidecar = by_tag["myth-v0.3.4"]
    if (
        old_sidecar.get("canonical_r1") is not False
        or old_sidecar.get("enabled_by_default") is not False
        or sidecar_reference.get("embedded") is not False
        or sidecar_reference.get("canonical_r1") is not False
        or sidecar_reference.get("enabled_by_default") is not False
        or sidecar_reference.get("publication_authorized_by_this_candidate") is not False
    ):
        raise EvidenceError("historical Myth sidecar boundary failed")
    for key in ("filename", "bytes", "sha256"):
        if sidecar_reference.get(key) != old_sidecar["asset"][key]:
            raise EvidenceError(f"historical Myth reference mismatch: {key}")
    for key in (
        "outer_custody_container_embedded",
        "raw_private_report_embedded",
        "historical_myth_v0_3_3_embedded",
        "sanitized_myth_successor_embedded",
        "publication_authorized",
    ):
        if r1_manifest.get(key) is not False:
            raise EvidenceError(f"preserved August 14 R1 boundary failed: {key}")
    publication_gate = gates.get("post_build_publication_gate")
    if not isinstance(publication_gate, dict) or (
        publication_gate.get("satisfied") is not False
        or publication_gate.get("external_to_candidate") is not True
    ):
        raise EvidenceError("preserved August 14 candidate gate was rewritten")
    governance_effect = signature_receipt.get("governance_effect")
    if not isinstance(governance_effect, dict) or (
        governance_effect.get("public_release_authorized") is not False
    ):
        raise EvidenceError("historical signature receipt must remain nonauthorizing")
    validate_resolved_publication_state(historical_rows, authorization, gates)

    # Validate the independently published Full-Canon v0.3.5 row.
    full_canon_row = by_tag["myth-v0.3.5"]
    for record in (full_canon_reference, full_canon_publication):
        artifact = record.get("artifact")
        if not isinstance(artifact, dict):
            raise EvidenceError("Full-Canon v0.3.5 record has no artifact")
        for key in ("filename", "bytes", "sha256"):
            if artifact.get(key) != full_canon_row["asset"][key]:
                raise EvidenceError(f"Full-Canon v0.3.5 identity mismatch: {key}")
    if (
        full_canon_row.get("canonical_r1") is not False
        or full_canon_row.get("enabled_by_default") is not False
        or full_canon_publication.get("relationship_to_r1")
        != "SEPARATE_OPTIONAL_COMPANION_NOT_R1_ADMITTED"
        or full_canon_publication.get("production_or_operational_deployment_authorized")
        is not False
        or full_canon_publication.get("operational_authority_granted") is not False
    ):
        raise EvidenceError("Full-Canon v0.3.5 optional/nonauthorizing boundary failed")

    generic_row = by_tag["generic-myth-v0.2.0"]
    generic_artifact = generic_reference.get("artifact")
    generic_test_artifact = generic_tests.get("final_artifact")
    if not isinstance(generic_artifact, dict) or not isinstance(generic_test_artifact, dict):
        raise EvidenceError("Generic Myth reference/test artifact is missing")
    if generic_reference.get("test_record") != (
        "governance/GENERIC_MYTH_v0.2.0_BUILD_AND_TEST_REPORT_2026-08-17.json"
    ):
        raise EvidenceError("Generic Myth test-record pointer mismatch")
    if generic_reference.get("authorization_record") != (
        "governance/GENERIC_MYTH_v0.2.0_EXACT_HASH_PUBLIC_RELEASE_AUTHORIZATION_2026-08-17.json"
    ):
        raise EvidenceError("Generic Myth authorization-record pointer mismatch")
    boundaries = generic_reference.get("boundaries")
    if not isinstance(boundaries, dict):
        raise EvidenceError("Generic Myth boundary object missing")
    for key in (
        "canonical_r1_component",
        "changes_operational_result",
        "default_off",
        "feedback_allowed",
        "gate_input_eligible",
        "model_context_eligible",
        "operational_deployment_authorized",
        "production_authorized",
        "required_for_r1",
        "terminal_only",
        "tool_argument_eligible",
    ):
        expected = key in {"default_off", "terminal_only"}
        if boundaries.get(key) is not expected:
            raise EvidenceError(f"Generic Myth boundary mismatch: {key}")

    inner = inner_admission.get("inner")
    outer_asset = outer_authorization.get("outer")
    if not isinstance(outer_asset, dict):
        outer_asset = outer_authorization.get("asset")
    if not isinstance(inner, dict) or not isinstance(outer_asset, dict):
        raise EvidenceError("R1.0.1 inner/outer identity record missing")
    if (
        inner.get("active_descendant_count") != 27
        or inner.get("operational_descendant_bytes_changed") != 0
        or inner.get("myth_payload_embedded") is not False
    ):
        raise EvidenceError("R1.0.1 inner invariants failed")
    if "nonclaims" in outer_authorization:
        check_nonclaims("R1.0.1 outer authorization", outer_authorization.get("nonclaims"))
    check_nonclaims("CAPA", capa.get("nonclaims"))
    check_nonclaims("current release status", current_status.get("nonclaims"))

    pending_identities = False
    if phase == "PREPUBLICATION":
        prepublication_state = manifest.get("prepublication_state")
        if prepublication_state == "PENDING_IDENTITIES":
            pending_identities = True
            require_pending_tokens()
            if generic_reference.get("publication", {}).get("state") != (
                "PENDING_FINAL_HARDENED_IDENTITY"
            ):
                raise EvidenceError("Generic Myth reference is not pending final identity")
            if generic_tests.get("status") != "PENDING_HARDENED_REBUILD_AND_RETEST":
                raise EvidenceError("Generic Myth test record overstates final status")
            if generic_row.get("publication_state") != "PENDING_FINAL_HARDENED_IDENTITY":
                raise EvidenceError("Generic Myth manifest state is not pending")
            for artifact in (
                generic_row["asset"],
                generic_artifact,
                generic_test_artifact,
            ):
                if artifact.get("bytes") is not None or artifact.get("sha256") is not None:
                    raise EvidenceError("Generic Myth pending identity must remain null")
            if (
                inner_admission.get("decision") != "PENDING_MAINTAINER_CONFIRMATION"
                or inner_admission.get("maintainer_confirmation") is not None
                or inner.get("bytes") is not None
                or inner.get("sha256") is not None
            ):
                raise EvidenceError("R1.0.1 inner admission placeholder is not fail-closed")
            if (
                outer_authorization.get("status") != "PENDING_EXACT_HASH_AUTHORIZATION"
                or outer_authorization.get("authorization", {}).get(
                    "publication_authorized"
                )
                is not False
                or outer_asset.get("bytes") is not None
                or outer_asset.get("sha256") is not None
            ):
                raise EvidenceError(
                    "R1.0.1 outer authorization placeholder is not fail-closed"
                )
        elif prepublication_state == "AWAITING_OUTER_EXACT_HASH_AUTHORIZATION":
            placeholder_findings = release_placeholder_findings()
            if placeholder_findings:
                raise EvidenceError(
                    "exact-identity prepublication repository retains release placeholders: "
                    + ", ".join(placeholder_findings)
                )
            if generic_row.get("publication_state") != "AUTHORIZED_FOR_PUBLIC_RELEASE":
                raise EvidenceError("Generic Myth manifest authorization state mismatch")
            if by_tag["r1.0.1-2026-08-17"].get("publication_state") != (
                "PENDING_EXACT_HASH_AUTHORIZATION"
            ):
                raise EvidenceError("R1.0.1 manifest is not pending exact-hash authorization")
            require_exact_identity("Generic Myth manifest", generic_row.get("asset"), GENERIC_FINAL)
            require_exact_identity(
                "R1.0.1 manifest",
                by_tag["r1.0.1-2026-08-17"].get("asset"),
                OUTER_FINAL,
            )
            require_exact_identity("Generic Myth reference", generic_artifact, GENERIC_FINAL)
            if generic_artifact.get("frozen") is not True or (
                generic_reference.get("publication", {}).get("state")
                != "AUTHORIZED_FOR_PUBLIC_RELEASE"
            ):
                raise EvidenceError("Generic Myth frozen/authorized state mismatch")
            validate_final_generic_tests(generic_tests)
            validate_gate_1_authority(generic_authorization, inner_admission)
            inner_note = RELEASE_NOTES["r1.0.1-2026-08-17"].read_text(
                encoding="utf-8"
            )
            for marker in (
                INNER_FINAL["filename"],
                str(INNER_FINAL["sha256"]),
                f"{INNER_FINAL['bytes']:,}",
            ):
                if marker not in inner_note:
                    raise EvidenceError(
                        f"R1.0.1 release notes omit admitted inner identity: {marker}"
                    )
            require_exact_identity("R1.0.1 outer authority slot", outer_asset, OUTER_FINAL)
            if (
                outer_authorization.get("schema")
                != "project-shadow.r1.0.1-outer-exact-hash-public-release-authorization.pending.v1"
                or outer_authorization.get("status")
                != "PENDING_EXACT_HASH_AUTHORIZATION"
                or outer_authorization.get("authorization")
                != {
                    "confirmed_at": None,
                    "confirmed_by": None,
                    "publication_authorized": False,
                    "statement": None,
                }
            ):
                raise EvidenceError("R1.0.1 outer authorization is not fail-closed")
            if (
                current_status.get("generic_myth", {}).get(
                    "final_hardened_identity_bound"
                )
                is not True
                or current_status.get("generic_myth", {}).get(
                    "publication_authorization_recorded"
                )
                is not True
                or current_status.get("generic_myth", {}).get("publication_state")
                != "AUTHORIZED_FOR_PUBLIC_RELEASE"
                or current_status.get("current_reference", {}).get(
                    "final_outer_identity_bound"
                )
                is not True
                or current_status.get("current_reference", {}).get(
                    "inner_exact_hash_admitted"
                )
                is not True
                or current_status.get("current_reference", {}).get("publication_state")
                != "PENDING_EXACT_HASH_AUTHORIZATION"
                or capa.get("implementation", {}).get("final_exact_identities_bound")
                is not True
                or capa.get("implementation", {}).get(
                    "generic_exact_hash_publication_authorized"
                )
                is not True
                or capa.get("implementation", {}).get("inner_exact_hash_admitted")
                is not True
                or capa.get("implementation", {}).get(
                    "outer_exact_hash_publication_authorized"
                )
                is not False
            ):
                raise EvidenceError("awaiting-outer-authorization state is incomplete")
        elif prepublication_state == "READY_TO_PUBLISH":
            placeholder_findings = release_placeholder_findings()
            if placeholder_findings:
                raise EvidenceError(
                    "ready prepublication repository retains release placeholders: "
                    + ", ".join(placeholder_findings)
                )
            for tag in ("generic-myth-v0.2.0", "r1.0.1-2026-08-17"):
                if by_tag[tag].get("publication_state") != "READY_TO_PUBLISH":
                    raise EvidenceError(f"prepublication row is not READY_TO_PUBLISH: {tag}")
                validate_asset_row(by_tag[tag], manifest["repository"])
            if generic_reference.get("publication", {}).get("state") != (
                "READY_TO_PUBLISH"
            ):
                raise EvidenceError("Generic Myth ready evidence is incomplete")
            validate_final_generic_tests(generic_tests)
            validate_gate_1_authority(generic_authorization, inner_admission)
            for artifact in (generic_artifact, generic_test_artifact):
                for key in ("filename", "bytes", "sha256"):
                    if artifact.get(key) != generic_row["asset"][key]:
                        raise EvidenceError(f"Generic Myth final identity mismatch: {key}")
            inner_note = RELEASE_NOTES["r1.0.1-2026-08-17"].read_text(
                encoding="utf-8"
            )
            for marker in (
                inner["filename"],
                str(inner["sha256"]),
                f"{inner['bytes']:,}",
            ):
                if marker not in inner_note:
                    raise EvidenceError(
                        f"R1.0.1 release notes omit admitted inner identity: {marker}"
                    )
            current_r1_asset = by_tag["r1.0.1-2026-08-17"]["asset"]
            for key in ("filename", "bytes", "sha256"):
                if outer_asset.get(key) != current_r1_asset[key]:
                    raise EvidenceError(f"R1.0.1 outer authorization mismatch: {key}")
            validate_outer_authority(outer_authorization)
            if (
                current_status.get("generic_myth", {}).get(
                    "final_hardened_identity_bound"
                )
                is not True
                or current_status.get("current_reference", {}).get(
                    "final_outer_identity_bound"
                )
                is not True
                or current_status.get("current_reference", {}).get(
                    "inner_exact_hash_admitted"
                )
                is not True
                or current_status.get("generic_myth", {}).get("publication_state")
                != "READY_TO_PUBLISH"
                or current_status.get("current_reference", {}).get("publication_state")
                != "READY_TO_PUBLISH"
                or capa.get("implementation", {}).get("final_exact_identities_bound")
                is not True
                or capa.get("implementation", {}).get(
                    "generic_exact_hash_publication_authorized"
                )
                is not True
                or capa.get("implementation", {}).get("inner_exact_hash_admitted")
                is not True
                or capa.get("implementation", {}).get(
                    "outer_exact_hash_publication_authorized"
                )
                is not True
            ):
                raise EvidenceError("ready prepublication identity state is incomplete")
        else:
            raise EvidenceError(
                f"unsupported prepublication state: {prepublication_state!r}"
            )
        if (
            current_status.get("publication_phase") != "PREPUBLICATION"
            or current_status.get("capa", {}).get("status")
            != "IMPLEMENTED_PENDING_EFFECTIVENESS"
            or current_status.get("capa", {}).get("effectiveness_verified") is not False
            or capa.get("status") != "IMPLEMENTED_PENDING_EFFECTIVENESS"
            or capa.get("closure", {}).get("effectiveness_verified") is not False
        ):
            raise EvidenceError("current status/CAPA prepublication state mismatch")
    else:
        placeholder_findings = release_placeholder_findings()
        if placeholder_findings:
            raise EvidenceError(
                "postpublication repository retains release placeholders: "
                + ", ".join(placeholder_findings)
            )
        for tag in ("generic-myth-v0.2.0", "r1.0.1-2026-08-17"):
            if by_tag[tag].get("publication_state") != "PUBLISHED":
                raise EvidenceError(f"postpublication manifest row is not PUBLISHED: {tag}")
            validate_asset_row(by_tag[tag], manifest["repository"])
        if (
            generic_reference.get("publication", {}).get("state") != "PUBLISHED"
            or generic_tests.get("status") != "PASS"
        ):
            raise EvidenceError("Generic Myth postpublication evidence is incomplete")
        validate_final_generic_tests(generic_tests)
        validate_gate_1_authority(generic_authorization, inner_admission)
        for artifact in (generic_artifact, generic_test_artifact):
            for key in ("filename", "bytes", "sha256"):
                if artifact.get(key) != generic_row["asset"][key]:
                    raise EvidenceError(f"Generic Myth final identity mismatch: {key}")
        current_r1_asset = by_tag["r1.0.1-2026-08-17"]["asset"]
        for key in ("filename", "bytes", "sha256"):
            if outer_asset.get(key) != current_r1_asset[key]:
                raise EvidenceError(f"R1.0.1 outer authorization mismatch: {key}")
        validate_outer_authority(outer_authorization)
        if (
            current_status.get("publication_phase") != "POSTPUBLICATION"
            or current_status.get("capa", {}).get("status") != "CLOSED_EFFECTIVE"
            or current_status.get("capa", {}).get("effectiveness_verified") is not True
            or capa.get("status") != "CLOSED_EFFECTIVE"
            or capa.get("closure", {}).get("effectiveness_verified") is not True
            or capa.get("closure", {}).get("verification_record")
            != "governance/R1_0_1_PUBLIC_REDOWNLOAD_VERIFICATION_2026-08-17.json"
        ):
            raise EvidenceError("current status/CAPA postpublication closure mismatch")
        validate_current_redownload(
            require_object(load_json(CURRENT_REDOWNLOAD), CURRENT_REDOWNLOAD.name),
            by_tag,
        )

    validate_public_documentation(phase, pending_identities=pending_identities)
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


def verify_live_release_metadata(
    rows: list[dict[str, Any]],
    expected_latest_tag: str,
) -> None:
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
    if latest.get("tag_name") != expected_latest_tag:
        raise EvidenceError(
            f"unexpected latest GitHub release: expected {expected_latest_tag!r}; "
            f"found {latest.get('tag_name')!r}"
        )


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


def verify_online(
    rows: list[dict[str, Any]],
    destination: Path,
    *,
    phase: str,
    expected_latest_tag: str,
) -> None:
    phase = phase_name(phase)
    online_rows = published_rows(rows) if phase == "PREPUBLICATION" else rows
    downloaded: dict[str, Path] = {}
    repository = "PauseBeforeHarmProtocol/Project-Shadow"
    for row in online_rows:
        asset = row["asset"]
        downloaded[row["role"]] = download_and_hash(asset, destination)
        release_url = f"https://github.com/{repository}/releases/tag/{row['tag']}"
        check_link(release_url)
    verify_live_release_metadata(online_rows, expected_latest_tag)
    if phase == "POSTPUBLICATION":
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
    parser.add_argument(
        "--phase",
        choices=("auto", "prepublication", "postpublication"),
        default="auto",
        help="validate an explicit lifecycle phase (default: read the manifest)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.online != (args.download_dir is not None):
        print("FAIL: --online and --download-dir must be supplied together", file=sys.stderr)
        return 2
    try:
        json_count = parse_all_json()
        manifest = require_object(load_json(PUBLICATION_MANIFEST), PUBLICATION_MANIFEST.name)
        phase = (
            phase_name(str(manifest.get("publication_phase")))
            if args.phase == "auto"
            else phase_name(args.phase)
        )
        rows = verify_repository_metadata(phase)
        findings = prohibited_claim_findings()
        if findings:
            raise EvidenceError(
                "unsupported production/safety/efficacy/certification/legal claims:\n  - "
                + "\n  - ".join(findings)
            )
        if args.online:
            latest_by_phase = manifest.get("expected_github_latest_tag")
            if not isinstance(latest_by_phase, dict):
                raise EvidenceError("manifest lacks expected latest-tag phase map")
            expected_latest = latest_by_phase.get(phase.lower())
            if not isinstance(expected_latest, str):
                raise EvidenceError(f"manifest lacks latest-tag expectation for {phase}")
            verify_online(
                rows,
                args.download_dir.resolve(),
                phase=phase,
                expected_latest_tag=expected_latest,
            )
    except EvidenceError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    print(f"PASS: parsed {json_count} repository JSON files")
    print(f"PASS: lifecycle phase {phase}")
    print("PASS: publication manifest, notes, lifecycle records, and authority state agree")
    print("PASS: historical August 14 status, redownload receipt, and attestation agree")
    print("PASS: Myth companions remain external, default-off, and nonauthorizing")
    print("PASS: corrected R1 boundary requires zero embedded Myth payload")
    print("PASS: preserved historical candidate/signature records remain non-self-authorizing")
    print("PASS: nonclaim scan")
    if args.online:
        print("PASS: exact published assets and release metadata")
        if phase == "POSTPUBLICATION":
            print("PASS: six public-site release links")
    else:
        print("INFO: network verification skipped (use --online --download-dir DIR)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
