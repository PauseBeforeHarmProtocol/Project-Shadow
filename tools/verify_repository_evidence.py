#!/usr/bin/env python3
"""Read-only CI verification for the Project Shadow public evidence surface.

This tool validates evidence already present in the repository and, with
``--online``, redownloads the exact public assets and checks public links.  It
has no publication, release-editing, tagging, or repository-write capability.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import io
import json
import os
import re
import stat
import subprocess
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from html.parser import HTMLParser
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
CAPA_REOPENING_RECORD = (
    ROOT
    / "governance"
    / "CAPA_PS-R1-PRIVATE-MYTH-PUBLIC-BOUNDARY-001_EFFECTIVENESS_REOPENING_2026-08-22.json"
)
CURRENT_REDOWNLOAD = (
    ROOT / "governance" / "R1_0_1_PUBLIC_REDOWNLOAD_VERIFICATION_2026-08-17.json"
)
SIX_SITE_EFFECTIVENESS = (
    ROOT
    / "governance"
    / "R1_0_1_SIX_PUBLIC_SITES_EFFECTIVENESS_VERIFICATION_2026-08-17.json"
)
SIX_SITE_REVERIFICATION = (
    ROOT
    / "governance"
    / "R1_0_1_SIX_PUBLIC_SITES_EFFECTIVENESS_REVERIFICATION_2026-08-22.json"
)
PUBLIC_BOUNDARY_HUMAN_REVIEW = (
    ROOT
    / "governance"
    / "R1_0_1_PUBLIC_BOUNDARY_V2_HUMAN_REVIEW_2026-08-22.json"
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
POSTPUBLICATION_REOPENING_PREAMBLE = (
    "> **Effectiveness correction — 2026-08-22.** CAPA "
    "`PS-R1-PRIVATE-MYTH-PUBLIC-BOUNDARY-001` moved to "
    "`IMPLEMENTED_PENDING_EFFECTIVENESS` on that date. The exact published artifact "
    "identities, bounded package verification, and recursive zero-Myth result remained "
    "valid. The six-site effectiveness criterion was reopened because the August 18 lexical checks "
    "did not adequately establish relation, uniqueness, contradiction rejection, and "
    "artifact-to-identity binding. The August 18 closure is preserved as historical "
    "evidence; this dated reopening paragraph does not determine a later current CAPA "
    "state. Reclosure requires retained exact "
    "response bodies, offline replay under a Git-bound verifier, and a named human "
    "review of all six browser-rendered sites.\n\n"
)
POSTPUBLICATION_CURRENT_STATE_PREAMBLES = {
    "IMPLEMENTED_PENDING_EFFECTIVENESS": (
        "> **Current CAPA state.** CAPA `PS-R1-PRIVATE-MYTH-PUBLIC-BOUNDARY-001` "
        "is `IMPLEMENTED_PENDING_EFFECTIVENESS`; public-boundary-v2 reverification "
        "and the named human rendered-site review remain pending.\n\n"
    ),
    "CLOSED_EFFECTIVE": (
        "> **Current CAPA state.** CAPA `PS-R1-PRIVATE-MYTH-PUBLIC-BOUNDARY-001` "
        "is `CLOSED_EFFECTIVE` under retained v2 response bodies, offline Git-bound "
        "replay, and the named human rendered-site review.\n\n"
    ),
}
POSTPUBLICATION_HISTORICAL_EFFECTIVENESS_PREAMBLE = (
    "> **Historical effectiveness event — 2026-08-18.** The CAPA was recorded as "
    "`CLOSED_EFFECTIVE` after exact GitHub and Hugging Face redownloads, bounded package "
    "verification, recursive zero-Myth verification, and the original six-site checks. "
    "That closure decision was superseded for current effectiveness on 2026-08-22; the "
    "underlying exact-byte and zero-Myth observations remain retained. No production or "
    "operational deployment is authorized, and no efficacy, safety, certification, "
    "legal-compliance, comprehensive-security, or independent-validation claim is made. "
    "The release text below retains the publication-time state.\n\n---\n\n"
)
POSTPUBLICATION_EFFECTIVENESS_PREAMBLE = (
    POSTPUBLICATION_REOPENING_PREAMBLE
    + POSTPUBLICATION_HISTORICAL_EFFECTIVENESS_PREAMBLE
)
FULL_CANON_POSTPUBLICATION_EFFECTIVENESS_PREAMBLE = (
    POSTPUBLICATION_REOPENING_PREAMBLE
    + POSTPUBLICATION_HISTORICAL_EFFECTIVENESS_PREAMBLE.replace("\n\n---\n\n", "\n\n")
    + "> **Scope note.** The reopened criterion concerns the separate R1 public-boundary "
    "CAPA; the original packaging finding did not apply to Full-Canon Myth v0.3.5.\n\n"
    "Current bounded compatibility command:\n\n"
    "```bash\n"
    "python3 -I -S -B tools/verify_package.py . --run-tests \\\n"
    "  --r1-family-zip /path/to/Project_Shadow_R1.0.1_Runtime_Family_Myth_Decoupled_2026-08-17.zip\n"
    "```\n\n---\n\n"
)
POSTPUBLICATION_RELEASE_PREAMBLES = {
    "myth-v0.3.5": FULL_CANON_POSTPUBLICATION_EFFECTIVENESS_PREAMBLE,
    "generic-myth-v0.2.0": POSTPUBLICATION_EFFECTIVENESS_PREAMBLE,
    "r1.0.1-2026-08-17": POSTPUBLICATION_EFFECTIVENESS_PREAMBLE,
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
CURRENT_OUTER_VERIFIER_SHA256 = (
    "721c384b245ca654c087d184bbfe5725d85d41536250140467d7cd913e6a1ccb"
)
GENERIC_V0_2_0_VERIFIER_SHA256 = (
    "0d84c8f90da35a16abbd410744ebd7df6f06a836e0c0b830b5213fb598087e9b"
)
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
CAPA_ID = "PS-R1-PRIVATE-MYTH-PUBLIC-BOUNDARY-001"
CURRENT_REDOWNLOAD_RECORD = (
    "governance/R1_0_1_PUBLIC_REDOWNLOAD_VERIFICATION_2026-08-17.json"
)
SIX_SITE_EFFECTIVENESS_RECORD = (
    "governance/"
    "R1_0_1_SIX_PUBLIC_SITES_EFFECTIVENESS_VERIFICATION_2026-08-17.json"
)
CAPA_REOPENING_RECORD_PATH = (
    "governance/"
    "CAPA_PS-R1-PRIVATE-MYTH-PUBLIC-BOUNDARY-001_EFFECTIVENESS_REOPENING_2026-08-22.json"
)
SIX_SITE_REVERIFICATION_RECORD = (
    "governance/"
    "R1_0_1_SIX_PUBLIC_SITES_EFFECTIVENESS_REVERIFICATION_2026-08-22.json"
)
PUBLIC_BOUNDARY_HUMAN_REVIEW_RECORD = (
    "governance/"
    "R1_0_1_PUBLIC_BOUNDARY_V2_HUMAN_REVIEW_2026-08-22.json"
)
HISTORICAL_CAPA_EFFECTIVENESS_RECORDS = (
    CURRENT_REDOWNLOAD_RECORD,
    SIX_SITE_EFFECTIVENESS_RECORD,
)
CAPA_EFFECTIVENESS_RECORDS = HISTORICAL_CAPA_EFFECTIVENESS_RECORDS
CURRENT_CAPA_EFFECTIVENESS_RECORDS = (
    CURRENT_REDOWNLOAD_RECORD,
    SIX_SITE_REVERIFICATION_RECORD,
    PUBLIC_BOUNDARY_HUMAN_REVIEW_RECORD,
)
REOPENED_EFFECTIVENESS_CRITERION = (
    "SIX_PUBLIC_PROJECT_SHADOW_SITES_REPORT_THE_CORRECTED_BOUNDARY"
)
RECLOSURE_REQUIREMENTS = (
    "DETERMINISTIC_RELATION_UNIQUENESS_CONTRADICTION_AND_BINDING_CHECKS_PASS",
    "ADVERSARIAL_NEGATIVE_CONTROLS_EXECUTE_WITH_EXPECTED_VERDICT_FLIPS",
    "ALL_REQUIRED_PUBLIC_ROUTES_PASS_THE_CORRECTED_V2_BOUNDARY_CONTRACT",
    "EXACT_RESPONSE_BODIES_ARE_RETAINED_AND_REPLAYED_OFFLINE",
    "EXPECTED_EXECUTED_SKIPPED_AND_NEGATIVE_CONTROL_COUNTS_ARE_RECORDED",
    "HUMAN_REVIEW_CONFIRMS_THE_VISIBLE_PUBLIC_MEANING",
)
HISTORICAL_CAPA_CLOSURE_EVENT = {
    "closed_at": "2026-08-18T10:39:24Z",
    "effectiveness_verified": True,
    "verification_record": CURRENT_REDOWNLOAD_RECORD,
    "verification_records": list(HISTORICAL_CAPA_EFFECTIVENESS_RECORDS),
}
HF_SPACE_RESOLVE_BASE = (
    "https://huggingface.co/spaces/ProjectShadow/"
    "project-shadow-r1-reference/resolve/main"
)
PUBLIC_SITE_REQUIREMENTS = (
    {
        "site_id": "project-shadow",
        "base_url": "https://projectshadow.frylock117.chatgpt.site",
        "routes": ("/", "/release", "/status", "/capa"),
        "specific_checks": (
            "outer_exact_identity",
            "inner_exact_identity",
            "generic_exact_identity",
            "full_canon_exact_identity",
            "member_set_identity",
            "capa_id",
            "capa_state",
        ),
    },
    {
        "site_id": "pause-before-harm",
        "base_url": "https://pausebeforeharm.frylock117.chatgpt.site",
        "routes": ("/",),
        "specific_checks": (),
    },
    {
        "site_id": "civic-qa",
        "base_url": "https://civicqa.frylock117.chatgpt.site",
        "routes": ("/",),
        "specific_checks": (),
    },
    {
        "site_id": "american-repair-manual",
        "base_url": "https://americanrepairmanual.frylock117.chatgpt.site",
        "routes": ("/", "/manual.html"),
        "specific_checks": ("archived_manual_current_boundary",),
    },
    {
        "site_id": "the-record",
        "base_url": "https://therecord.frylock117.chatgpt.site",
        "routes": ("/", "/corrections", "/national.html"),
        "specific_checks": (
            "capa_state",
            "national_trump_record",
        ),
    },
    {
        "site_id": "almsivi",
        "base_url": "https://almsivi.frylock117.chatgpt.site",
        "routes": ("/", "/technical/project-shadow"),
        "specific_checks": (
            "outer_exact_identity",
            "inner_exact_identity",
            "generic_exact_identity",
            "full_canon_exact_identity",
            "member_set_identity",
            "preserved_predecessor",
        ),
    },
)
PUBLIC_SITE_URLS = tuple(
    str(requirement["base_url"]) for requirement in PUBLIC_SITE_REQUIREMENTS
)
HISTORICAL_COMMON_SITE_CHECKS_V1 = (
    "r1_0_1_current",
    "contains_no_myth_package",
    "generic_v0_2_0",
    "full_canon_v0_3_5",
    "sidecars_separate",
    "sidecars_optional",
    "sidecars_default_off",
    "sidecars_nonauthorizing",
    "canonical_release_link",
    "capa_link",
)
COMMON_SITE_CHECKS = (
    "semantic_markup_unambiguous",
    "boundary_contract_unique",
    "r1_0_1_current",
    "historical_r1_superseded",
    "contains_no_myth_package",
    "generic_v0_2_0",
    "full_canon_v0_3_5",
    "sidecars_separate",
    "sidecars_optional",
    "sidecars_default_off",
    "sidecars_nonauthorizing",
    "boundary_no_contradictions",
    "canonical_release_link",
    "capa_link",
)
PUBLIC_BOUNDARY_CONTRACT = "public-boundary-v2"
PUBLIC_BOUNDARY_CURRENT_CLAIM = (
    "Project Shadow R1.0.1 is the current R1 reference. The August 14 R1 release "
    "is a preserved historical predecessor superseded by R1.0.1."
)
PUBLIC_BOUNDARY_SHARED_CLAIM = (
    "Project Shadow 1.0.1 contains no Myth package. Generic Myth v0.2.0 and "
    "Full-Canon Myth v0.3.5 are separate optional companions; both default off, "
    "neither is required by R1, and neither can authorize action or change an R1 result."
)
PUBLIC_BOUNDARY_CLAIMS = {
    "release-role": PUBLIC_BOUNDARY_CURRENT_CLAIM,
    "sidecar-role": PUBLIC_BOUNDARY_SHARED_CLAIM,
}
PUBLIC_BOUNDARY_BAND_ATTRIBUTES = {
    "data-shadow-contract": PUBLIC_BOUNDARY_CONTRACT,
    "data-shadow-current-release": "r1.0.1-2026-08-17",
    "data-shadow-historical-release": "r1-2026-08-14",
    "data-shadow-historical-state": "preserved-superseded",
    "data-shadow-zero-myth": "true",
    "data-shadow-generic-myth-role": "separate-optional-default-off-nonauthorizing",
    "data-shadow-full-canon-myth-role": "separate-optional-default-off-nonauthorizing",
}
OPERATIONAL_MEMBER_SET_SHA256 = (
    "7a557efad953cbafd9e3ea9eb29b2d3e3e1bc6ab99dcf6b9ae7a99c487b0754d"
)
PUBLIC_ARTIFACT_BINDINGS = {
    "outer_exact_identity": {
        "artifact_id": "r1_0_1_outer",
        **OUTER_FINAL,
    },
    "inner_exact_identity": {
        "artifact_id": "r1_0_1_inner",
        **INNER_FINAL,
    },
    "generic_exact_identity": {
        "artifact_id": "generic_myth_v0_2_0",
        **GENERIC_FINAL,
    },
    "full_canon_exact_identity": {
        "artifact_id": "full_canon_myth_v0_3_5",
        "filename": (
            "Project_Shadow_Full_Canon_Myth_Sidecar_"
            "v0.3.5_OPTIONAL_PUBLIC_COMPANION_2026-08-17.zip"
        ),
        "bytes": 1_428_812,
        "sha256": "2b55867fe7c502a0defd8d6f2e9b53fbd1caaf1b0f225a438bd45b04a3e7bae2",
    },
    "member_set_identity": {
        "artifact_id": "r1_0_1_operational_member_set",
        "filename": "R1.0.1 operational member set",
        "member_count": 27,
        "sha256": OPERATIONAL_MEMBER_SET_SHA256,
    },
    "preserved_predecessor": {
        "artifact_id": "r1_2026_08_14_predecessor",
        "filename": "Project_Shadow_R1_Public_Release_Candidate_2026-08-14.zip",
        "bytes": 7_679_812,
        "sha256": "2f8fe1530b6a83294d15011df95853aaecf08fa4dba756f0c2e91dd089e1b1ec",
    },
}
MAX_LINK_RESPONSE_BYTES = 2 * 1024 * 1024
SITE_ROUTE_FINAL_PATH_OVERRIDES = {
    ("american-repair-manual", "/manual.html"): "/manual",
    ("the-record", "/national.html"): "/national",
}
SITE_ROUTE_MAX_BYTES_OVERRIDES = {
    ("the-record", "/national.html"): 16 * 1024 * 1024,
}
SITE_RECEIPT_METHOD = {
    "anonymous_https": True,
    "http_status_required": 200,
    "default_max_response_bytes": 2 * 1024 * 1024,
    "route_max_response_bytes": {
        "the-record:/national.html": 16 * 1024 * 1024,
    },
    "response_hash_algorithm": "SHA-256",
    "content_type_prefix": "text/html",
    "same_origin_final_url_required": True,
    "semantic_content_checks": True,
}
SITE_REVERIFICATION_RECEIPT_METHOD = {
    **SITE_RECEIPT_METHOD,
    "semantic_contract": PUBLIC_BOUNDARY_CONTRACT,
    "exact_response_bodies_retained": True,
    "offline_replay_required": True,
    "adversarial_negative_controls_required": True,
}
SITE_RESPONSE_EVIDENCE_PACK_FILENAME = (
    "R1_0_1_SIX_PUBLIC_SITES_RESPONSE_EVIDENCE_2026-08-22.zip"
)
SITE_REVERIFICATION_RECEIPT_FILENAME = (
    "R1_0_1_SIX_PUBLIC_SITES_EFFECTIVENESS_REVERIFICATION_2026-08-22.json"
)
VERIFIER_SOURCE_PATH = "tools/verify_repository_evidence.py"
PUBLIC_BOUNDARY_HUMAN_REVIEW_ATTESTATION = (
    "I personally reviewed the browser-rendered public pages and the retained "
    "response bodies and confirm that their ordinary visible meaning matches "
    "public-boundary-v2."
)
PUBLIC_BOUNDARY_HUMAN_REVIEW_DETERMINATIONS = {
    "r1_0_1_is_the_sole_current_r1": True,
    "august_14_r1_is_a_preserved_superseded_predecessor": True,
    "sidecars_are_separate_optional_default_off_and_nonauthorizing": True,
    "artifact_identities_are_bound_to_their_intended_records": True,
    "capa_state_is_unambiguous": True,
    "browser_rendered_contract_is_visible": True,
}
MAX_SITE_EVIDENCE_PACK_MEMBERS = sum(
    len(requirement["routes"]) for requirement in PUBLIC_SITE_REQUIREMENTS
)
# The 13 retained routes have a 40 MiB aggregate expanded-size ceiling.
MAX_SITE_EVIDENCE_EXPANDED_BYTES = 40 * 1024 * 1024
CURRENT_MIRROR_PATHS = {
    "generic-myth-v0.2.0": (
        "releases/generic-myth-v0.2.0/"
        "Project_Shadow_Generic_Myth_Sidecar_v0.2.0_OPTIONAL_PUBLIC_COMPANION_2026-08-17.zip"
    ),
    "r1.0.1-2026-08-17": (
        "releases/r1.0.1-2026-08-17/"
        "Project_Shadow_R1.0.1_Public_Reference_2026-08-17.zip"
    ),
}
PUBLIC_DOWNLOAD_FINAL_HOSTS = {
    "GITHUB": frozenset({"github.com", "release-assets.githubusercontent.com"}),
    "HUGGING_FACE": frozenset(
        {"huggingface.co", "us.aws.cdn.hf.co", "us.gcp.cdn.hf.co"}
    ),
}
USER_AGENT = "Project-Shadow-read-only-evidence-verifier/2.0"

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
    "neither ",
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


def parse_rfc3339_utc(label: str, value: Any) -> datetime:
    if not isinstance(value, str) or re.fullmatch(
        r"20\d\d-(?:0[1-9]|1[0-2])-(?:0[1-9]|[12]\d|3[01])T"
        r"(?:[01]\d|2[0-3]):[0-5]\d:[0-5]\dZ",
        value,
    ) is None:
        raise EvidenceError(f"{label} is not RFC3339 UTC")
    try:
        return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(
            tzinfo=timezone.utc
        )
    except ValueError as exc:
        raise EvidenceError(f"{label} is not a real UTC timestamp") from exc


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
    phase: str = "POSTPUBLICATION",
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
        "Project Shadow Generic Myth Sidecar v0.2.0",
        GENERIC_FINAL["filename"],
        GENERIC_FINAL["sha256"],
        "separate from canonical Project Shadow R1",
        "default-off",
        "Terminal-only",
        "Nonauthorizing",
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
        current_status = require_object(load_json(CURRENT_STATUS), CURRENT_STATUS.name)
        current_capa_status = current_status.get("capa", {}).get("status")
        if current_capa_status not in {
            "IMPLEMENTED_PENDING_EFFECTIVENESS",
            "CLOSED_EFFECTIVE",
        }:
            raise EvidenceError("unsupported public documentation CAPA state")
        require_document_markers(
            "repository README",
            ROOT / "README.md",
            (
                "POSTPUBLICATION",
                str(current_capa_status),
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
    recorded_at = record.get("recorded_at")
    parse_rfc3339_utc("R1.0.1 redownload timestamp", recorded_at)
    if record.get("method") != {
        "anonymous_https": True,
        "exact_byte_count_and_sha256": True,
        "http_status_required": 200,
    }:
        raise EvidenceError("R1.0.1 redownload method is incomplete")
    check_nonclaims("R1.0.1 redownload record", record.get("nonclaims"))
    observations = record.get("observations")
    if not isinstance(observations, list):
        raise EvidenceError("R1.0.1 redownload observations missing")
    expected: dict[tuple[str, str], tuple[dict[str, Any], str]] = {}
    for tag, role in (
        ("generic-myth-v0.2.0", "OPTIONAL_GENERIC_COMPANION"),
        ("r1.0.1-2026-08-17", "R1_REFERENCE_CORRECTED"),
    ):
        asset = by_tag[tag]["asset"]
        expected[(role, "GITHUB")] = (asset, asset["download_url"])
        expected[(role, "HUGGING_FACE")] = (
            asset,
            f"{HF_SPACE_RESOLVE_BASE}/{CURRENT_MIRROR_PATHS[tag]}",
        )
    observed_keys: set[tuple[str, str]] = set()
    for row in observations:
        if not isinstance(row, dict):
            raise EvidenceError("invalid R1.0.1 redownload observation")
        key = (str(row.get("role")), str(row.get("host")))
        expected_row = expected.get(key)
        if expected_row is None or key in observed_keys:
            raise EvidenceError(f"unexpected/duplicate redownload observation: {key}")
        asset, expected_url = expected_row
        observed_keys.add(key)
        final_host = row.get("final_host")
        if not isinstance(final_host, str):
            raise EvidenceError(f"redownload final host missing: {key}")
        validate_public_download_final_host(key[1], f"https://{final_host}/")
        if (
            row.get("filename") != asset["filename"]
            or row.get("download_url") != expected_url
            or row.get("http_status") != 200
            or row.get("bytes_expected") != asset["bytes"]
            or row.get("bytes_observed") != asset["bytes"]
            or row.get("sha256_expected") != asset["sha256"]
            or row.get("sha256_observed") != asset["sha256"]
            or row.get("identity_verified") is not True
        ):
            raise EvidenceError(f"redownload identity mismatch: {key}")
    if observed_keys != set(expected):
        raise EvidenceError("redownload record lacks GitHub/Hugging Face coverage")
    generic_verification = record.get("generic_v0_2_0_bounded_verification")
    if generic_verification != {
        "tool": "tools/verify_generic_myth_v0_2_0.py",
        "tool_sha256": GENERIC_V0_2_0_VERIFIER_SHA256,
        "target": GENERIC_FINAL,
        "inventory_path_count": 23,
        "bounded_archive_verifier": True,
        "old_predecessor_embedded": False,
        "observations": [
            {"host": "GITHUB", "status": "PASS"},
            {"host": "HUGGING_FACE", "status": "PASS"},
        ],
    }:
        raise EvidenceError("Generic v0.2.0 public-download verification mismatch")
    recursive = record.get("r1_0_1_recursive_verification")
    if recursive != {
        "tool": "tools/verify_outer_release.py",
        "tool_sha256": CURRENT_OUTER_VERIFIER_SHA256,
        "target": OUTER_FINAL,
        "status": "PASS",
        "recursive_forbidden_payload_scan": True,
        "zero_embedded_myth_payload": True,
        "observations": [
            {"host": "GITHUB", "status": "PASS"},
            {"host": "HUGGING_FACE", "status": "PASS"},
        ],
    }:
        raise EvidenceError("R1.0.1 recursive public-download verification mismatch")


def required_site_checks(requirement: dict[str, Any]) -> tuple[str, ...]:
    satellite_checks = (
        ("no_direct_github_release_link",)
        if requirement["site_id"] != "project-shadow"
        else ()
    )
    return COMMON_SITE_CHECKS + satellite_checks + tuple(requirement["specific_checks"])


def historical_required_site_checks_v1(
    requirement: dict[str, Any],
) -> tuple[str, ...]:
    satellite_checks = (
        ("no_direct_github_release_link",)
        if requirement["site_id"] != "project-shadow"
        else ()
    )
    return (
        HISTORICAL_COMMON_SITE_CHECKS_V1
        + satellite_checks
        + tuple(requirement["specific_checks"])
    )


def semantic_check_execution(
    expected_checks: Iterable[str],
    checks: dict[str, bool],
) -> dict[str, Any]:
    expected = tuple(expected_checks)
    expected_set = set(expected)
    executed_set = set(checks)
    failed = sorted(
        check_id
        for check_id in expected
        if check_id in checks and checks[check_id] is not True
    )
    skipped = sorted(expected_set - executed_set)
    unexpected = sorted(executed_set - expected_set)
    return {
        "expected_count": len(expected),
        "executed_count": len(executed_set & expected_set),
        "passed_count": len(expected) - len(failed) - len(skipped),
        "failed_check_ids": failed,
        "skipped_check_ids": skipped,
        "unexpected_check_ids": unexpected,
    }


def require_complete_semantic_execution(
    label: str,
    expected_checks: Iterable[str],
    checks: dict[str, bool],
) -> dict[str, Any]:
    execution = semantic_check_execution(expected_checks, checks)
    if (
        execution["executed_count"] != execution["expected_count"]
        or execution["failed_check_ids"]
        or execution["skipped_check_ids"]
        or execution["unexpected_check_ids"]
    ):
        raise EvidenceError(
            f"{label} semantic execution incomplete or failed: "
            + json.dumps(execution, sort_keys=True)
        )
    return execution


def exact_public_site_url(base_url: str, route: str) -> str:
    if not route.startswith("/") or route.startswith("//"):
        raise EvidenceError(f"unsafe public-site route: {route!r}")
    return base_url + route


def site_route_key(requirement: dict[str, Any], route: str) -> tuple[str, str]:
    return (str(requirement["site_id"]), route)


def site_route_max_bytes(requirement: dict[str, Any], route: str) -> int:
    return SITE_ROUTE_MAX_BYTES_OVERRIDES.get(
        site_route_key(requirement, route),
        MAX_LINK_RESPONSE_BYTES,
    )


def expected_site_final_url(requirement: dict[str, Any], route: str) -> str:
    final_path = SITE_ROUTE_FINAL_PATH_OVERRIDES.get(
        site_route_key(requirement, route),
        route,
    )
    return exact_public_site_url(str(requirement["base_url"]), final_path)


def validate_six_public_sites_effectiveness(
    record: dict[str, Any],
    by_tag: dict[str, dict[str, Any]],
) -> None:
    """Validate retained route observations and corrected-boundary semantics."""
    if record.get("schema") != (
        "project-shadow.r1.0.1-six-public-sites-effectiveness-verification.v1"
    ):
        raise EvidenceError("unsupported six-public-sites effectiveness schema")
    if (
        record.get("capa_id") != CAPA_ID
        or record.get("status") != "VERIFIED"
        or record.get("all_six_verified") is not True
    ):
        raise EvidenceError("six-public-sites effectiveness receipt is not VERIFIED")
    verified_at = record.get("verified_at")
    parse_rfc3339_utc(
        "six-public-sites effectiveness timestamp",
        verified_at,
    )
    if record.get("method") != SITE_RECEIPT_METHOD:
        raise EvidenceError("six-public-sites effectiveness method is incomplete")
    check_nonclaims("six-public-sites effectiveness receipt", record.get("nonclaims"))

    bindings = record.get("artifact_bindings")
    if not isinstance(bindings, dict):
        raise EvidenceError("six-public-sites effectiveness receipt lacks artifact bindings")
    expected_bindings = {
        "r1_0_1_outer": by_tag["r1.0.1-2026-08-17"]["asset"],
        "r1_0_1_inner": INNER_FINAL,
        "generic_myth_v0_2_0": by_tag["generic-myth-v0.2.0"]["asset"],
        "full_canon_myth_v0_3_5": by_tag["myth-v0.3.5"]["asset"],
    }
    if set(bindings) != set(expected_bindings):
        raise EvidenceError("six-public-sites artifact-binding coverage mismatch")
    for key, expected in expected_bindings.items():
        observed = bindings.get(key)
        if not isinstance(observed, dict):
            raise EvidenceError(f"six-public-sites artifact binding is invalid: {key}")
        if set(observed) != {"filename", "bytes", "sha256"}:
            raise EvidenceError(f"six-public-sites artifact binding has extra fields: {key}")
        for field in ("filename", "bytes", "sha256"):
            if observed.get(field) != expected[field]:
                raise EvidenceError(
                    f"six-public-sites artifact binding mismatch: {key}.{field}"
                )

    sites = record.get("sites")
    if not isinstance(sites, list) or len(sites) != len(PUBLIC_SITE_REQUIREMENTS):
        raise EvidenceError("six-public-sites receipt does not contain exactly six sites")
    observed_ids: set[str] = set()
    for requirement, site in zip(PUBLIC_SITE_REQUIREMENTS, sites):
        if not isinstance(site, dict):
            raise EvidenceError("six-public-sites receipt contains an invalid site row")
        site_id = str(requirement["site_id"])
        if site.get("site_id") != site_id or site_id in observed_ids:
            raise EvidenceError("six-public-sites site order/identity mismatch")
        observed_ids.add(site_id)
        base_url = str(requirement["base_url"])
        if site.get("base_url") != base_url:
            raise EvidenceError(f"six-public-sites base URL mismatch: {site_id}")
        routes = site.get("routes")
        expected_routes = tuple(str(value) for value in requirement["routes"])
        if not isinstance(routes, list) or len(routes) != len(expected_routes):
            raise EvidenceError(f"six-public-sites route coverage mismatch: {site_id}")
        for expected_route, route in zip(expected_routes, routes):
            if not isinstance(route, dict):
                raise EvidenceError(f"invalid route observation: {site_id}")
            expected_url = exact_public_site_url(base_url, expected_route)
            expected_final = expected_site_final_url(requirement, expected_route)
            size = route.get("bytes_observed")
            digest = route.get("sha256_observed")
            if (
                route.get("path") != expected_route
                or route.get("url") != expected_url
                or route.get("final_url") != expected_final
                or route.get("http_status") != 200
                or route.get("content_type") != "text/html"
                or not isinstance(size, int)
                or isinstance(size, bool)
                or size <= 0
                or size > site_route_max_bytes(requirement, expected_route)
                or not isinstance(digest, str)
                or re.fullmatch(r"[0-9a-f]{64}", digest) is None
            ):
                raise EvidenceError(
                    f"six-public-sites route observation mismatch: {site_id}{expected_route}"
                )
        checks = site.get("semantic_checks")
        expected_checks = historical_required_site_checks_v1(requirement)
        if not isinstance(checks, dict) or set(checks) != set(expected_checks):
            raise EvidenceError(f"six-public-sites semantic-check coverage mismatch: {site_id}")
        failed = sorted(key for key, value in checks.items() if value is not True)
        if failed:
            raise EvidenceError(
                f"six-public-sites semantic checks are not all true for {site_id}: "
                + ", ".join(failed)
            )


def git_file_at_reachable_commit(commit: str, path: str) -> bytes:
    """Read one Git blob from a commit that is an ancestor of this checkout."""
    if re.fullmatch(r"[0-9a-f]{40}", commit) is None:
        raise EvidenceError("verifier repository commit is not a full Git object ID")
    object_type = subprocess.run(
        ["git", "cat-file", "-t", commit],
        cwd=ROOT,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        check=False,
    )
    if object_type.returncode != 0 or object_type.stdout.strip() != "commit":
        raise EvidenceError("verifier repository commit does not exist as a commit")
    reachable = subprocess.run(
        ["git", "merge-base", "--is-ancestor", commit, "HEAD"],
        cwd=ROOT,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    if reachable.returncode != 0:
        raise EvidenceError("verifier repository commit is not reachable from HEAD")
    completed = subprocess.run(
        ["git", "show", f"{commit}:{path}"],
        cwd=ROOT,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    if completed.returncode != 0:
        raise EvidenceError("verifier source is absent from the recorded commit")
    return completed.stdout


def validate_verifier_binding(verifier: Any) -> None:
    if (
        not isinstance(verifier, dict)
        or set(verifier)
        != {"path", "sha256", "repository_commit", "working_tree_clean"}
        or verifier.get("path") != VERIFIER_SOURCE_PATH
        or re.fullmatch(r"[0-9a-f]{64}", str(verifier.get("sha256"))) is None
        or verifier.get("working_tree_clean") is not True
    ):
        raise EvidenceError("six-public-sites verifier binding is incomplete")
    commit = str(verifier.get("repository_commit"))
    source = git_file_at_reachable_commit(commit, VERIFIER_SOURCE_PATH)
    if hashlib.sha256(source).hexdigest() != verifier.get("sha256"):
        raise EvidenceError("six-public-sites verifier source identity mismatch")


def validate_six_public_sites_effectiveness_v2(
    record: dict[str, Any],
    by_tag: dict[str, dict[str, Any]],
    *,
    response_pack: Path | None = None,
) -> tuple[datetime, ...]:
    """Replay the v2 receipt from retained bytes and recompute every semantic result."""
    if record.get("schema") != (
        "project-shadow.r1.0.1-six-public-sites-effectiveness-reverification.v2"
    ):
        raise EvidenceError("unsupported six-public-sites reverification schema")
    if (
        record.get("capa_id") != CAPA_ID
        or record.get("status") != "VERIFIED"
        or record.get("all_six_verified") is not True
        or record.get("method") != SITE_REVERIFICATION_RECEIPT_METHOD
    ):
        raise EvidenceError("six-public-sites reverification receipt is not VERIFIED")
    verified_time = parse_rfc3339_utc(
        "six-public-sites reverification timestamp",
        record.get("verified_at"),
    )
    check_nonclaims("six-public-sites reverification receipt", record.get("nonclaims"))

    validate_verifier_binding(record.get("verifier_binding"))

    observed_capa_state = record.get("observed_capa_state")
    if observed_capa_state != "IMPLEMENTED_PENDING_EFFECTIVENESS":
        raise EvidenceError(
            "closure-eligible six-public-sites receipt did not observe pending CAPA state"
        )

    expected_bindings = current_public_artifact_bindings(list(by_tag.values()))
    if record.get("artifact_bindings") != expected_bindings:
        raise EvidenceError("six-public-sites v2 artifact bindings mismatch")

    negative = record.get("negative_control_execution")
    replayed_negative = validate_public_semantic_negative_controls()
    if negative != replayed_negative:
        raise EvidenceError("six-public-sites negative-control execution mismatch")

    sites = record.get("sites")
    if not isinstance(sites, list) or len(sites) != len(PUBLIC_SITE_REQUIREMENTS):
        raise EvidenceError("six-public-sites v2 receipt does not contain exactly six sites")
    body_bindings: dict[str, dict[str, Any]] = {}
    recorded_total_expected = 0
    recorded_total_executed = 0
    recorded_total_passed = 0
    route_observation_times: list[datetime] = []
    for requirement, site in zip(PUBLIC_SITE_REQUIREMENTS, sites):
        if not isinstance(site, dict) or site.get("site_id") != requirement["site_id"]:
            raise EvidenceError("six-public-sites v2 site order/identity mismatch")
        if site.get("base_url") != requirement["base_url"]:
            raise EvidenceError(f"six-public-sites v2 base URL mismatch: {requirement['site_id']}")
        routes = site.get("routes")
        expected_routes = tuple(str(route) for route in requirement["routes"])
        if not isinstance(routes, list) or len(routes) != len(expected_routes):
            raise EvidenceError(f"six-public-sites v2 route coverage mismatch: {requirement['site_id']}")
        for expected_route, route in zip(expected_routes, routes):
            if not isinstance(route, dict):
                raise EvidenceError("six-public-sites v2 route row is invalid")
            body = route.get("response_body")
            expected_member = public_site_response_member(
                str(requirement["site_id"]),
                expected_route,
            )
            digest = route.get("sha256_observed")
            size = route.get("bytes_observed")
            if (
                route.get("path") != expected_route
                or route.get("url")
                != exact_public_site_url(str(requirement["base_url"]), expected_route)
                or route.get("final_url") != expected_site_final_url(requirement, expected_route)
                or route.get("http_status") != 200
                or route.get("content_type") != "text/html"
                or not isinstance(size, int)
                or isinstance(size, bool)
                or size <= 0
                or size > site_route_max_bytes(requirement, expected_route)
                or re.fullmatch(r"[0-9a-f]{64}", str(digest)) is None
                or not isinstance(body, dict)
                or body.get("pack_member") != expected_member
                or body.get("bytes") != size
                or body.get("sha256") != digest
                or body.get("encoding") != "utf-8"
            ):
                raise EvidenceError(
                    f"six-public-sites v2 route binding mismatch: {requirement['site_id']}{expected_route}"
                )
            observed_time = parse_rfc3339_utc(
                "six-public-sites v2 route timestamp",
                route.get("observed_at"),
            )
            if observed_time > verified_time:
                raise EvidenceError(
                    "six-public-sites route observation follows receipt verification"
                )
            route_observation_times.append(observed_time)
            if expected_member in body_bindings:
                raise EvidenceError("duplicate six-public-sites v2 response-body binding")
            body_bindings[expected_member] = body

        expected_checks = required_site_checks(requirement)
        checks = site.get("semantic_checks")
        execution = site.get("check_execution")
        if not isinstance(checks, dict) or not isinstance(execution, dict):
            raise EvidenceError("six-public-sites v2 semantic execution is missing")
        expected_execution = semantic_check_execution(expected_checks, checks)
        if execution != expected_execution:
            raise EvidenceError("six-public-sites v2 semantic execution accounting mismatch")
        require_complete_semantic_execution(
            f"six-public-sites v2 receipt for {requirement['site_id']}",
            expected_checks,
            checks,
        )
        recorded_total_expected += int(execution["expected_count"])
        recorded_total_executed += int(execution["executed_count"])
        recorded_total_passed += int(execution["passed_count"])

    pack_binding = record.get("response_evidence_pack")
    if (
        not isinstance(pack_binding, dict)
        or set(pack_binding) != {"filename", "bytes", "sha256", "format", "member_count"}
        or pack_binding.get("format") != "bounded-zip-v1"
        or pack_binding.get("filename") != SITE_RESPONSE_EVIDENCE_PACK_FILENAME
        or not isinstance(pack_binding.get("bytes"), int)
        or isinstance(pack_binding.get("bytes"), bool)
        or not 0 < int(pack_binding["bytes"]) <= MAX_SITE_EVIDENCE_EXPANDED_BYTES
        or re.fullmatch(r"[0-9a-f]{64}", str(pack_binding.get("sha256"))) is None
        or pack_binding.get("member_count") != len(body_bindings)
    ):
        raise EvidenceError("six-public-sites v2 response-evidence pack binding missing")
    if response_pack is None:
        response_pack = SIX_SITE_REVERIFICATION.parent / SITE_RESPONSE_EVIDENCE_PACK_FILENAME
    if response_pack.name != SITE_RESPONSE_EVIDENCE_PACK_FILENAME:
        raise EvidenceError("six-public-sites v2 response-evidence filename is unsafe")
    payload = read_bounded_regular_file(
        response_pack,
        limit=MAX_SITE_EVIDENCE_EXPANDED_BYTES,
        label="public-site response evidence pack",
    )
    if (
        len(payload) != pack_binding.get("bytes")
        or hashlib.sha256(payload).hexdigest() != pack_binding.get("sha256")
    ):
        raise EvidenceError("six-public-sites v2 response-evidence pack identity mismatch")
    bodies = load_public_site_response_pack(response_pack, body_bindings)

    for requirement, site in zip(PUBLIC_SITE_REQUIREMENTS, sites):
        pages = {
            str(route): bodies[
                public_site_response_member(str(requirement["site_id"]), str(route))
            ].decode("utf-8")
            for route in requirement["routes"]
        }
        replayed_checks = public_site_semantic_checks(
            requirement,
            pages,
            expected_capa_status=observed_capa_state,
        )
        if replayed_checks != site["semantic_checks"]:
            raise EvidenceError(
                f"six-public-sites v2 semantic replay mismatch: {requirement['site_id']}"
            )

    expected_total = {
        "expected_count": recorded_total_expected,
        "executed_count": recorded_total_executed,
        "passed_count": recorded_total_passed,
        "failed_check_ids": [],
        "skipped_check_ids": [],
        "unexpected_check_ids": [],
    }
    if record.get("check_execution") != expected_total:
        raise EvidenceError("six-public-sites v2 aggregate execution accounting mismatch")
    return tuple(route_observation_times)


def validate_capa_reopening_record(
    record: dict[str, Any],
    current_status: dict[str, Any],
    capa: dict[str, Any],
) -> datetime:
    """Validate the additive reopening without erasing the historical closure."""
    if record.get("schema") != "project-shadow.capa-effectiveness-reopening.v1":
        raise EvidenceError("unsupported CAPA effectiveness-reopening schema")
    if (
        record.get("capa_id") != CAPA_ID
        or record.get("current_status") != "IMPLEMENTED_PENDING_EFFECTIVENESS"
        or record.get("affected_effectiveness_criterion")
        != REOPENED_EFFECTIVENESS_CRITERION
    ):
        raise EvidenceError("CAPA effectiveness-reopening identity/state mismatch")
    reopened_time = parse_rfc3339_utc(
        "CAPA effectiveness-reopening timestamp",
        record.get("reopened_at"),
    )
    historical_closed_time = parse_rfc3339_utc(
        "historical CAPA closure timestamp",
        HISTORICAL_CAPA_CLOSURE_EVENT["closed_at"],
    )
    if reopened_time <= historical_closed_time:
        raise EvidenceError("CAPA reopening does not follow the historical closure")
    check_nonclaims("CAPA effectiveness-reopening record", record.get("nonclaims"))
    if record.get("reclosure_requirements") != list(RECLOSURE_REQUIREMENTS):
        raise EvidenceError("CAPA reclosure requirements were weakened or reordered")

    external = record.get("external_review")
    if not isinstance(external, dict) or external.get("pinned_repository_commit") != (
        "013334aebf200455f1e03c05a7574db1aa673575"
    ):
        raise EvidenceError("CAPA reopening does not bind the reproduced repository state")
    reproduced = record.get("reproduced_semantic_oracle_finding")
    expected_mutations = {
        "REVERSE_CURRENT",
        "DUAL_CURRENT",
        "CONTRADICTORY_CAPA",
        "SIDECAR_SEMANTICS_REVERSED",
        "IDENTITY_MISBINDING",
    }
    if (
        not isinstance(reproduced, dict)
        or reproduced.get("baseline_repository_tests") != "38/38_PASS"
        or set(reproduced.get("mutation_classes_reproduced", []))
        != expected_mutations
    ):
        raise EvidenceError("CAPA reopening does not bind the reproduced semantic finding")
    disposition = record.get("disposition")
    if not isinstance(disposition, dict) or any(
        disposition.get(key) is not expected
        for key, expected in {
            "artifact_identity_findings": False,
            "authorization_boundary_findings": False,
            "correction_implementation_remains_verified": True,
            "current_effectiveness_verified": False,
            "prior_closure_preserved_as_history": True,
            "r1_0_1_zero_myth_result_remains_verified": True,
        }.items()
    ):
        raise EvidenceError("CAPA reopening disposition is incomplete")
    prior = record.get("prior_closure")
    if prior != {
        "closed_at": HISTORICAL_CAPA_CLOSURE_EVENT["closed_at"],
        "verification_records": list(HISTORICAL_CAPA_EFFECTIVENESS_RECORDS),
    }:
        raise EvidenceError("CAPA reopening misstates the historical closure")

    history = capa.get("closure_history")
    if (
        capa.get("reopening_record") != CAPA_REOPENING_RECORD_PATH
        or not isinstance(history, list)
        or len(history) != 1
        or history[0].get("event") != HISTORICAL_CAPA_CLOSURE_EVENT
        or history[0].get("status") != "CLOSED_EFFECTIVE"
        or history[0].get("superseded_for_current_effectiveness_by")
        != CAPA_REOPENING_RECORD_PATH
    ):
        raise EvidenceError("CAPA current reopening/history representation mismatch")

    current_capa = current_status.get("capa")
    if not isinstance(current_capa, dict):
        raise EvidenceError("current status lacks reopened CAPA state")
    status_history = current_capa.get("closure_history")
    if (
        current_capa.get("id") != CAPA_ID
        or current_capa.get("reopening_record") != CAPA_REOPENING_RECORD_PATH
        or not isinstance(status_history, list)
        or len(status_history) != 1
        or status_history[0].get("closed_at")
        != HISTORICAL_CAPA_CLOSURE_EVENT["closed_at"]
        or status_history[0].get("verification_records")
        != list(HISTORICAL_CAPA_EFFECTIVENESS_RECORDS)
        or status_history[0].get("status") != "CLOSED_EFFECTIVE"
        or status_history[0].get("superseded_for_current_effectiveness_by")
        != CAPA_REOPENING_RECORD_PATH
        or CAPA_REOPENING_RECORD_PATH not in current_status.get("source_records", [])
    ):
        raise EvidenceError("derived current status misstates the CAPA reopening")

    capa_status = capa.get("status")
    if current_capa.get("status") != capa_status:
        raise EvidenceError("current status and CAPA lifecycle states disagree")
    if capa_status == "IMPLEMENTED_PENDING_EFFECTIVENESS":
        empty_closure = {
            "closed_at": None,
            "effectiveness_verified": False,
            "verification_record": None,
            "verification_records": [],
        }
        if (
            capa.get("closure") != empty_closure
            or capa.get("pending_effectiveness_criteria")
            != [REOPENED_EFFECTIVENESS_CRITERION]
            or current_capa.get("effectiveness_verified") is not False
            or current_capa.get("verification_records") != []
            or current_capa.get("pending_effectiveness_criteria")
            != [REOPENED_EFFECTIVENESS_CRITERION]
        ):
            raise EvidenceError("pending CAPA state misstates the reopened criterion")
    elif capa_status == "CLOSED_EFFECTIVE":
        closure = capa.get("closure")
        if (
            not isinstance(closure, dict)
            or closure.get("effectiveness_verified") is not True
            or closure.get("verification_record") != CURRENT_REDOWNLOAD_RECORD
            or closure.get("verification_records")
            != list(CURRENT_CAPA_EFFECTIVENESS_RECORDS)
            or capa.get("pending_effectiveness_criteria") != []
            or current_capa.get("effectiveness_verified") is not True
            or current_capa.get("verification_records")
            != list(CURRENT_CAPA_EFFECTIVENESS_RECORDS)
            or current_capa.get("pending_effectiveness_criteria") != []
        ):
            raise EvidenceError("closed CAPA state does not satisfy v2 reclosure shape")
        parse_rfc3339_utc("CAPA closure timestamp", closure.get("closed_at"))
    else:
        raise EvidenceError(f"unsupported reopened CAPA state: {capa_status!r}")
    return reopened_time


def validate_public_boundary_human_review(
    record: dict[str, Any],
    six_site_record: dict[str, Any],
    *,
    six_site_receipt_path: Path | None = None,
) -> datetime:
    """Require a retained human rendered-page review before CAPA reclosure."""
    if (
        record.get("schema") != "project-shadow.public-boundary-v2-human-review.v1"
        or record.get("capa_id") != CAPA_ID
        or record.get("status") != "APPROVED_FOR_RECLOSURE"
        or record.get("human_reviewer") is not True
        or record.get("semantic_contract") != PUBLIC_BOUNDARY_CONTRACT
    ):
        raise EvidenceError("public-boundary human-review identity/state mismatch")
    reviewed_time = parse_rfc3339_utc(
        "public-boundary human-review timestamp",
        record.get("reviewed_at"),
    )
    check_nonclaims("public-boundary human-review record", record.get("nonclaims"))
    reviewer = record.get("reviewer")
    if (
        not isinstance(reviewer, dict)
        or set(reviewer) != {"identity", "reviewer_type", "attestation"}
        or not isinstance(reviewer.get("identity"), str)
        or not reviewer["identity"].strip()
        or reviewer.get("reviewer_type") != "HUMAN"
        or reviewer.get("attestation") != PUBLIC_BOUNDARY_HUMAN_REVIEW_ATTESTATION
    ):
        raise EvidenceError("public-boundary human-review attestation is incomplete")

    if six_site_receipt_path is None:
        six_site_receipt_path = SIX_SITE_REVERIFICATION
    receipt_payload = read_bounded_regular_file(
        six_site_receipt_path,
        limit=4 * 1024 * 1024,
        label="six-public-sites v2 receipt",
    )
    pack = six_site_record.get("response_evidence_pack")
    expected_binding = {
        "record": SIX_SITE_REVERIFICATION_RECORD,
        "sha256": hashlib.sha256(receipt_payload).hexdigest(),
        "verified_at": six_site_record.get("verified_at"),
        "response_evidence_pack": {
            "filename": pack.get("filename") if isinstance(pack, dict) else None,
            "sha256": pack.get("sha256") if isinstance(pack, dict) else None,
        },
    }
    if record.get("six_site_reverification") != expected_binding:
        raise EvidenceError("human review does not bind the exact v2 receipt and response pack")

    sites = record.get("sites")
    expected_sites = [
        {
            "site_id": requirement["site_id"],
            "base_url": requirement["base_url"],
            "routes_reviewed": list(requirement["routes"]),
            "browser_rendered_visible": True,
            "visible_meaning_confirmed": True,
        }
        for requirement in PUBLIC_SITE_REQUIREMENTS
    ]
    if sites != expected_sites:
        raise EvidenceError("human review does not cover all six rendered public sites")
    if record.get("determinations") != PUBLIC_BOUNDARY_HUMAN_REVIEW_DETERMINATIONS:
        raise EvidenceError("human-review relation/binding determinations are incomplete")
    return reviewed_time


def validate_reclosure_causality(
    reopened_time: datetime,
    six_site_time: datetime,
    human_review_time: datetime,
    closed_time: datetime,
    route_observation_times: tuple[datetime, ...] = (),
) -> None:
    routes_are_causal = bool(route_observation_times) and all(
        reopened_time < observed_time <= six_site_time
        for observed_time in route_observation_times
    )
    if (
        not routes_are_causal
        or not reopened_time < six_site_time <= human_review_time <= closed_time
    ):
        raise EvidenceError(
            "CAPA causality must be historical closure < reopening < every route "
            "observation <= v2 verification <= human review <= reclosure"
        )


def validate_capa_effectiveness_record_pointers(
    current_status: dict[str, Any],
    capa: dict[str, Any],
) -> None:
    closure = capa.get("closure")
    current_capa = current_status.get("capa")
    if not isinstance(closure, dict) or not isinstance(current_capa, dict):
        raise EvidenceError("current status/CAPA closure object missing")
    expected = list(CURRENT_CAPA_EFFECTIVENESS_RECORDS)
    if (
        closure.get("verification_record") != CURRENT_REDOWNLOAD_RECORD
        or closure.get("verification_records") != expected
        or current_capa.get("verification_records") != expected
        or not all(
            record in current_status.get("source_records", []) for record in expected
        )
    ):
        raise EvidenceError(
            "CAPA closure must bind redownload, v2 site, and human-review records"
        )


def verify_repository_metadata(phase: str = "POSTPUBLICATION") -> list[dict[str, Any]]:
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
    capa_reopening = require_object(
        load_json(CAPA_REOPENING_RECORD),
        CAPA_REOPENING_RECORD.name,
    )

    if manifest.get("schema") != "project-shadow.publication-manifest.v2":
        raise EvidenceError("unsupported publication manifest schema")
    if current_status.get("schema") != "project-shadow.current-release-status.v1":
        raise EvidenceError("unsupported current release-status schema")
    if capa.get("schema") != "project-shadow.capa.v1":
        raise EvidenceError("unsupported CAPA schema")
    reopened_time = validate_capa_reopening_record(
        capa_reopening,
        current_status,
        capa,
    )
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
        note_markers = identity_markers if tag == "generic-myth-v0.2.0" else (tag,) + identity_markers
        for expected in note_markers:
            if expected not in note:
                raise EvidenceError(f"release notes for {tag} omit {expected!r}")
        if tag != "generic-myth-v0.2.0" and not note.lstrip().startswith("**"):
            raise EvidenceError(f"release notes for {tag} lack a bold first-line warning")
        if tag == "myth-v0.3.5":
            source_warning_present = (
                "automatically generated source archive" in note
                and "repackaged copy" in note
            )
        elif tag == "r1.0.1-2026-08-17":
            source_warning_present = (
                "automatically generated source ZIP and TAR archives" in note
                and "repository snapshots" in note
            )
        elif tag != "generic-myth-v0.2.0":
            source_warning_present = (
                "automatically generated" in note and "Source code (zip)" in note
            )
        else:
            source_warning_present = True
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
        current_capa = current_status.get("capa", {})
        closure = capa.get("closure", {})
        capa_status = current_capa.get("status")
        if (
            manifest.get("current_reference")
            != {
                "publication_state": "PUBLISHED",
                "tag": "r1.0.1-2026-08-17",
            }
            or current_status.get("publication_phase") != "POSTPUBLICATION"
            or current_status.get("generic_myth", {}).get("publication_state")
            != "PUBLISHED"
            or current_status.get("current_reference", {}).get("publication_state")
            != "PUBLISHED"
            or capa_status != capa.get("status")
        ):
            raise EvidenceError("current status/CAPA postpublication state mismatch")
        if capa_status == "IMPLEMENTED_PENDING_EFFECTIVENESS":
            if (
                manifest.get("postpublication_state")
                != "PUBLISHED_PENDING_EFFECTIVENESS"
                or current_capa.get("effectiveness_verified") is not False
                or current_capa.get("verification_records") != []
                or closure.get("effectiveness_verified") is not False
                or closure.get("closed_at") is not None
                or closure.get("verification_record") is not None
                or closure.get("verification_records") != []
            ):
                raise EvidenceError(
                    "pending-effectiveness postpublication state is inconsistent"
                )
            historical_redownload = require_object(
                load_json(CURRENT_REDOWNLOAD),
                CURRENT_REDOWNLOAD.name,
            )
            historical_six_site = require_object(
                load_json(SIX_SITE_EFFECTIVENESS),
                SIX_SITE_EFFECTIVENESS.name,
            )
            validate_current_redownload(historical_redownload, by_tag)
            validate_six_public_sites_effectiveness(historical_six_site, by_tag)
        elif capa_status == "CLOSED_EFFECTIVE":
            closed_at = closure.get("closed_at")
            if (
                manifest.get("postpublication_state")
                != "PUBLISHED_EFFECTIVENESS_VERIFIED"
                or current_capa.get("effectiveness_verified") is not True
                or closure.get("effectiveness_verified") is not True
            ):
                raise EvidenceError("current status/CAPA postpublication closure mismatch")
            closed_time = parse_rfc3339_utc("CAPA closure timestamp", closed_at)
            validate_capa_effectiveness_record_pointers(current_status, capa)
            redownload_record = require_object(
                load_json(CURRENT_REDOWNLOAD),
                CURRENT_REDOWNLOAD.name,
            )
            six_site_record = require_object(
                load_json(SIX_SITE_REVERIFICATION),
                SIX_SITE_REVERIFICATION.name,
            )
            human_review_record = require_object(
                load_json(PUBLIC_BOUNDARY_HUMAN_REVIEW),
                PUBLIC_BOUNDARY_HUMAN_REVIEW.name,
            )
            validate_current_redownload(redownload_record, by_tag)
            route_observation_times = validate_six_public_sites_effectiveness_v2(
                six_site_record,
                by_tag,
            )
            six_site_time = parse_rfc3339_utc(
                "six-public-sites effectiveness timestamp",
                six_site_record.get("verified_at"),
            )
            human_review_time = validate_public_boundary_human_review(
                human_review_record,
                six_site_record,
            )
            validate_reclosure_causality(
                reopened_time,
                six_site_time,
                human_review_time,
                closed_time,
                route_observation_times,
            )
        else:
            raise EvidenceError(f"unsupported postpublication CAPA state: {capa_status!r}")

    validate_public_semantic_negative_controls()
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
    headers = {
        "Accept-Encoding": "identity",
        "User-Agent": USER_AGENT,
    }
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


def public_download_provider(url: str) -> str | None:
    hostname = (urllib.parse.urlparse(url).hostname or "").lower()
    if hostname == "github.com":
        return "GITHUB"
    if hostname == "huggingface.co":
        return "HUGGING_FACE"
    return None


def validate_public_download_final_host(
    provider: str,
    final_url: str,
) -> str:
    parsed = urllib.parse.urlparse(final_url)
    hostname = (parsed.hostname or "").lower()
    allowed = hostname in PUBLIC_DOWNLOAD_FINAL_HOSTS[provider]
    try:
        port = parsed.port
    except ValueError as exc:
        raise EvidenceError(
            f"unexpected {provider} public-download final host: {final_url}"
        ) from exc
    if parsed.scheme != "https" or port not in (None, 443) or not allowed:
        raise EvidenceError(
            f"unexpected {provider} public-download final host: {final_url}"
        )
    return hostname


def download_and_hash(asset: dict[str, Any], destination: Path) -> Path:
    destination.mkdir(parents=True, exist_ok=True)
    output = destination / asset["filename"]
    if output.exists() or output.is_symlink():
        raise EvidenceError(f"refusing to overwrite release download: {output}")
    digest = hashlib.sha256()
    count = 0
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            dir=destination,
            prefix=f".{asset['filename']}.",
            delete=False,
        ) as handle:
            temporary = Path(handle.name)
            with request(asset["download_url"]) as response:
                if getattr(response, "status", None) != 200:
                    raise EvidenceError(
                        f"unexpected public-download status for {asset['filename']}"
                    )
                provider = public_download_provider(str(asset["download_url"]))
                if provider is not None:
                    validate_public_download_final_host(provider, response.geturl())
                header = response.headers.get("Content-Length")
                if header is not None:
                    try:
                        advertised = int(header)
                    except ValueError as exc:
                        raise EvidenceError(
                            f"invalid Content-Length for {asset['filename']}"
                        ) from exc
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
                        raise EvidenceError(
                            f"oversized release download: {asset['filename']}"
                        )
                    digest.update(block)
                    handle.write(block)
            handle.flush()
            os.fsync(handle.fileno())
        os.link(temporary, output)
        temporary.unlink()
        temporary = None
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    if count != asset["bytes"] or digest.hexdigest() != asset["sha256"]:
        raise EvidenceError(
            f"release download identity mismatch for {asset['filename']}: "
            f"bytes={count}; sha256={digest.hexdigest()}"
        )
    return output


def download_and_hash_at_url(
    asset: dict[str, Any],
    download_url: str,
    destination: Path,
) -> Path:
    """Download one exact asset identity from an explicitly selected mirror."""
    mirrored = dict(asset)
    mirrored["download_url"] = download_url
    return download_and_hash(mirrored, destination)


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
    normalized = value.replace("\r\n", "\n").replace("\r", "\n")
    return "\n".join(line.rstrip() for line in normalized.splitlines()).rstrip()


def expected_live_release_body(tag: str, capa_status: str | None = None) -> str:
    """Return the exact allowed live body without mutating its frozen release note."""
    note = RELEASE_NOTES[tag].read_text(encoding="utf-8")
    preamble = POSTPUBLICATION_RELEASE_PREAMBLES.get(tag, "")
    if not preamble:
        return note
    if capa_status is None:
        current_status = require_object(load_json(CURRENT_STATUS), CURRENT_STATUS.name)
        capa_status = current_status.get("capa", {}).get("status")
    state_preamble = POSTPUBLICATION_CURRENT_STATE_PREAMBLES.get(str(capa_status))
    if state_preamble is None:
        raise EvidenceError(f"unsupported live-release CAPA state: {capa_status!r}")
    return preamble.replace(
        POSTPUBLICATION_REOPENING_PREAMBLE,
        POSTPUBLICATION_REOPENING_PREAMBLE + state_preamble,
        1,
    ) + note


def verify_live_release_metadata(
    rows: list[dict[str, Any]],
    expected_latest_tag: str,
    *,
    capa_status: str | None = None,
) -> None:
    repository = "PauseBeforeHarmProtocol/Project-Shadow"
    for row in rows:
        tag = row["tag"]
        release = fetch_public_json(
            f"https://api.github.com/repos/{repository}/releases/tags/{tag}"
        )
        note = expected_live_release_body(tag, capa_status)
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


def fetch_public_site_route(
    requirement: dict[str, Any],
    route: str,
) -> tuple[str, dict[str, Any], bytes]:
    url = exact_public_site_url(str(requirement["base_url"]), route)
    expected_final = expected_site_final_url(requirement, route)
    limit = site_route_max_bytes(requirement, route)
    with request(url) as response:
        status = getattr(response, "status", None)
        final_url = response.geturl()
        content_type = response.headers.get_content_type()
        requested = urllib.parse.urlparse(url)
        final = urllib.parse.urlparse(final_url)
        if status != 200:
            raise EvidenceError(f"unexpected HTTP {status} for {url}")
        if (
            final.scheme != requested.scheme
            or final.netloc != requested.netloc
            or final_url != expected_final
        ):
            raise EvidenceError(f"public page final URL mismatch: {url} -> {final_url}")
        body = bytearray()
        digest = hashlib.sha256()
        while True:
            block = response.read(min(1024 * 1024, limit + 1 - len(body)))
            if not block:
                break
            body.extend(block)
            digest.update(block)
            if len(body) > limit:
                raise EvidenceError(f"public page exceeds bounded size {limit}: {url}")
    if content_type != "text/html":
        raise EvidenceError(f"public page content type is not text/html: {url}")
    try:
        response_body = bytes(body)
        source = response_body.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise EvidenceError(f"public page is not UTF-8: {url}") from exc
    observed_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace(
        "+00:00",
        "Z",
    )
    return source, {
        "path": route,
        "url": url,
        "final_url": final_url,
        "http_status": status,
        "bytes_observed": len(body),
        "sha256_observed": digest.hexdigest(),
        "content_type": content_type,
        "observed_at": observed_at,
    }, response_body


def public_site_response_member(site_id: str, route: str) -> str:
    if not route.startswith("/") or route.startswith("//"):
        raise EvidenceError(f"unsafe response-evidence route: {route!r}")
    relative = route.lstrip("/") or "root.html"
    pure = PurePosixPath(relative)
    if pure.is_absolute() or ".." in pure.parts:
        raise EvidenceError(f"unsafe response-evidence route: {route!r}")
    if pure.suffix == "":
        pure = pure / "index.html"
    return (PurePosixPath("responses") / site_id / pure).as_posix()


def build_public_site_response_pack(
    captures: list[tuple[str, bytes]],
    destination: Path,
) -> dict[str, Any]:
    expected_count = MAX_SITE_EVIDENCE_PACK_MEMBERS
    if len(captures) != expected_count or len({name for name, _ in captures}) != expected_count:
        raise EvidenceError("public-site response capture coverage mismatch")
    buffer = io.BytesIO()
    with zipfile.ZipFile(
        buffer,
        mode="w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=9,
    ) as archive:
        for member, body in sorted(captures):
            pure = PurePosixPath(member)
            if pure.is_absolute() or ".." in pure.parts or not member.startswith("responses/"):
                raise EvidenceError(f"unsafe response-evidence member: {member!r}")
            info = zipfile.ZipInfo(member, date_time=(1980, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, body)
    payload = buffer.getvalue()
    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        with destination.open("xb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
    except FileExistsError as exc:
        raise EvidenceError(f"refusing to overwrite response evidence: {destination}") from exc
    return {
        "filename": destination.name,
        "bytes": len(payload),
        "sha256": hashlib.sha256(payload).hexdigest(),
        "format": "bounded-zip-v1",
        "member_count": len(captures),
    }


def read_bounded_regular_file(path: Path, *, limit: int, label: str) -> bytes:
    try:
        metadata = path.lstat()
    except OSError as exc:
        raise EvidenceError(f"{label} is unavailable: {path}") from exc
    if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISREG(metadata.st_mode):
        raise EvidenceError(f"{label} is not a regular non-symlink file")
    if metadata.st_size <= 0 or metadata.st_size > limit:
        raise EvidenceError(f"{label} is unexpectedly large or empty")
    try:
        return path.read_bytes()
    except OSError as exc:
        raise EvidenceError(f"{label} could not be read") from exc


def load_public_site_response_pack(
    path: Path,
    expected: dict[str, dict[str, Any]],
) -> dict[str, bytes]:
    payload = read_bounded_regular_file(
        path,
        limit=MAX_SITE_EVIDENCE_EXPANDED_BYTES,
        label="public-site response evidence pack",
    )
    bodies: dict[str, bytes] = {}
    try:
        with zipfile.ZipFile(io.BytesIO(payload), "r") as archive:
            infos = archive.infolist()
            if len(infos) != len(expected) or len(infos) > MAX_SITE_EVIDENCE_PACK_MEMBERS:
                raise EvidenceError("public-site response evidence member-count mismatch")
            names = [info.filename for info in infos]
            if len(set(names)) != len(names) or set(names) != set(expected):
                raise EvidenceError("public-site response evidence inventory mismatch")
            expanded = 0
            for info in infos:
                pure = PurePosixPath(info.filename)
                mode = (info.external_attr >> 16) & 0o170000
                if (
                    info.is_dir()
                    or pure.is_absolute()
                    or ".." in pure.parts
                    or not info.filename.startswith("responses/")
                    or mode == 0o120000
                ):
                    raise EvidenceError(
                        f"unsafe public-site response evidence member: {info.filename!r}"
                    )
                expanded += info.file_size
                if expanded > MAX_SITE_EVIDENCE_EXPANDED_BYTES:
                    raise EvidenceError("public-site response evidence expansion exceeds limit")
                if info.file_size and (
                    info.compress_size == 0 or info.file_size / info.compress_size > 200
                ):
                    raise EvidenceError(
                        f"public-site response evidence compression ratio exceeds limit: {info.filename}"
                    )
                body = archive.read(info)
                binding = expected[info.filename]
                if (
                    len(body) != binding.get("bytes")
                    or hashlib.sha256(body).hexdigest() != binding.get("sha256")
                    or binding.get("encoding") != "utf-8"
                ):
                    raise EvidenceError(
                        f"public-site response evidence binding mismatch: {info.filename}"
                    )
                try:
                    body.decode("utf-8")
                except UnicodeDecodeError as exc:
                    raise EvidenceError(
                        f"public-site response evidence is not UTF-8: {info.filename}"
                    ) from exc
                bodies[info.filename] = body
    except EvidenceError:
        raise
    except (
        zipfile.BadZipFile,
        zipfile.LargeZipFile,
        NotImplementedError,
        RuntimeError,
        OSError,
    ) as exc:
        raise EvidenceError("public-site response evidence pack is not a valid ZIP") from exc
    return bodies


class PublicHTMLView(HTMLParser):
    """Extract non-hidden source text and fail closed on ambiguous semantic markup."""

    HIDDEN_TAGS = frozenset({"script", "style", "template", "noscript"})
    VOID_TAGS = frozenset(
        {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}
    )

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.depth = 0
        self.hidden_stack: list[bool] = [False]
        self.tag_stack: list[str] = []
        self.valid = True
        self.text_chunks: list[str] = []
        self.hrefs: list[str] = []
        self.regions: list[dict[str, Any]] = []
        self.active_regions: list[dict[str, Any]] = []
        self.next_region_id = 1

    def normalized_attrs(
        self,
        attrs: list[tuple[str, str | None]],
    ) -> dict[str, str | None]:
        normalized: dict[str, str | None] = {}
        for name, value in attrs:
            lowered = name.lower()
            if lowered in normalized:
                self.valid = False
            normalized[lowered] = (
                html.unescape(value) if isinstance(value, str) else None
            )
        return normalized

    @classmethod
    def attrs_are_hidden(cls, tag: str, attrs: dict[str, str | None]) -> bool:
        style = attrs.get("style") or ""
        return (
            tag in cls.HIDDEN_TAGS
            or "hidden" in attrs
            or "inert" in attrs
            or (tag == "details" and "open" not in attrs)
            or (attrs.get("aria-hidden") or "").lower() == "true"
            or re.search(
                r"(?:^|;)\s*(?:display\s*:\s*none|visibility\s*:\s*hidden|"
                r"opacity\s*:\s*0(?:\.0*)?|content-visibility\s*:\s*hidden)\b",
                style,
                re.IGNORECASE,
            )
            is not None
        )

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        lowered = tag.lower()
        attributes = self.normalized_attrs(attrs)
        hidden = self.hidden_stack[-1] or self.attrs_are_hidden(lowered, attributes)
        self.depth += 1
        self.hidden_stack.append(hidden)
        if lowered not in self.VOID_TAGS:
            self.tag_stack.append(lowered)
        if hidden:
            if lowered in self.VOID_TAGS:
                self.finish_current_depth()
            return
        href = attributes.get("href") if lowered == "a" else None
        if isinstance(href, str):
            self.hrefs.append(href)
            for region in self.active_regions:
                region["hrefs"].append(href)
        classes = set((attributes.get("class") or "").split())
        if (
            "public-release-band" in classes
            or any(name.startswith("data-shadow-") for name in attributes)
        ):
            parent_region_id = (
                self.active_regions[-1]["region_id"] if self.active_regions else None
            )
            region_id = self.next_region_id
            self.next_region_id += 1
            self.active_regions.append(
                {
                    "region_id": region_id,
                    "parent_region_id": parent_region_id,
                    "tag": lowered,
                    "attrs": attributes,
                    "chunks": [],
                    "hrefs": [href] if isinstance(href, str) else [],
                    "depth": self.depth,
                }
            )
        if lowered in self.VOID_TAGS:
            self.finish_current_depth()

    def finish_current_depth(self) -> None:
        if self.depth <= 0:
            return
        finalized: list[dict[str, Any]] = []
        remaining: list[dict[str, Any]] = []
        for region in self.active_regions:
            if region["depth"] == self.depth:
                finalized.append(region)
            else:
                remaining.append(region)
        self.active_regions = remaining
        for region in finalized:
            self.regions.append(
                {
                    "region_id": region["region_id"],
                    "parent_region_id": region["parent_region_id"],
                    "tag": region["tag"],
                    "attrs": region["attrs"],
                    "text": re.sub(r"\s+", " ", " ".join(region["chunks"])).strip(),
                    "hrefs": tuple(region["hrefs"]),
                }
            )
        self.hidden_stack.pop()
        self.depth -= 1

    def handle_endtag(self, tag: str) -> None:
        lowered = tag.lower()
        if not self.tag_stack or self.tag_stack[-1] != lowered:
            self.valid = False
            return
        self.finish_current_depth()
        self.tag_stack.pop()

    def handle_startendtag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        self.handle_starttag(tag, attrs)
        lowered = tag.lower()
        if lowered not in self.VOID_TAGS:
            self.handle_endtag(lowered)

    def handle_data(self, data: str) -> None:
        if not self.hidden_stack[-1]:
            self.text_chunks.append(data)
            for region in self.active_regions:
                region["chunks"].append(data)

    def close(self) -> None:
        super().close()
        if self.tag_stack or self.depth != 0 or len(self.hidden_stack) != 1:
            self.valid = False


def public_html_evidence(source: str) -> PublicHTMLView:
    parser = PublicHTMLView()
    parser.feed(source)
    parser.close()
    return parser


def public_html_view(source: str) -> tuple[str, tuple[str, ...]]:
    parser = public_html_evidence(source)
    text = re.sub(r"\s+", " ", " ".join(parser.text_chunks)).strip()
    return text, tuple(parser.hrefs)


def normalized_public_text(source: str) -> str:
    return public_html_view(source)[0]


def public_region_classes(region: dict[str, Any]) -> set[str]:
    attrs = region.get("attrs", {})
    value = attrs.get("class") if isinstance(attrs, dict) else None
    return set(value.split()) if isinstance(value, str) else set()


def public_boundary_band(
    source: str,
) -> tuple[dict[str, Any] | None, bool, bool]:
    evidence = public_html_evidence(source)
    bands = [
        region
        for region in evidence.regions
        if "public-release-band" in public_region_classes(region)
    ]
    if not evidence.valid or len(bands) != 1:
        return None, False, False
    band = bands[0]
    attrs = band["attrs"]
    contract = all(
        attrs.get(name) == value
        for name, value in PUBLIC_BOUNDARY_BAND_ATTRIBUTES.items()
    )
    claim_regions = [
        region
        for region in evidence.regions
        if "data-shadow-claim" in region["attrs"]
    ]
    expected_claims = [
        region
        for region in claim_regions
        if region.get("parent_region_id") == band.get("region_id")
        and region["attrs"].get("data-shadow-claim") in PUBLIC_BOUNDARY_CLAIMS
    ]
    visible_claims = (
        len(claim_regions) == len(PUBLIC_BOUNDARY_CLAIMS)
        and len(expected_claims) == len(PUBLIC_BOUNDARY_CLAIMS)
        and all(
            len(
                [
                    region
                    for region in expected_claims
                    if region["attrs"].get("data-shadow-claim") == claim_id
                    and region["text"] == claim_text
                ]
            )
            == 1
            for claim_id, claim_text in PUBLIC_BOUNDARY_CLAIMS.items()
        )
    )
    return band, contract, visible_claims


def public_shadow_semantic_markup_is_closed(
    requirement: dict[str, Any],
    route_evidence: dict[str, PublicHTMLView],
) -> bool:
    """Reject every unrecognized or ambiguously placed data-shadow marker."""
    expected_artifacts = {
        str(PUBLIC_ARTIFACT_BINDINGS[name]["artifact_id"]): PUBLIC_ARTIFACT_BINDINGS[name]
        for name in requirement["specific_checks"]
        if name in PUBLIC_ARTIFACT_BINDINGS
    }
    expected_capa_count = (
        1
        if {"capa_id", "capa_state"}.intersection(requirement["specific_checks"])
        else 0
    )
    band_keys = set(PUBLIC_BOUNDARY_BAND_ATTRIBUTES)
    band_ids: list[tuple[str, int]] = []
    claim_rows: list[tuple[tuple[str, int] | None, str, str]] = []
    capa_ids: list[tuple[str, int]] = []
    capa_children: list[tuple[tuple[str, int] | None, str]] = []
    artifact_ids: list[str] = []
    identity_ids: list[str] = []

    for route, evidence in route_evidence.items():
        if not evidence.valid:
            return False
        regions = {
            int(region["region_id"]): region
            for region in evidence.regions
        }
        for region in evidence.regions:
            attrs = region["attrs"]
            shadow = {
                name: value
                for name, value in attrs.items()
                if name.startswith("data-shadow-")
            }
            if not shadow:
                continue
            keys = set(shadow)
            region_key = (route, int(region["region_id"]))
            parent_id = region.get("parent_region_id")
            parent_key = (
                (route, int(parent_id))
                if isinstance(parent_id, int) and parent_id in regions
                else None
            )

            if keys == band_keys:
                if (
                    parent_key is not None
                    or "public-release-band" not in public_region_classes(region)
                    or any(
                        shadow.get(name) != value
                        for name, value in PUBLIC_BOUNDARY_BAND_ATTRIBUTES.items()
                    )
                ):
                    return False
                band_ids.append(region_key)
                continue

            if keys == {"data-shadow-claim"}:
                claim_id = shadow.get("data-shadow-claim")
                if claim_id not in PUBLIC_BOUNDARY_CLAIMS:
                    return False
                claim_rows.append((parent_key, str(claim_id), str(region["text"])))
                continue

            if keys == {"data-shadow-capa-id", "data-shadow-capa-state"}:
                if (
                    parent_key is not None
                    or shadow.get("data-shadow-capa-id") != CAPA_ID
                    or shadow.get("data-shadow-capa-state")
                    not in POSTPUBLICATION_CURRENT_STATE_PREAMBLES
                ):
                    return False
                capa_ids.append(region_key)
                continue

            if keys == {"data-shadow-capa-declaration"}:
                if shadow.get("data-shadow-capa-declaration") != "current-state":
                    return False
                capa_children.append((parent_key, "current-state"))
                continue

            artifact_id = shadow.get("data-shadow-artifact-id")
            if isinstance(artifact_id, str) and artifact_id in expected_artifacts:
                spec = expected_artifacts[artifact_id]
                expected_keys = {
                    "data-shadow-artifact-id",
                    "data-shadow-filename",
                    "data-shadow-sha256",
                    (
                        "data-shadow-bytes"
                        if "bytes" in spec
                        else "data-shadow-member-count"
                    ),
                }
                if keys != expected_keys or parent_key is not None:
                    return False
                artifact_ids.append(artifact_id)
                continue

            identity_id = shadow.get("data-shadow-artifact-identity-for")
            if keys == {"data-shadow-artifact-identity-for"} and isinstance(
                identity_id,
                str,
            ):
                if identity_id not in expected_artifacts or parent_key is None:
                    return False
                parent = regions[parent_key[1]]
                if parent["attrs"].get("data-shadow-artifact-id") != identity_id:
                    return False
                identity_ids.append(identity_id)
                continue

            return False

    expected_artifact_ids = set(expected_artifacts)
    band_counts_by_route = {
        route: sum(1 for band_route, _region_id in band_ids if band_route == route)
        for route in route_evidence
    }
    if (
        band_counts_by_route.get("/") != 1
        or any(count > 1 for count in band_counts_by_route.values())
        or (
            "archived_manual_current_boundary" in requirement["specific_checks"]
            and band_counts_by_route.get("/manual.html") != 1
        )
        or len(set(band_ids)) != len(band_ids)
        or len(claim_rows) != len(band_ids) * len(PUBLIC_BOUNDARY_CLAIMS)
        or any(
            sum(
                1
                for parent, value, claim_text in claim_rows
                if parent == band_id
                and value == claim_id
                and claim_text == PUBLIC_BOUNDARY_CLAIMS[claim_id]
            )
            != 1
            for band_id in band_ids
            for claim_id in PUBLIC_BOUNDARY_CLAIMS
        )
        or len(capa_ids) != expected_capa_count
        or len(capa_children) != expected_capa_count
        or any(
            sum(1 for parent, value in capa_children if parent == capa_id and value == "current-state")
            != 1
            for capa_id in capa_ids
        )
        or len(artifact_ids) != len(expected_artifact_ids)
        or set(artifact_ids) != expected_artifact_ids
        or len(identity_ids) != len(expected_artifact_ids)
        or set(identity_ids) != expected_artifact_ids
    ):
        return False
    return True


def public_boundary_has_contradiction(text: str) -> bool:
    negation_patterns = (
        r"\b(?:false|untrue|incorrect)\s+that\s+(?:project\s+shadow\s+)?r?1\.0\.1\b[^.!?]{0,120}\bcurrent\b",
        r"\b(?:false|untrue|incorrect)\s+that\s+project\s+shadow\s+1\.0\.1\s+contains\s+no\s+myth\s+package\b",
    )
    if any(
        re.search(pattern, text, re.IGNORECASE) is not None
        for pattern in negation_patterns
    ):
        return True
    residual = text.replace(PUBLIC_BOUNDARY_CURRENT_CLAIM, " ").replace(
        PUBLIC_BOUNDARY_SHARED_CLAIM,
        " ",
    )
    direct_patterns = (
        r"\b(?:project\s+shadow\s+)?r?1\.0\.1\b[^.!?]{0,120}\b(?:is|was|remains?|has\s+been)\s+(?:(?:not\s+)?the\s+)?(?:superseded|historical|not\s+(?:the\s+)?current(?:\s+release)?)\b",
        r"\b(?:august\s+14\s+r1|r1-2026-08-14)\b[^.!?]{0,120}\b(?:is|was|remains?)\s+(?:(?:also|still)\s+)?(?:the\s+)?current\b",
        r"\bnot\s+(?:separate|optional|default[- ]off|non[- ]?authorizing)\b",
    )
    if any(
        re.search(pattern, residual, re.IGNORECASE) is not None
        for pattern in direct_patterns
    ):
        return True
    affirmative_patterns = (
        r"\b(?:sidecars?|companions?|generic\s+myth\s+v0\.2\.0|full[- ]canon\s+myth\s+v0\.3\.5)\b[^.!?]{0,120}\b(?:are|is|become|remain)\s+(?:mandatory|required|authorizing|default[- ]on)\b",
        r"\b(?:sidecars?|companions?)\b[^.!?]{0,120}\bcan\s+authorize\b",
        r"\b(?:sidecars?|companions?)\b[^.!?]{0,120}\bmust\s+be\s+(?:enabled\s+by\s+default|default[- ]on|required|mandatory|authorizing)\b",
    )
    for pattern in affirmative_patterns:
        for match in re.finditer(pattern, residual, re.IGNORECASE):
            context = residual[max(0, match.start() - 24):match.end()]
            if re.search(r"\b(?:neither|not|never|no)\b", context, re.IGNORECASE):
                continue
            return True
    return False


def expected_capa_visible_statement(status: str) -> str:
    if status == "IMPLEMENTED_PENDING_EFFECTIVENESS":
        return (
            f"CAPA {CAPA_ID} current state: "
            "IMPLEMENTED_PENDING_EFFECTIVENESS."
        )
    if status == "CLOSED_EFFECTIVE":
        return f"CAPA {CAPA_ID} current state: CLOSED_EFFECTIVE."
    raise EvidenceError(f"unsupported public CAPA state: {status!r}")


def public_capa_state_check(pages: dict[str, str], expected_status: str) -> bool:
    declarations: list[dict[str, Any]] = []
    declaration_children: list[dict[str, Any]] = []
    visible_texts: list[str] = []
    for source in pages.values():
        evidence = public_html_evidence(source)
        if not evidence.valid:
            return False
        visible_texts.append(
            re.sub(r"\s+", " ", " ".join(evidence.text_chunks)).strip()
        )
        for region in evidence.regions:
            attrs = region["attrs"]
            if "data-shadow-capa-id" in attrs or "data-shadow-capa-state" in attrs:
                declarations.append(region)
            if "data-shadow-capa-declaration" in attrs:
                declaration_children.append(region)
    if not declarations:
        return False
    expected_statement = expected_capa_visible_statement(expected_status)
    parents_valid = all(
        region["attrs"].get("data-shadow-capa-id") == CAPA_ID
        and region["attrs"].get("data-shadow-capa-state") == expected_status
        for region in declarations
    )
    children_valid = (
        len(declaration_children) == len(declarations)
        and all(
            len(
                [
                    child
                    for child in declaration_children
                    if child.get("parent_region_id") == parent.get("region_id")
                    and child["attrs"].get("data-shadow-capa-declaration")
                    == "current-state"
                    and child["text"] == expected_statement
                ]
            )
            == 1
            for parent in declarations
        )
    )
    combined = " ".join(visible_texts)
    observed_states = re.findall(
        rf"CAPA\s+{re.escape(CAPA_ID)}\s+current\s+state:\s*([A-Z_]+)\.",
        combined,
    )
    conflicting_statuses = set(POSTPUBLICATION_CURRENT_STATE_PREAMBLES) - {
        expected_status
    }
    conflicting_claim = any(
        re.search(
            rf"\bCAPA\s+{re.escape(CAPA_ID)}\b[^.!?]{{0,100}}"
            rf"\b(?:is|remains?)\s+(?:now\s+)?`?{re.escape(status)}`?\b",
            combined,
            re.IGNORECASE,
        )
        is not None
        for status in conflicting_statuses
    )
    return (
        parents_valid
        and children_valid
        and not conflicting_claim
        and len(observed_states) == len(declaration_children)
        and observed_states == [expected_status] * len(declaration_children)
        and combined.count(expected_statement) == len(declaration_children)
    )


def canonical_public_artifact_identity_text(spec: dict[str, Any]) -> str:
    quantity = (
        f"{int(spec['bytes']):,} bytes"
        if "bytes" in spec
        else f"{int(spec['member_count']):,} members"
    )
    return f"{spec['filename']} · {quantity} · SHA-256 {spec['sha256']}"


def public_artifact_binding_check(
    regions: list[dict[str, Any]],
    spec: dict[str, Any],
) -> bool:
    artifact_id = str(spec["artifact_id"])
    matches = [
        region
        for region in regions
        if region["attrs"].get("data-shadow-artifact-id") == artifact_id
    ]
    if len(matches) != 1:
        return False
    region = matches[0]
    attrs = region["attrs"]
    expected_attrs = {
        "data-shadow-artifact-id": artifact_id,
        "data-shadow-filename": str(spec["filename"]),
        "data-shadow-sha256": str(spec["sha256"]),
    }
    if "bytes" in spec:
        expected_attrs["data-shadow-bytes"] = str(spec["bytes"])
    if "member_count" in spec:
        expected_attrs["data-shadow-member-count"] = str(spec["member_count"])
    if any(attrs.get(name) != value for name, value in expected_attrs.items()):
        return False
    identity_regions = [
        candidate
        for candidate in regions
        if candidate.get("parent_region_id") == region.get("region_id")
        and candidate["attrs"].get("data-shadow-artifact-identity-for")
        == artifact_id
    ]
    return (
        len(identity_regions) == 1
        and identity_regions[0]["text"] == canonical_public_artifact_identity_text(spec)
    )


def public_site_semantic_checks(
    requirement: dict[str, Any],
    pages: dict[str, str],
    *,
    expected_capa_status: str | None = None,
) -> dict[str, bool]:
    """Evaluate the non-hidden HTML-source v2 contract and bound public records."""
    missing_routes = [route for route in requirement["routes"] if route not in pages]
    if missing_routes:
        raise EvidenceError(
            f"semantic input lacks routes for {requirement['site_id']}: "
            + ", ".join(missing_routes)
        )
    route_evidence = {
        str(route): public_html_evidence(pages[str(route)])
        for route in requirement["routes"]
    }
    markup_valid = public_shadow_semantic_markup_is_closed(
        requirement,
        route_evidence,
    )
    home_source = pages["/"]
    home_evidence = route_evidence["/"]
    home_text = re.sub(r"\s+", " ", " ".join(home_evidence.text_chunks)).strip()
    home_links = tuple(home_evidence.hrefs)
    band, contract_valid, visible_claims_valid = public_boundary_band(home_source)
    band_links = tuple(band.get("hrefs", ())) if band is not None else ()
    all_visible_text = " ".join(
        re.sub(r"\s+", " ", " ".join(evidence.text_chunks)).strip()
        for evidence in route_evidence.values()
    )
    all_regions = [
        region
        for evidence in route_evidence.values()
        for region in evidence.regions
    ]
    canonical_release = "https://projectshadow.frylock117.chatgpt.site/release"
    canonical_capa = "https://projectshadow.frylock117.chatgpt.site/capa"
    site_id = str(requirement["site_id"])
    release_link = "/release" if site_id == "project-shadow" else canonical_release
    capa_link = "/capa" if site_id == "project-shadow" else canonical_capa

    checks: dict[str, bool] = {
        "semantic_markup_unambiguous": markup_valid,
        "boundary_contract_unique": contract_valid,
        "r1_0_1_current": contract_valid and visible_claims_valid,
        "historical_r1_superseded": contract_valid and visible_claims_valid,
        "contains_no_myth_package": contract_valid and visible_claims_valid,
        "generic_v0_2_0": contract_valid and visible_claims_valid,
        "full_canon_v0_3_5": contract_valid and visible_claims_valid,
        "sidecars_separate": contract_valid and visible_claims_valid,
        "sidecars_optional": contract_valid and visible_claims_valid,
        "sidecars_default_off": contract_valid and visible_claims_valid,
        "sidecars_nonauthorizing": contract_valid and visible_claims_valid,
        "boundary_no_contradictions": (
            contract_valid
            and visible_claims_valid
            and not public_boundary_has_contradiction(all_visible_text)
        ),
        "canonical_release_link": release_link in band_links,
        "capa_link": capa_link in band_links,
    }
    if site_id != "project-shadow":
        checks["no_direct_github_release_link"] = not any(
            urllib.parse.urlparse(link).netloc.lower() == "github.com"
            and "/PauseBeforeHarmProtocol/Project-Shadow/releases" in link
            for link in home_links
        )

    for name, spec in PUBLIC_ARTIFACT_BINDINGS.items():
        if name in requirement["specific_checks"]:
            checks[name] = markup_valid and public_artifact_binding_check(all_regions, spec)
    if "capa_id" in requirement["specific_checks"]:
        if expected_capa_status is None:
            current_status = require_object(load_json(CURRENT_STATUS), CURRENT_STATUS.name)
            expected_capa_status = str(current_status.get("capa", {}).get("status"))
        checks["capa_id"] = public_capa_state_check(pages, expected_capa_status)
    if "capa_state" in requirement["specific_checks"]:
        if expected_capa_status is None:
            current_status = require_object(load_json(CURRENT_STATUS), CURRENT_STATUS.name)
            expected_capa_status = str(current_status.get("capa", {}).get("status"))
        checks["capa_state"] = public_capa_state_check(pages, expected_capa_status)
    if "archived_manual_current_boundary" in requirement["specific_checks"]:
        manual_band, manual_contract, manual_claims = public_boundary_band(
            pages["/manual.html"]
        )
        checks["archived_manual_current_boundary"] = (
            manual_band is not None
            and manual_contract
            and manual_claims
            and canonical_release in tuple(manual_band.get("hrefs", ()))
            and canonical_capa in tuple(manual_band.get("hrefs", ()))
            and not public_boundary_has_contradiction(str(manual_band["text"]))
        )
    if "national_trump_record" in requirement["specific_checks"]:
        checks["national_trump_record"] = re.search(
            r"\bnational\s+trump\s+record\b",
            normalized_public_text(pages["/national.html"]),
            re.IGNORECASE,
        ) is not None
    if "preserved_predecessor" in requirement["specific_checks"]:
        checks["preserved_predecessor"] = public_artifact_binding_check(
            all_regions,
            PUBLIC_ARTIFACT_BINDINGS["preserved_predecessor"],
        )
    return checks


def html_attribute_text(attrs: dict[str, str]) -> str:
    return " ".join(
        f'{name}="{html.escape(value, quote=True)}"'
        for name, value in attrs.items()
    )


def canonical_public_boundary_band() -> str:
    return (
        '<section class="public-release-band" '
        + html_attribute_text(PUBLIC_BOUNDARY_BAND_ATTRIBUTES)
        + ">"
        + '<p data-shadow-claim="release-role">'
        + PUBLIC_BOUNDARY_CURRENT_CLAIM
        + "</p>"
        + '<p data-shadow-claim="sidecar-role">'
        + PUBLIC_BOUNDARY_SHARED_CLAIM
        + "</p>"
        + "</section>"
    )


def canonical_public_artifact_region(spec: dict[str, Any]) -> str:
    attrs = {
        "data-shadow-artifact-id": str(spec["artifact_id"]),
        "data-shadow-filename": str(spec["filename"]),
        "data-shadow-sha256": str(spec["sha256"]),
    }
    markers = [str(spec["filename"])]
    if "bytes" in spec:
        attrs["data-shadow-bytes"] = str(spec["bytes"])
        markers.append(f"{int(spec['bytes']):,}")
    if "member_count" in spec:
        attrs["data-shadow-member-count"] = str(spec["member_count"])
        markers.append(f"{int(spec['member_count']):,} members")
    markers.append(str(spec["sha256"]))
    return (
        "<article "
        + html_attribute_text(attrs)
        + "><p>"
        + " · ".join(markers)
        + "</p><p "
        + html_attribute_text(
            {"data-shadow-artifact-identity-for": str(spec["artifact_id"])}
        )
        + ">"
        + canonical_public_artifact_identity_text(spec)
        + "</p></article>"
    )


def canonical_public_capa_region(
    status: str = "IMPLEMENTED_PENDING_EFFECTIVENESS",
) -> str:
    attrs = {
        "data-shadow-capa-id": CAPA_ID,
        "data-shadow-capa-state": status,
    }
    return (
        "<section "
        + html_attribute_text(attrs)
        + '><p data-shadow-capa-declaration="current-state">'
        + expected_capa_visible_statement(status)
        + "</p></section>"
    )


def canonical_public_site_fixture(
    requirement: dict[str, Any],
    *,
    expected_capa_status: str = "IMPLEMENTED_PENDING_EFFECTIVENESS",
) -> dict[str, str]:
    """Create the deterministic fixture used by verifier self-tests and unit tests."""
    site_id = str(requirement["site_id"])
    release_link = (
        "/release"
        if site_id == "project-shadow"
        else "https://projectshadow.frylock117.chatgpt.site/release"
    )
    capa_link = (
        "/capa"
        if site_id == "project-shadow"
        else "https://projectshadow.frylock117.chatgpt.site/capa"
    )
    band = canonical_public_boundary_band().replace(
        "</section>",
        f'<a href="{release_link}">Canonical release</a>'
        f'<a href="{capa_link}">CAPA</a></section>',
    )
    pages = {
        str(route): "<html><body></body></html>"
        for route in requirement["routes"]
    }
    pages["/"] = "<html><body>" + band + "</body></html>"

    artifact_markup = "".join(
        canonical_public_artifact_region(PUBLIC_ARTIFACT_BINDINGS[name])
        for name in requirement["specific_checks"]
        if name in PUBLIC_ARTIFACT_BINDINGS
    )
    if artifact_markup:
        artifact_route = (
            "/release" if site_id == "project-shadow" else "/technical/project-shadow"
        )
        pages[artifact_route] = f"<html><body>{artifact_markup}</body></html>"
    if "capa_state" in requirement["specific_checks"]:
        capa_route = "/capa" if site_id == "project-shadow" else "/corrections"
        pages[capa_route] = (
            "<html><body>"
            + canonical_public_capa_region(expected_capa_status)
            + "</body></html>"
        )
    if "archived_manual_current_boundary" in requirement["specific_checks"]:
        pages["/manual.html"] = "<html><body>" + band + "</body></html>"
    if "national_trump_record" in requirement["specific_checks"]:
        pages["/national.html"] = "<html><body><h1>National Trump Record</h1></body></html>"
    return pages


def public_semantic_negative_control_execution() -> dict[str, Any]:
    requirement = next(
        row for row in PUBLIC_SITE_REQUIREMENTS if row["site_id"] == "project-shadow"
    )
    baseline = canonical_public_site_fixture(requirement)
    cases: dict[str, tuple[dict[str, str], bool]] = {"baseline": (baseline, True)}
    case_requirements: dict[str, dict[str, Any]] = {}
    current_paragraph = (
        '<p data-shadow-claim="release-role">'
        + PUBLIC_BOUNDARY_CURRENT_CLAIM
        + "</p>"
    )
    shared_paragraph = (
        '<p data-shadow-claim="sidecar-role">'
        + PUBLIC_BOUNDARY_SHARED_CLAIM
        + "</p>"
    )

    format_pages = dict(baseline)
    format_pages["/"] = format_pages["/"].replace(
        current_paragraph,
        (
            '<!-- irrelevant formatting control -->\n<p data-shadow-claim="release-role">\n  '
            + PUBLIC_BOUNDARY_CURRENT_CLAIM
            + "\n</p>"
        ),
    ).replace("</body>", "<p>Unrelated visible text.</p></body>")
    cases["format_noise"] = (format_pages, True)

    reordered_pages = dict(baseline)
    reordered_pages["/"] = reordered_pages["/"].replace(
        current_paragraph + shared_paragraph,
        shared_paragraph + current_paragraph,
    )
    cases["reordered_contract_children"] = (reordered_pages, True)

    reverse_pages = dict(baseline)
    reverse_pages["/"] = reverse_pages["/"].replace(
        PUBLIC_BOUNDARY_CURRENT_CLAIM,
        PUBLIC_BOUNDARY_CURRENT_CLAIM
        + " Project Shadow R1.0.1 is superseded. August 14 R1 is the current release.",
    )
    cases["reverse_current"] = (reverse_pages, False)

    dual_pages = dict(baseline)
    dual_pages["/"] = dual_pages["/"].replace(
        PUBLIC_BOUNDARY_CURRENT_CLAIM,
        PUBLIC_BOUNDARY_CURRENT_CLAIM + " August 14 R1 is also the current release.",
    )
    cases["dual_current"] = (dual_pages, False)

    sidecar_pages = dict(baseline)
    sidecar_pages["/"] = sidecar_pages["/"].replace(
        PUBLIC_BOUNDARY_SHARED_CLAIM,
        PUBLIC_BOUNDARY_SHARED_CLAIM
        + " The companions are mandatory, authorizing, and default-on.",
    )
    cases["sidecar_semantics_reversed"] = (sidecar_pages, False)

    capa_pages = dict(baseline)
    capa_pages["/capa"] = capa_pages["/capa"].replace(
        "</body>",
        (
            f'<section data-shadow-capa-id="{CAPA_ID}" '
            'data-shadow-capa-state="CLOSED_EFFECTIVE">'
            f"CAPA {CAPA_ID} current state: CLOSED_EFFECTIVE.</section></body>"
        ),
    )
    cases["contradictory_capa"] = (capa_pages, False)

    identity_pages = dict(baseline)
    outer_id = str(PUBLIC_ARTIFACT_BINDINGS["outer_exact_identity"]["artifact_id"])
    inner_id = str(PUBLIC_ARTIFACT_BINDINGS["inner_exact_identity"]["artifact_id"])
    identity_pages["/release"] = identity_pages["/release"].replace(
        f'data-shadow-artifact-id="{outer_id}"',
        'data-shadow-artifact-id="__swap_outer__"',
    ).replace(
        f'data-shadow-artifact-id="{inner_id}"',
        f'data-shadow-artifact-id="{outer_id}"',
    ).replace(
        'data-shadow-artifact-id="__swap_outer__"',
        f'data-shadow-artifact-id="{inner_id}"',
    )
    cases["identity_misbinding"] = (identity_pages, False)

    outside_role_pages = dict(baseline)
    outside_role_pages["/"] = outside_role_pages["/"].replace(
        "</body>",
        "<p>Project Shadow R1.0.1 is superseded. August 14 R1 is the current release.</p></body>",
    )
    cases["outside_band_role_reversal"] = (outside_role_pages, False)

    not_current_pages = dict(baseline)
    not_current_pages["/"] = not_current_pages["/"].replace(
        "</body>",
        "<p>R1.0.1 is not the current release.</p></body>",
    )
    cases["outside_band_r1_not_current"] = (not_current_pages, False)

    predecessor_current_pages = dict(baseline)
    predecessor_current_pages["/"] = predecessor_current_pages["/"].replace(
        "</body>",
        "<p>August 14 R1 is still current.</p></body>",
    )
    cases["outside_band_predecessor_still_current"] = (
        predecessor_current_pages,
        False,
    )

    superseded_pages = dict(baseline)
    superseded_pages["/"] = superseded_pages["/"].replace(
        "</body>",
        "<p>R1.0.1 has been superseded.</p></body>",
    )
    cases["outside_band_r1_has_been_superseded"] = (superseded_pages, False)

    outside_sidecar_pages = dict(baseline)
    outside_sidecar_pages["/"] = outside_sidecar_pages["/"].replace(
        "</body>",
        "<p>The companions are mandatory, authorizing, and default-on.</p></body>",
    )
    cases["outside_band_sidecar_reversal"] = (outside_sidecar_pages, False)

    enabled_by_default_pages = dict(baseline)
    enabled_by_default_pages["/"] = enabled_by_default_pages["/"].replace(
        "</body>",
        "<p>The companions must be enabled by default.</p></body>",
    )
    cases["outside_band_sidecars_must_default_on"] = (
        enabled_by_default_pages,
        False,
    )

    negated_claim_pages = dict(baseline)
    negated_claim_pages["/"] = negated_claim_pages["/"].replace(
        PUBLIC_BOUNDARY_CURRENT_CLAIM,
        "It is false that " + PUBLIC_BOUNDARY_CURRENT_CLAIM,
    )
    cases["negated_required_claim"] = (negated_claim_pages, False)

    unmarked_capa_pages = dict(baseline)
    unmarked_capa_pages["/capa"] = unmarked_capa_pages["/capa"].replace(
        "</body>",
        f"<p>CAPA {CAPA_ID} current state: CLOSED_EFFECTIVE.</p></body>",
    )
    cases["unmarked_contradictory_capa"] = (unmarked_capa_pages, False)

    unmarked_now_closed_pages = dict(baseline)
    unmarked_now_closed_pages["/capa"] = unmarked_now_closed_pages["/capa"].replace(
        "</body>",
        f"<p>CAPA {CAPA_ID} is now CLOSED_EFFECTIVE.</p></body>",
    )
    cases["unmarked_capa_is_now_closed"] = (unmarked_now_closed_pages, False)

    negated_capa_pages = dict(baseline)
    pending_statement = expected_capa_visible_statement(
        "IMPLEMENTED_PENDING_EFFECTIVENESS"
    )
    negated_capa_pages["/capa"] = negated_capa_pages["/capa"].replace(
        pending_statement,
        "It is false that " + pending_statement,
    )
    cases["negated_capa_declaration"] = (negated_capa_pages, False)

    prefixed_identity_pages = dict(baseline)
    outer_spec = PUBLIC_ARTIFACT_BINDINGS["outer_exact_identity"]
    outer_identity_text = canonical_public_artifact_identity_text(outer_spec)
    prefixed_identity_pages["/release"] = prefixed_identity_pages["/release"].replace(
        outer_identity_text,
        outer_identity_text.replace("5,731,663 bytes", "15,731,663 bytes"),
    )
    cases["artifact_digit_prefix"] = (prefixed_identity_pages, False)

    unrelated_artifact_pages = dict(baseline)
    unrelated_artifact_pages["/release"] = unrelated_artifact_pages["/release"].replace(
        "</body>",
        (
            '<article data-shadow-artifact-id="unrelated"><p>'
            + str(outer_spec["filename"])
            + " · 1 byte · SHA-256 "
            + str(outer_spec["sha256"])
            + "</p></article></body>"
        ),
    )
    cases["unrelated_artifact_record"] = (unrelated_artifact_pages, False)

    structured_dual_current_pages = dict(baseline)
    structured_dual_current_pages["/"] = structured_dual_current_pages["/"].replace(
        "</body>",
        '<span data-shadow-current-release="r1-2026-08-14">Legacy</span></body>',
    )
    cases["structured_dual_current_outside_band"] = (
        structured_dual_current_pages,
        False,
    )

    unknown_marker_pages = dict(baseline)
    unknown_marker_pages["/"] = unknown_marker_pages["/"].replace(
        "</body>",
        '<span data-shadow-unknown="x">Unknown</span></body>',
    )
    cases["unknown_shadow_marker"] = (unknown_marker_pages, False)

    off_home_claim_pages = dict(baseline)
    alternate_band = canonical_public_boundary_band().replace(
        PUBLIC_BOUNDARY_CURRENT_CLAIM,
        "Alternate release-role claim.",
    )
    off_home_claim_pages["/release"] = off_home_claim_pages["/release"].replace(
        "</body>",
        alternate_band + "</body>",
    )
    cases["off_home_noncanonical_structured_claim"] = (
        off_home_claim_pages,
        False,
    )

    duplicate_attribute_pages = dict(baseline)
    duplicate_attribute_pages["/"] = duplicate_attribute_pages["/"].replace(
        'data-shadow-contract="public-boundary-v2"',
        'data-shadow-contract="evil" data-shadow-contract="public-boundary-v2"',
        1,
    )
    cases["duplicate_semantic_attribute"] = (duplicate_attribute_pages, False)

    malformed_pages = dict(baseline)
    malformed_pages["/"] = malformed_pages["/"].replace(
        "</section>",
        "</div></section>",
        1,
    )
    cases["mismatched_semantic_markup"] = (malformed_pages, False)

    opacity_pages = dict(baseline)
    opacity_pages["/"] = opacity_pages["/"].replace(
        '<section class="public-release-band"',
        '<section style="opacity:0" class="public-release-band"',
        1,
    )
    cases["inline_opacity_hidden_contract"] = (opacity_pages, False)

    closed_details_pages = dict(baseline)
    closed_details_pages["/"] = closed_details_pages["/"].replace(
        '<section class="public-release-band"',
        '<details><section class="public-release-band"',
        1,
    ).replace("</section>", "</section></details>", 1)
    cases["closed_details_contract"] = (closed_details_pages, False)

    hidden_pages = dict(baseline)
    hidden_pages["/"] = hidden_pages["/"].replace(
        '<section class="public-release-band"',
        '<section hidden class="public-release-band"',
    )
    cases["hidden_contract"] = (hidden_pages, False)

    missing_link_pages = dict(baseline)
    missing_link_pages["/"] = missing_link_pages["/"].replace(
        '<a href="/release">Canonical release</a>',
        "",
    )
    cases["missing_release_link"] = (missing_link_pages, False)

    arm_requirement = next(
        row
        for row in PUBLIC_SITE_REQUIREMENTS
        if row["site_id"] == "american-repair-manual"
    )
    arm_manual_link_pages = canonical_public_site_fixture(arm_requirement)
    arm_manual_link_pages["/manual.html"] = arm_manual_link_pages[
        "/manual.html"
    ].replace(
        '<a href="https://projectshadow.frylock117.chatgpt.site/release">Canonical release</a>',
        "",
    ).replace(
        '<a href="https://projectshadow.frylock117.chatgpt.site/capa">CAPA</a>',
        "",
    )
    cases["arm_manual_missing_boundary_links"] = (arm_manual_link_pages, False)
    case_requirements["arm_manual_missing_boundary_links"] = arm_requirement

    failed: list[str] = []
    executed: list[str] = []
    for case_id, (pages, expected_pass) in cases.items():
        executed.append(case_id)
        if case_id != "baseline" and pages == baseline:
            failed.append(case_id)
            continue
        case_requirement = case_requirements.get(case_id, requirement)
        checks = public_site_semantic_checks(
            case_requirement,
            pages,
            expected_capa_status="IMPLEMENTED_PENDING_EFFECTIVENESS",
        )
        actual_pass = all(
            checks.get(name) is True
            for name in required_site_checks(case_requirement)
        )
        if actual_pass is not expected_pass:
            failed.append(case_id)
    case_ids = list(cases)
    return {
        "suite_id": "project-shadow.public-boundary-adversarial.v2",
        "expected_case_ids": case_ids,
        "executed_case_ids": executed,
        "matched_expectation_count": len(case_ids) - len(failed),
        "failed_case_ids": failed,
        "skipped_case_ids": sorted(set(case_ids) - set(executed)),
    }


def validate_public_semantic_negative_controls() -> dict[str, Any]:
    execution = public_semantic_negative_control_execution()
    expected = execution["expected_case_ids"]
    if (
        execution["executed_case_ids"] != expected
        or execution["matched_expectation_count"] != len(expected)
        or execution["failed_case_ids"]
        or execution["skipped_case_ids"]
    ):
        raise EvidenceError(
            "public-boundary adversarial self-test failed: "
            + json.dumps(execution, sort_keys=True)
        )
    return execution


def current_verifier_binding() -> dict[str, Any]:
    completed = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        check=False,
    )
    status = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=ROOT,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        check=False,
    )
    commit = completed.stdout.strip() if completed.returncode == 0 else "UNAVAILABLE"
    return {
        "path": VERIFIER_SOURCE_PATH,
        "sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "repository_commit": commit,
        "working_tree_clean": status.returncode == 0 and status.stdout == "",
    }


def current_public_artifact_bindings(
    rows: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    by_tag = {str(row["tag"]): row for row in rows}
    return {
        "r1_0_1_outer": dict(by_tag["r1.0.1-2026-08-17"]["asset"]),
        "r1_0_1_inner": dict(INNER_FINAL),
        "generic_myth_v0_2_0": dict(by_tag["generic-myth-v0.2.0"]["asset"]),
        "full_canon_myth_v0_3_5": dict(by_tag["myth-v0.3.5"]["asset"]),
    }


def observe_public_sites(
    rows: list[dict[str, Any]],
    evidence_dir: Path | None = None,
) -> list[dict[str, Any]]:
    current_status = require_object(load_json(CURRENT_STATUS), CURRENT_STATUS.name)
    observed_capa_state = str(current_status.get("capa", {}).get("status"))
    if observed_capa_state not in {
        "IMPLEMENTED_PENDING_EFFECTIVENESS",
        "CLOSED_EFFECTIVE",
    }:
        raise EvidenceError(f"unsupported live public CAPA state: {observed_capa_state!r}")
    verifier_binding: dict[str, Any] | None = None
    if evidence_dir is not None:
        if observed_capa_state != "IMPLEMENTED_PENDING_EFFECTIVENESS":
            raise EvidenceError(
                "v2 reclosure evidence may only be captured while CAPA is pending"
            )
        verifier_binding = current_verifier_binding()
        validate_verifier_binding(verifier_binding)
    release_page = ""
    observations: list[dict[str, Any]] = []
    captures: list[tuple[str, bytes]] = []
    for requirement in PUBLIC_SITE_REQUIREMENTS:
        pages: dict[str, str] = {}
        routes: list[dict[str, Any]] = []
        for route in requirement["routes"]:
            route_text = str(route)
            source, observation, response_body = fetch_public_site_route(
                requirement,
                route_text,
            )
            pages[route_text] = source
            member = public_site_response_member(
                str(requirement["site_id"]),
                route_text,
            )
            observation["response_body"] = {
                "pack_member": member,
                "bytes": len(response_body),
                "sha256": hashlib.sha256(response_body).hexdigest(),
                "encoding": "utf-8",
            }
            captures.append((member, response_body))
            routes.append(observation)
        checks = public_site_semantic_checks(
            requirement,
            pages,
            expected_capa_status=observed_capa_state,
        )
        expected_checks = required_site_checks(requirement)
        execution = require_complete_semantic_execution(
            f"live public-site boundary for {requirement['site_id']}",
            expected_checks,
            checks,
        )
        observations.append(
            {
                "site_id": requirement["site_id"],
                "base_url": requirement["base_url"],
                "routes": routes,
                "semantic_checks": checks,
                "check_execution": execution,
            }
        )
        if requirement["site_id"] == "project-shadow":
            release_page = pages["/release"]
    if not release_page:
        raise EvidenceError("canonical Project Shadow release page was not checked")
    current_rows = [
        row for row in rows if row.get("publication_state") == "PUBLISHED"
    ]
    if len(current_rows) != 3:
        raise EvidenceError("canonical release-page current-row coverage is ambiguous")
    for row in current_rows:
        asset = row["asset"]
        for expected in (asset["download_url"], asset["sha256"]):
            if expected not in release_page:
                raise EvidenceError(
                    f"canonical public release page omits {row['role']} identity: {expected}"
                )
    if evidence_dir is not None:
        evidence_dir.mkdir(parents=True, exist_ok=True)
        pack_path = evidence_dir / SITE_RESPONSE_EVIDENCE_PACK_FILENAME
        pack_binding = build_public_site_response_pack(captures, pack_path)
        total_expected = sum(
            int(site["check_execution"]["expected_count"])
            for site in observations
        )
        total_executed = sum(
            int(site["check_execution"]["executed_count"])
            for site in observations
        )
        total_passed = sum(
            int(site["check_execution"]["passed_count"])
            for site in observations
        )
        now = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace(
            "+00:00",
            "Z",
        )
        receipt = {
            "schema": (
                "project-shadow.r1.0.1-six-public-sites-"
                "effectiveness-reverification.v2"
            ),
            "capa_id": CAPA_ID,
            "status": "VERIFIED",
            "all_six_verified": True,
            "verified_at": now,
            "method": SITE_REVERIFICATION_RECEIPT_METHOD,
            "observed_capa_state": observed_capa_state,
            "verifier_binding": verifier_binding,
            "response_evidence_pack": pack_binding,
            "negative_control_execution": validate_public_semantic_negative_controls(),
            "check_execution": {
                "expected_count": total_expected,
                "executed_count": total_executed,
                "passed_count": total_passed,
                "failed_check_ids": [],
                "skipped_check_ids": [],
                "unexpected_check_ids": [],
            },
            "artifact_bindings": current_public_artifact_bindings(rows),
            "sites": observations,
            "nonclaims": {
                "operational_deployment_authorized": False,
                "production_authorized": False,
                "efficacy_claimed": False,
                "safety_claimed": False,
                "certification_claimed": False,
                "legal_compliance_claimed": False,
            },
        }
        validate_six_public_sites_effectiveness_v2(
            receipt,
            {str(row["tag"]): row for row in rows},
            response_pack=pack_path,
        )
        receipt_path = evidence_dir / SITE_REVERIFICATION_RECEIPT_FILENAME
        try:
            with receipt_path.open("x", encoding="utf-8", newline="\n") as handle:
                json.dump(receipt, handle, indent=2, sort_keys=True)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
        except FileExistsError as exc:
            raise EvidenceError(
                f"refusing to overwrite site reverification receipt: {receipt_path}"
            ) from exc
    return observations


def verify_public_site_release_links(
    rows: list[dict[str, Any]],
    evidence_dir: Path | None = None,
) -> None:
    observe_public_sites(rows, evidence_dir)


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
    hf_downloaded: dict[str, Path] = {}
    repository = "PauseBeforeHarmProtocol/Project-Shadow"
    for row in online_rows:
        asset = row["asset"]
        downloaded[row["role"]] = download_and_hash(asset, destination)
        release_url = f"https://github.com/{repository}/releases/tag/{row['tag']}"
        check_link(release_url)

    by_tag = {str(row["tag"]): row for row in rows}
    for tag in ("generic-myth-v0.2.0", "r1.0.1-2026-08-17"):
        row = by_tag[tag]
        hf_downloaded[tag] = download_and_hash_at_url(
            row["asset"],
            f"{HF_SPACE_RESOLVE_BASE}/{CURRENT_MIRROR_PATHS[tag]}",
            destination / "hugging-face",
        )
    current_status = require_object(load_json(CURRENT_STATUS), CURRENT_STATUS.name)
    capa_status = current_status.get("capa", {}).get("status")
    verify_live_release_metadata(
        online_rows,
        expected_latest_tag,
        capa_status=str(capa_status) if phase == "POSTPUBLICATION" else None,
    )
    if phase == "POSTPUBLICATION":
        evidence_dir = (
            destination / "public-site-evidence"
            if capa_status == "IMPLEMENTED_PENDING_EFFECTIVENESS"
            else None
        )
        verify_public_site_release_links(rows, evidence_dir)

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

    generic = downloaded.get("OPTIONAL_GENERIC_COMPANION")
    hf_generic = hf_downloaded.get("generic-myth-v0.2.0")
    if generic is None or hf_generic is None:
        raise EvidenceError("downloaded assets lack both Generic v0.2.0 mirrors")
    for host, archive in (("GITHUB", generic), ("HUGGING_FACE", hf_generic)):
        generic_completed = subprocess.run(
            [
                sys.executable,
                "-I",
                "-S",
                "-B",
                str(ROOT / "tools" / "verify_generic_myth_v0_2_0.py"),
                str(archive),
            ],
            cwd=ROOT,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        if generic_completed.returncode != 0:
            raise EvidenceError(
                f"bounded verification of {host} Generic v0.2.0 failed:\n"
                + generic_completed.stdout
            )
        print(f"{host} Generic v0.2.0: {generic_completed.stdout.rstrip()}")

    current_r1 = downloaded.get("R1_REFERENCE_CORRECTED")
    hf_current_r1 = hf_downloaded.get("r1.0.1-2026-08-17")
    if current_r1 is None or hf_current_r1 is None:
        raise EvidenceError("downloaded assets lack both corrected R1.0.1 mirrors")
    for host, archive in (("GITHUB", current_r1), ("HUGGING_FACE", hf_current_r1)):
        current_completed = subprocess.run(
            [
                sys.executable,
                "-I",
                "-S",
                "-B",
                str(ROOT / "tools" / "verify_outer_release.py"),
                str(archive),
            ],
            cwd=ROOT,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        if current_completed.returncode != 0:
            raise EvidenceError(
                f"positive recursive verification of {host} R1.0.1 failed:\n"
                + current_completed.stdout
            )
        print(f"{host} R1.0.1: {current_completed.stdout.rstrip()}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--online",
        action="store_true",
        help="redownload exact assets and check phase-appropriate public URLs",
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
    print("PASS: public-boundary adversarial negative controls")
    print("PASS: preserved historical candidate/signature records remain non-self-authorizing")
    print("PASS: nonclaim scan")
    if args.online:
        print("PASS: exact published assets and release metadata")
        current_status = require_object(load_json(CURRENT_STATUS), CURRENT_STATUS.name)
        if (
            phase == "POSTPUBLICATION"
            and current_status.get("capa", {}).get("status") == "CLOSED_EFFECTIVE"
        ):
            print("PASS: six public-site routes and corrected-boundary semantics")
        elif phase == "POSTPUBLICATION":
            print("PASS: current six-site boundary state; CAPA reverification remains pending")
    else:
        print("INFO: network verification skipped (use --online --download-dir DIR)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
