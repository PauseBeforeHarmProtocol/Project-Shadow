from __future__ import annotations

import importlib.util
import hashlib
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "verify_repository_evidence",
    ROOT / "tools" / "verify_repository_evidence.py",
)
if SPEC is None or SPEC.loader is None:  # pragma: no cover - import setup guard
    raise RuntimeError("could not load tools/verify_repository_evidence.py")
VERIFIER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VERIFIER)


class RepositoryEvidenceTests(unittest.TestCase):
    @staticmethod
    def committed_verifier_binding() -> dict[str, object]:
        commit = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True,
        ).stdout.strip()
        source = subprocess.run(
            ["git", "show", f"{commit}:{VERIFIER.VERIFIER_SOURCE_PATH}"],
            cwd=ROOT,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        ).stdout
        return {
            "path": VERIFIER.VERIFIER_SOURCE_PATH,
            "sha256": hashlib.sha256(source).hexdigest(),
            "repository_commit": commit,
            "working_tree_clean": True,
        }

    def test_current_repository_metadata_agrees(self) -> None:
        self.assertGreaterEqual(VERIFIER.parse_all_json(), 1)
        rows = VERIFIER.verify_repository_metadata("POSTPUBLICATION")
        self.assertEqual([row["order"] for row in rows], [1, 2, 3, 4, 5])
        self.assertEqual(
            [row["tag"] for row in VERIFIER.published_rows(rows)],
            [
                "myth-v0.3.4",
                "r1-2026-08-14",
                "myth-v0.3.5",
                "generic-myth-v0.2.0",
                "r1.0.1-2026-08-17",
            ],
        )
        self.assertEqual(VERIFIER.prohibited_claim_findings(), [])

    def test_live_release_preambles_are_exact_additive_controls(self) -> None:
        self.assertEqual(
            set(VERIFIER.POSTPUBLICATION_RELEASE_PREAMBLES),
            {
                "myth-v0.3.5",
                "generic-myth-v0.2.0",
                "r1.0.1-2026-08-17",
            },
        )
        for tag, note_path in VERIFIER.RELEASE_NOTES.items():
            frozen_note = note_path.read_text(encoding="utf-8")
            expected = VERIFIER.expected_live_release_body(tag)
            self.assertTrue(expected.endswith(frozen_note))
            if tag in VERIFIER.POSTPUBLICATION_RELEASE_PREAMBLES:
                self.assertTrue(expected.startswith("> **Effectiveness correction — 2026-08-22.**"))
                self.assertIn("`IMPLEMENTED_PENDING_EFFECTIVENESS`", expected)
                self.assertIn("`CLOSED_EFFECTIVE`", expected)
                self.assertNotIn("is currently", expected)
                closed = VERIFIER.expected_live_release_body(tag, "CLOSED_EFFECTIVE")
                self.assertIn(
                    "is `CLOSED_EFFECTIVE` under retained v2 response bodies",
                    closed,
                )
                self.assertNotIn(
                    "is `IMPLEMENTED_PENDING_EFFECTIVENESS`; public-boundary-v2",
                    closed,
                )
            else:
                self.assertEqual(expected, frozen_note)
        self.assertIn(
            "Project_Shadow_R1.0.1_Runtime_Family_Myth_Decoupled_2026-08-17.zip",
            VERIFIER.expected_live_release_body("myth-v0.3.5"),
        )

    def test_historical_public_release_verifier_remains_byte_pinned(self) -> None:
        digest = hashlib.sha256(
            (ROOT / "tools" / "verify_public_release.py").read_bytes()
        ).hexdigest()
        self.assertEqual(
            digest,
            "f1358db6c824319501d0eabf341174eb96217e5d2545d9ac908a81d338c8afa8",
        )

    def test_current_public_release_verifiers_remain_byte_pinned(self) -> None:
        outer = hashlib.sha256(
            (ROOT / "tools" / "verify_outer_release.py").read_bytes()
        ).hexdigest()
        generic = hashlib.sha256(
            (ROOT / "tools" / "verify_generic_myth_v0_2_0.py").read_bytes()
        ).hexdigest()
        self.assertEqual(outer, VERIFIER.CURRENT_OUTER_VERIFIER_SHA256)
        self.assertEqual(generic, VERIFIER.GENERIC_V0_2_0_VERIFIER_SHA256)

    def test_published_postpublication_has_no_release_placeholders(self) -> None:
        self.assertEqual(VERIFIER.release_placeholder_findings(), [])

    def test_prepublication_mode_rejects_postpublication_manifest(self) -> None:
        with self.assertRaisesRegex(VERIFIER.EvidenceError, "manifest phase mismatch"):
            VERIFIER.verify_repository_metadata("PREPUBLICATION")

    def test_postpublication_reopens_only_six_site_effectiveness(self) -> None:
        status = json.loads(VERIFIER.CURRENT_STATUS.read_text(encoding="utf-8"))
        capa = json.loads(VERIFIER.CAPA_RECORD.read_text(encoding="utf-8"))
        self.assertEqual(status["publication_phase"], "POSTPUBLICATION")
        self.assertEqual(
            status["capa"]["status"],
            "IMPLEMENTED_PENDING_EFFECTIVENESS",
        )
        self.assertFalse(status["capa"]["effectiveness_verified"])
        self.assertEqual(status["capa"]["verification_records"], [])
        self.assertEqual(capa["status"], "IMPLEMENTED_PENDING_EFFECTIVENESS")
        self.assertFalse(capa["closure"]["effectiveness_verified"])
        self.assertIsNone(capa["closure"]["closed_at"])
        self.assertEqual(
            capa["pending_effectiveness_criteria"],
            [VERIFIER.REOPENED_EFFECTIVENESS_CRITERION],
        )
        historical = capa["closure_history"][0]
        self.assertEqual(historical["status"], "CLOSED_EFFECTIVE")
        self.assertEqual(
            historical["event"],
            VERIFIER.HISTORICAL_CAPA_CLOSURE_EVENT,
        )

    def test_stale_true_effectiveness_after_reopening_fails_closed(self) -> None:
        status = json.loads(VERIFIER.CURRENT_STATUS.read_text(encoding="utf-8"))
        status["capa"]["effectiveness_verified"] = True
        with tempfile.TemporaryDirectory(prefix="shadow-capa-status-test-") as temp:
            mutated = Path(temp) / "PUBLIC_RELEASE_STATUS_2026-08-17.json"
            mutated.write_text(json.dumps(status), encoding="utf-8")
            with mock.patch.object(VERIFIER, "CURRENT_STATUS", mutated):
                with self.assertRaisesRegex(
                    VERIFIER.EvidenceError,
                    "pending CAPA state misstates the reopened criterion",
                ):
                    VERIFIER.verify_repository_metadata("POSTPUBLICATION")

    def test_missing_reopening_pointer_fails_closed(self) -> None:
        status = json.loads(VERIFIER.CURRENT_STATUS.read_text(encoding="utf-8"))
        status["capa"].pop("reopening_record")
        with tempfile.TemporaryDirectory(prefix="shadow-capa-reopening-test-") as temp:
            mutated = Path(temp) / "PUBLIC_RELEASE_STATUS_2026-08-17.json"
            mutated.write_text(json.dumps(status), encoding="utf-8")
            with mock.patch.object(VERIFIER, "CURRENT_STATUS", mutated):
                with self.assertRaisesRegex(
                    VERIFIER.EvidenceError,
                    "derived current status misstates the CAPA reopening",
                ):
                    VERIFIER.verify_repository_metadata("POSTPUBLICATION")

    def test_historical_v1_site_receipt_cannot_be_reused_for_reclosure(self) -> None:
        status = json.loads(VERIFIER.CURRENT_STATUS.read_text(encoding="utf-8"))
        capa = json.loads(VERIFIER.CAPA_RECORD.read_text(encoding="utf-8"))
        old_records = list(VERIFIER.HISTORICAL_CAPA_EFFECTIVENESS_RECORDS)
        status["capa"]["verification_records"] = old_records
        capa["closure"] = dict(VERIFIER.HISTORICAL_CAPA_CLOSURE_EVENT)
        with self.assertRaisesRegex(
            VERIFIER.EvidenceError,
            "CAPA closure must bind redownload, v2 site, and human-review records",
        ):
            VERIFIER.validate_capa_effectiveness_record_pointers(status, capa)

    def test_reclosure_requirements_are_exact_and_cannot_be_weakened(self) -> None:
        reopening = json.loads(
            VERIFIER.CAPA_REOPENING_RECORD.read_text(encoding="utf-8")
        )
        status = json.loads(VERIFIER.CURRENT_STATUS.read_text(encoding="utf-8"))
        capa = json.loads(VERIFIER.CAPA_RECORD.read_text(encoding="utf-8"))
        reopening["reclosure_requirements"].pop()
        with self.assertRaisesRegex(
            VERIFIER.EvidenceError,
            "reclosure requirements were weakened or reordered",
        ):
            VERIFIER.validate_capa_reopening_record(reopening, status, capa)

    def test_future_closed_state_shape_is_reachable_and_human_gated(self) -> None:
        reopening = json.loads(
            VERIFIER.CAPA_REOPENING_RECORD.read_text(encoding="utf-8")
        )
        status = json.loads(VERIFIER.CURRENT_STATUS.read_text(encoding="utf-8"))
        capa = json.loads(VERIFIER.CAPA_RECORD.read_text(encoding="utf-8"))
        expected_records = list(VERIFIER.CURRENT_CAPA_EFFECTIVENESS_RECORDS)
        capa["status"] = "CLOSED_EFFECTIVE"
        capa["pending_effectiveness_criteria"] = []
        capa["closure"] = {
            "closed_at": "2026-08-23T12:00:00Z",
            "effectiveness_verified": True,
            "verification_record": VERIFIER.CURRENT_REDOWNLOAD_RECORD,
            "verification_records": expected_records,
        }
        status["capa"]["status"] = "CLOSED_EFFECTIVE"
        status["capa"]["effectiveness_verified"] = True
        status["capa"]["pending_effectiveness_criteria"] = []
        status["capa"]["verification_records"] = expected_records
        status["source_records"] = list(
            dict.fromkeys(status["source_records"] + expected_records)
        )

        VERIFIER.validate_capa_reopening_record(reopening, status, capa)
        VERIFIER.validate_capa_effectiveness_record_pointers(status, capa)
        status["capa"]["verification_records"].remove(
            VERIFIER.PUBLIC_BOUNDARY_HUMAN_REVIEW_RECORD
        )
        with self.assertRaisesRegex(
            VERIFIER.EvidenceError,
            "human-review records",
        ):
            VERIFIER.validate_capa_effectiveness_record_pointers(status, capa)

    def test_reclosure_timestamp_causality_fails_closed(self) -> None:
        parse = VERIFIER.parse_rfc3339_utc
        reopened = parse("reopened", "2026-08-22T12:00:00Z")
        verified = parse("verified", "2026-08-22T13:00:00Z")
        reviewed = parse("reviewed", "2026-08-22T14:00:00Z")
        closed = parse("closed", "2026-08-22T15:00:00Z")
        observed = (
            parse("observed one", "2026-08-22T12:15:00Z"),
            parse("observed two", "2026-08-22T12:45:00Z"),
        )
        VERIFIER.validate_reclosure_causality(
            reopened,
            verified,
            reviewed,
            closed,
            observed,
        )
        with self.assertRaisesRegex(VERIFIER.EvidenceError, "CAPA causality"):
            VERIFIER.validate_reclosure_causality(
                reopened,
                verified,
                reviewed,
                parse("early close", "2026-08-22T13:30:00Z"),
                observed,
            )
        with self.assertRaisesRegex(VERIFIER.EvidenceError, "CAPA causality"):
            VERIFIER.validate_reclosure_causality(
                reopened,
                verified,
                reviewed,
                closed,
                (parse("pre-reopening route", "2026-08-22T11:59:59Z"),),
            )

    def test_manual_evidence_upload_is_pending_state_gated(self) -> None:
        workflow = (ROOT / ".github/workflows/public-evidence-verification.yml").read_text(
            encoding="utf-8"
        )
        self.assertIn("fetch-depth: 0", workflow)
        self.assertIn("id: capa_state", workflow)
        self.assertIn("github.run_id || github.ref", workflow)
        self.assertIn("steps.capa_state.outputs.pending_capture == 'true'", workflow)
        self.assertIn("if-no-files-found: error", workflow)

    def test_human_review_binds_exact_v2_receipt_and_rendered_sites(self) -> None:
        six_site = {
            "verified_at": "2026-08-22T13:00:00Z",
            "response_evidence_pack": {
                "filename": VERIFIER.SITE_RESPONSE_EVIDENCE_PACK_FILENAME,
                "sha256": "1" * 64,
            },
        }
        with tempfile.TemporaryDirectory(prefix="shadow-human-review-test-") as temp:
            receipt_path = Path(temp) / "v2.json"
            receipt_payload = json.dumps(six_site, sort_keys=True).encode("utf-8")
            receipt_path.write_bytes(receipt_payload)
            review = {
                "schema": "project-shadow.public-boundary-v2-human-review.v1",
                "capa_id": VERIFIER.CAPA_ID,
                "status": "APPROVED_FOR_RECLOSURE",
                "human_reviewer": True,
                "semantic_contract": VERIFIER.PUBLIC_BOUNDARY_CONTRACT,
                "reviewed_at": "2026-08-22T14:00:00Z",
                "reviewer": {
                    "identity": "Named Human Reviewer",
                    "reviewer_type": "HUMAN",
                    "attestation": VERIFIER.PUBLIC_BOUNDARY_HUMAN_REVIEW_ATTESTATION,
                },
                "six_site_reverification": {
                    "record": VERIFIER.SIX_SITE_REVERIFICATION_RECORD,
                    "sha256": hashlib.sha256(receipt_payload).hexdigest(),
                    "verified_at": six_site["verified_at"],
                    "response_evidence_pack": six_site["response_evidence_pack"],
                },
                "sites": [
                    {
                        "site_id": requirement["site_id"],
                        "base_url": requirement["base_url"],
                        "routes_reviewed": list(requirement["routes"]),
                        "browser_rendered_visible": True,
                        "visible_meaning_confirmed": True,
                    }
                    for requirement in VERIFIER.PUBLIC_SITE_REQUIREMENTS
                ],
                "determinations": VERIFIER.PUBLIC_BOUNDARY_HUMAN_REVIEW_DETERMINATIONS,
                "nonclaims": {
                    "operational_deployment_authorized": False,
                    "production_authorized": False,
                    "efficacy_claimed": False,
                    "safety_claimed": False,
                    "certification_claimed": False,
                    "legal_compliance_claimed": False,
                },
            }
            VERIFIER.validate_public_boundary_human_review(
                review,
                six_site,
                six_site_receipt_path=receipt_path,
            )
            review["human_reviewer"] = False
            with self.assertRaisesRegex(
                VERIFIER.EvidenceError,
                "human-review identity/state mismatch",
            ):
                VERIFIER.validate_public_boundary_human_review(
                    review,
                    six_site,
                    six_site_receipt_path=receipt_path,
                )

    def test_retained_current_effectiveness_receipts_validate(self) -> None:
        rows = VERIFIER.verify_repository_metadata("POSTPUBLICATION")
        by_tag = {row["tag"]: row for row in rows}
        redownload = json.loads(
            VERIFIER.CURRENT_REDOWNLOAD.read_text(encoding="utf-8")
        )
        sites = json.loads(
            VERIFIER.SIX_SITE_EFFECTIVENESS.read_text(encoding="utf-8")
        )
        VERIFIER.validate_current_redownload(redownload, by_tag)
        VERIFIER.validate_six_public_sites_effectiveness(sites, by_tag)
        project_shadow = next(
            site for site in sites["sites"] if site["site_id"] == "project-shadow"
        )
        self.assertIn("/status", [route["path"] for route in project_shadow["routes"]])

    def test_impossible_effectiveness_timestamp_fails_closed(self) -> None:
        rows = VERIFIER.verify_repository_metadata("POSTPUBLICATION")
        by_tag = {row["tag"]: row for row in rows}
        redownload = json.loads(
            VERIFIER.CURRENT_REDOWNLOAD.read_text(encoding="utf-8")
        )
        redownload["recorded_at"] = "2026-02-31T10:33:45Z"
        with self.assertRaisesRegex(VERIFIER.EvidenceError, "not a real UTC timestamp"):
            VERIFIER.validate_current_redownload(redownload, by_tag)

    def test_redownload_hugging_face_final_host_mutation_fails_closed(self) -> None:
        rows = VERIFIER.verify_repository_metadata("POSTPUBLICATION")
        by_tag = {row["tag"]: row for row in rows}
        redownload = json.loads(
            VERIFIER.CURRENT_REDOWNLOAD.read_text(encoding="utf-8")
        )
        hf_row = next(
            row for row in redownload["observations"]
            if row["host"] == "HUGGING_FACE"
        )
        hf_row["final_host"] = "example.invalid"
        with self.assertRaisesRegex(
            VERIFIER.EvidenceError,
            "unexpected HUGGING_FACE public-download final host",
        ):
            VERIFIER.validate_current_redownload(redownload, by_tag)

    def test_documented_hugging_face_cdn_edges_are_exactly_allowed(self) -> None:
        accepted = (
            "https://huggingface.co/file",
            "https://us.aws.cdn.hf.co/file",
            "https://us.gcp.cdn.hf.co/file",
            "https://us.gcp.cdn.hf.co:443/file",
        )
        for url in accepted:
            with self.subTest(url=url):
                self.assertEqual(
                    VERIFIER.validate_public_download_final_host("HUGGING_FACE", url),
                    url.split("/")[2].split(":")[0],
                )
        rejected = (
            "https://gcp.cdn.hf.co/file",
            "https://us.gcp.cdn.hf.co.example.invalid/file",
            "http://us.gcp.cdn.hf.co/file",
            "https://us.gcp.cdn.hf.co:444/file",
        )
        for url in rejected:
            with self.subTest(url=url):
                with self.assertRaisesRegex(
                    VERIFIER.EvidenceError,
                    "unexpected HUGGING_FACE public-download final host",
                ):
                    VERIFIER.validate_public_download_final_host("HUGGING_FACE", url)

    def test_retained_hf_observation_accepts_gcp_route_but_still_binds_identity(self) -> None:
        rows = VERIFIER.verify_repository_metadata("POSTPUBLICATION")
        by_tag = {row["tag"]: row for row in rows}
        redownload = json.loads(
            VERIFIER.CURRENT_REDOWNLOAD.read_text(encoding="utf-8")
        )
        hf_row = next(
            row for row in redownload["observations"]
            if row["host"] == "HUGGING_FACE"
        )
        hf_row["final_host"] = "us.gcp.cdn.hf.co"
        VERIFIER.validate_current_redownload(redownload, by_tag)
        hf_row["sha256_observed"] = "0" * 64
        with self.assertRaisesRegex(
            VERIFIER.EvidenceError,
            "redownload identity mismatch",
        ):
            VERIFIER.validate_current_redownload(redownload, by_tag)

    def test_python_verifier_sources_are_pinned_to_lf(self) -> None:
        paths = (
            "tools/verify_public_release.py",
            "tools/verify_outer_release.py",
            "tools/verify_generic_myth_v0_2_0.py",
        )
        completed = subprocess.run(
            ["git", "check-attr", "eol", "--", *paths],
            cwd=ROOT,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True,
        )
        for path in paths:
            self.assertIn(f"{path}: eol: lf", completed.stdout)

    def test_generic_public_download_verifier_mutation_fails_closed(self) -> None:
        rows = VERIFIER.verify_repository_metadata("POSTPUBLICATION")
        by_tag = {row["tag"]: row for row in rows}
        redownload = json.loads(
            VERIFIER.CURRENT_REDOWNLOAD.read_text(encoding="utf-8")
        )
        redownload["generic_v0_2_0_bounded_verification"]["observations"][1][
            "status"
        ] = "FAIL"
        with self.assertRaisesRegex(
            VERIFIER.EvidenceError,
            "Generic v0.2.0 public-download verification mismatch",
        ):
            VERIFIER.validate_current_redownload(redownload, by_tag)

    def test_site_receipt_wrong_alias_final_path_fails_closed(self) -> None:
        rows = VERIFIER.verify_repository_metadata("POSTPUBLICATION")
        by_tag = {row["tag"]: row for row in rows}
        sites = json.loads(
            VERIFIER.SIX_SITE_EFFECTIVENESS.read_text(encoding="utf-8")
        )
        arm = next(
            site for site in sites["sites"]
            if site["site_id"] == "american-repair-manual"
        )
        manual = next(route for route in arm["routes"] if route["path"] == "/manual.html")
        manual["final_url"] = manual["url"]
        with self.assertRaisesRegex(
            VERIFIER.EvidenceError,
            "route observation mismatch: american-repair-manual/manual.html",
        ):
            VERIFIER.validate_six_public_sites_effectiveness(sites, by_tag)

    def test_national_route_has_only_bounded_size_override(self) -> None:
        rows = VERIFIER.verify_repository_metadata("POSTPUBLICATION")
        by_tag = {row["tag"]: row for row in rows}
        sites = json.loads(
            VERIFIER.SIX_SITE_EFFECTIVENESS.read_text(encoding="utf-8")
        )
        record = next(
            site for site in sites["sites"] if site["site_id"] == "the-record"
        )
        national = next(
            route for route in record["routes"] if route["path"] == "/national.html"
        )
        self.assertGreater(national["bytes_observed"], VERIFIER.MAX_LINK_RESPONSE_BYTES)
        VERIFIER.validate_six_public_sites_effectiveness(sites, by_tag)
        national["bytes_observed"] = 16 * 1024 * 1024 + 1
        with self.assertRaisesRegex(VERIFIER.EvidenceError, "route observation mismatch"):
            VERIFIER.validate_six_public_sites_effectiveness(sites, by_tag)

    def test_v2_site_receipt_replays_exact_response_bodies(self) -> None:
        rows = VERIFIER.verify_repository_metadata("POSTPUBLICATION")
        by_tag = {row["tag"]: row for row in rows}
        sites = []
        captures = []
        for requirement in VERIFIER.PUBLIC_SITE_REQUIREMENTS:
            pages = VERIFIER.canonical_public_site_fixture(requirement)
            routes = []
            for route in requirement["routes"]:
                route_text = str(route)
                body = pages[route_text].encode("utf-8")
                member = VERIFIER.public_site_response_member(
                    str(requirement["site_id"]),
                    route_text,
                )
                digest = hashlib.sha256(body).hexdigest()
                routes.append(
                    {
                        "path": route_text,
                        "url": VERIFIER.exact_public_site_url(
                            str(requirement["base_url"]),
                            route_text,
                        ),
                        "final_url": VERIFIER.expected_site_final_url(
                            requirement,
                            route_text,
                        ),
                        "http_status": 200,
                        "bytes_observed": len(body),
                        "sha256_observed": digest,
                        "content_type": "text/html",
                        "observed_at": "2026-08-22T12:47:23Z",
                        "response_body": {
                            "pack_member": member,
                            "bytes": len(body),
                            "sha256": digest,
                            "encoding": "utf-8",
                        },
                    }
                )
                captures.append((member, body))
            checks = VERIFIER.public_site_semantic_checks(requirement, pages)
            execution = VERIFIER.require_complete_semantic_execution(
                f"synthetic {requirement['site_id']}",
                VERIFIER.required_site_checks(requirement),
                checks,
            )
            sites.append(
                {
                    "site_id": requirement["site_id"],
                    "base_url": requirement["base_url"],
                    "routes": routes,
                    "semantic_checks": checks,
                    "check_execution": execution,
                }
            )

        totals = {
            "expected_count": sum(site["check_execution"]["expected_count"] for site in sites),
            "executed_count": sum(site["check_execution"]["executed_count"] for site in sites),
            "passed_count": sum(site["check_execution"]["passed_count"] for site in sites),
            "failed_check_ids": [],
            "skipped_check_ids": [],
            "unexpected_check_ids": [],
        }
        with tempfile.TemporaryDirectory(prefix="shadow-site-v2-test-") as temp:
            temp_path = Path(temp)
            pack_path = temp_path / VERIFIER.SITE_RESPONSE_EVIDENCE_PACK_FILENAME
            pack_binding = VERIFIER.build_public_site_response_pack(captures, pack_path)
            receipt = {
                "schema": (
                    "project-shadow.r1.0.1-six-public-sites-"
                    "effectiveness-reverification.v2"
                ),
                "capa_id": VERIFIER.CAPA_ID,
                "status": "VERIFIED",
                "all_six_verified": True,
                "verified_at": "2026-08-22T12:47:23Z",
                "method": VERIFIER.SITE_REVERIFICATION_RECEIPT_METHOD,
                "observed_capa_state": "IMPLEMENTED_PENDING_EFFECTIVENESS",
                "verifier_binding": self.committed_verifier_binding(),
                "response_evidence_pack": pack_binding,
                "negative_control_execution": (
                    VERIFIER.validate_public_semantic_negative_controls()
                ),
                "check_execution": totals,
                "artifact_bindings": VERIFIER.current_public_artifact_bindings(rows),
                "sites": sites,
                "nonclaims": {
                    "operational_deployment_authorized": False,
                    "production_authorized": False,
                    "efficacy_claimed": False,
                    "safety_claimed": False,
                    "certification_claimed": False,
                    "legal_compliance_claimed": False,
                },
            }
            VERIFIER.validate_six_public_sites_effectiveness_v2(
                receipt,
                by_tag,
                response_pack=pack_path,
            )

            wrong_state = json.loads(json.dumps(receipt))
            wrong_state["observed_capa_state"] = "CLOSED_EFFECTIVE"
            with self.assertRaisesRegex(
                VERIFIER.EvidenceError,
                "did not observe pending CAPA state",
            ):
                VERIFIER.validate_six_public_sites_effectiveness_v2(
                    wrong_state,
                    by_tag,
                    response_pack=pack_path,
                )

            unsafe_filename = json.loads(json.dumps(receipt))
            unsafe_filename["response_evidence_pack"]["filename"] = "../escape.zip"
            with self.assertRaisesRegex(
                VERIFIER.EvidenceError,
                "response-evidence pack binding missing",
            ):
                VERIFIER.validate_six_public_sites_effectiveness_v2(
                    unsafe_filename,
                    by_tag,
                    response_pack=pack_path,
                )

            altered = list(captures)
            altered[0] = (altered[0][0], altered[0][1] + b"x")
            altered_dir = temp_path / "altered"
            altered_dir.mkdir()
            altered_path = altered_dir / VERIFIER.SITE_RESPONSE_EVIDENCE_PACK_FILENAME
            altered_binding = VERIFIER.build_public_site_response_pack(
                altered,
                altered_path,
            )
            altered_receipt = json.loads(json.dumps(receipt))
            altered_receipt["response_evidence_pack"] = altered_binding
            with self.assertRaisesRegex(
                VERIFIER.EvidenceError,
                "response evidence binding mismatch",
            ):
                VERIFIER.validate_six_public_sites_effectiveness_v2(
                    altered_receipt,
                    by_tag,
                    response_pack=altered_path,
                )

            unsafe = list(captures)
            unsafe[0] = ("responses/../escape.html", unsafe[0][1])
            with self.assertRaisesRegex(
                VERIFIER.EvidenceError,
                "unsafe response-evidence member",
            ):
                VERIFIER.build_public_site_response_pack(
                    unsafe,
                    temp_path / "unsafe.zip",
                )

    def test_verifier_binding_requires_reachable_exact_git_blob(self) -> None:
        binding = self.committed_verifier_binding()
        VERIFIER.validate_verifier_binding(binding)

        fabricated_commit = dict(binding)
        fabricated_commit["repository_commit"] = "0" * 40
        with self.assertRaisesRegex(
            VERIFIER.EvidenceError,
            "does not exist as a commit",
        ):
            VERIFIER.validate_verifier_binding(fabricated_commit)

        fabricated_hash = dict(binding)
        fabricated_hash["sha256"] = "0" * 64
        with self.assertRaisesRegex(
            VERIFIER.EvidenceError,
            "source identity mismatch",
        ):
            VERIFIER.validate_verifier_binding(fabricated_hash)

    def test_retained_pending_receipt_state_is_stable_after_lifecycle_change(self) -> None:
        requirement = next(
            row for row in VERIFIER.PUBLIC_SITE_REQUIREMENTS
            if row["site_id"] == "project-shadow"
        )
        pages = VERIFIER.canonical_public_site_fixture(
            requirement,
            expected_capa_status="IMPLEMENTED_PENDING_EFFECTIVENESS",
        )
        status = json.loads(VERIFIER.CURRENT_STATUS.read_text(encoding="utf-8"))
        status["capa"]["status"] = "CLOSED_EFFECTIVE"
        with tempfile.TemporaryDirectory(prefix="shadow-replay-state-test-") as temp:
            mutated = Path(temp) / "status.json"
            mutated.write_text(json.dumps(status), encoding="utf-8")
            with mock.patch.object(VERIFIER, "CURRENT_STATUS", mutated):
                replayed = VERIFIER.public_site_semantic_checks(
                    requirement,
                    pages,
                    expected_capa_status="IMPLEMENTED_PENDING_EFFECTIVENESS",
                )
                live = VERIFIER.public_site_semantic_checks(requirement, pages)
        self.assertTrue(replayed["capa_state"])
        self.assertFalse(live["capa_state"])

    def test_hidden_script_text_cannot_satisfy_public_semantics(self) -> None:
        source = (
            "<html><body><script>R1.0.1 contains no Myth package; Generic Myth "
            "v0.2.0; Full-Canon Myth v0.3.5; separate optional default off "
            "nonauthorizing</script></body></html>"
        )
        text, links = VERIFIER.public_html_view(source)
        self.assertEqual(text, "")
        self.assertEqual(links, ())

    def test_public_boundary_adversarial_suite_executes_without_skips(self) -> None:
        execution = VERIFIER.validate_public_semantic_negative_controls()
        self.assertEqual(
            execution["executed_case_ids"],
            execution["expected_case_ids"],
        )
        self.assertEqual(
            execution["matched_expectation_count"],
            len(execution["expected_case_ids"]),
        )
        self.assertEqual(execution["failed_case_ids"], [])
        self.assertEqual(execution["skipped_case_ids"], [])
        self.assertIn("reverse_current", execution["expected_case_ids"])
        self.assertIn("identity_misbinding", execution["expected_case_ids"])
        self.assertIn("outside_band_role_reversal", execution["expected_case_ids"])
        self.assertIn("artifact_digit_prefix", execution["expected_case_ids"])
        self.assertIn("duplicate_semantic_attribute", execution["expected_case_ids"])
        self.assertIn("mismatched_semantic_markup", execution["expected_case_ids"])
        self.assertIn("outside_band_r1_not_current", execution["expected_case_ids"])
        self.assertIn(
            "outside_band_predecessor_still_current",
            execution["expected_case_ids"],
        )
        self.assertIn("unmarked_capa_is_now_closed", execution["expected_case_ids"])
        self.assertIn("unrelated_artifact_record", execution["expected_case_ids"])
        self.assertIn(
            "structured_dual_current_outside_band",
            execution["expected_case_ids"],
        )
        self.assertIn("unknown_shadow_marker", execution["expected_case_ids"])
        self.assertIn(
            "off_home_noncanonical_structured_claim",
            execution["expected_case_ids"],
        )
        self.assertIn(
            "arm_manual_missing_boundary_links",
            execution["expected_case_ids"],
        )

    def test_hidden_or_duplicate_boundary_contract_fails_closed(self) -> None:
        requirement = next(
            row for row in VERIFIER.PUBLIC_SITE_REQUIREMENTS
            if row["site_id"] == "pause-before-harm"
        )
        baseline = VERIFIER.canonical_public_site_fixture(requirement)
        baseline_checks = VERIFIER.public_site_semantic_checks(requirement, baseline)
        VERIFIER.require_complete_semantic_execution(
            "baseline fixture",
            VERIFIER.required_site_checks(requirement),
            baseline_checks,
        )

        hidden = dict(baseline)
        hidden["/"] = hidden["/"].replace(
            '<section class="public-release-band"',
            '<section aria-hidden="true" class="public-release-band"',
        )
        self.assertFalse(
            VERIFIER.public_site_semantic_checks(requirement, hidden)[
                "boundary_contract_unique"
            ]
        )

        duplicate = dict(baseline)
        duplicate["/"] = duplicate["/"].replace(
            "</body>",
            VERIFIER.canonical_public_boundary_band() + "</body>",
        )
        self.assertFalse(
            VERIFIER.public_site_semantic_checks(requirement, duplicate)[
                "boundary_contract_unique"
            ]
        )

    def test_reversed_sidecar_meaning_fails_even_with_positive_claim_retained(self) -> None:
        requirement = next(
            row for row in VERIFIER.PUBLIC_SITE_REQUIREMENTS
            if row["site_id"] == "pause-before-harm"
        )
        pages = VERIFIER.canonical_public_site_fixture(requirement)
        pages["/"] = pages["/"].replace(
            VERIFIER.PUBLIC_BOUNDARY_SHARED_CLAIM,
            VERIFIER.PUBLIC_BOUNDARY_SHARED_CLAIM
            + " The companions are not separate, not optional, mandatory, "
            "authorizing, and default-on.",
        )
        checks = VERIFIER.public_site_semantic_checks(requirement, pages)
        self.assertFalse(checks["boundary_no_contradictions"])

    def test_semantic_execution_reports_skipped_and_unexpected_checks(self) -> None:
        execution = VERIFIER.semantic_check_execution(
            ("expected_a", "expected_b"),
            {"expected_a": True, "unexpected": True},
        )
        self.assertEqual(execution["expected_count"], 2)
        self.assertEqual(execution["executed_count"], 1)
        self.assertEqual(execution["passed_count"], 1)
        self.assertEqual(execution["skipped_check_ids"], ["expected_b"])
        self.assertEqual(execution["unexpected_check_ids"], ["unexpected"])

    def test_satellite_direct_github_release_link_is_rejected(self) -> None:
        requirement = next(
            row for row in VERIFIER.PUBLIC_SITE_REQUIREMENTS
            if row["site_id"] == "pause-before-harm"
        )
        source = (
            '<p>R1.0.1 contains no Myth package. Generic Myth v0.2.0 and '
            'Full-Canon Myth v0.3.5 are separate optional default-off '
            'nonauthorizing companions.</p>'
            '<a href="https://projectshadow.frylock117.chatgpt.site/release">release</a>'
            '<a href="https://projectshadow.frylock117.chatgpt.site/capa">capa</a>'
            '<a href="https://github.com/PauseBeforeHarmProtocol/Project-Shadow/'
            'releases/tag/r1.0.1-2026-08-17">direct</a>'
        )
        checks = VERIFIER.public_site_semantic_checks(requirement, {"/": source})
        self.assertFalse(checks["no_direct_github_release_link"])

    def test_generic_exact_identity_mutation_fails_closed(self) -> None:
        manifest = json.loads(VERIFIER.PUBLICATION_MANIFEST.read_text(encoding="utf-8"))
        generic = next(
            row for row in manifest["releases"]
            if row["tag"] == "generic-myth-v0.2.0"
        )
        generic["asset"]["bytes"] = 1
        generic["asset"]["sha256"] = "0" * 64
        with tempfile.TemporaryDirectory(prefix="shadow-generic-pending-test-") as temp:
            mutated = Path(temp) / "PUBLICATION_MANIFEST.json"
            mutated.write_text(json.dumps(manifest), encoding="utf-8")
            with mock.patch.object(VERIFIER, "PUBLICATION_MANIFEST", mutated):
                with self.assertRaisesRegex(
                    VERIFIER.EvidenceError,
                    "release notes for generic-myth-v0.2.0 omit",
                ):
                    VERIFIER.verify_repository_metadata("POSTPUBLICATION")

    def test_outer_authorized_action_mutation_fails_closed(self) -> None:
        record = json.loads(VERIFIER.OUTER_AUTHORIZATION.read_text(encoding="utf-8"))
        record["authorized_actions"]["github_release"] = False
        with tempfile.TemporaryDirectory(prefix="shadow-outer-auth-test-") as temp:
            mutated = Path(temp) / "R1_0_1_OUTER_RELEASE_AUTHORIZATION.json"
            mutated.write_text(json.dumps(record), encoding="utf-8")
            with mock.patch.object(VERIFIER, "OUTER_AUTHORIZATION", mutated):
                with self.assertRaisesRegex(
                    VERIFIER.EvidenceError,
                    "outer authorization scope mismatch",
                ):
                    VERIFIER.verify_repository_metadata("POSTPUBLICATION")

    def test_generic_authorization_wording_mutation_fails_closed(self) -> None:
        record = json.loads(VERIFIER.GENERIC_AUTHORIZATION.read_text(encoding="utf-8"))
        record["maintainer_confirmation"]["statement"] += " altered"
        with tempfile.TemporaryDirectory(prefix="shadow-generic-auth-test-") as temp:
            mutated = Path(temp) / "GENERIC_AUTHORIZATION.json"
            mutated.write_text(json.dumps(record), encoding="utf-8")
            with mock.patch.object(VERIFIER, "GENERIC_AUTHORIZATION", mutated):
                with self.assertRaisesRegex(
                    VERIFIER.EvidenceError,
                    "Generic Myth maintainer confirmation wording mismatch",
                ):
                    VERIFIER.verify_repository_metadata("POSTPUBLICATION")

    def test_inner_admission_wording_mutation_fails_closed(self) -> None:
        record = json.loads(VERIFIER.INNER_ADMISSION.read_text(encoding="utf-8"))
        record["maintainer_confirmation"]["statement"] += " altered"
        with tempfile.TemporaryDirectory(prefix="shadow-inner-auth-test-") as temp:
            mutated = Path(temp) / "INNER_ADMISSION.json"
            mutated.write_text(json.dumps(record), encoding="utf-8")
            with mock.patch.object(VERIFIER, "INNER_ADMISSION", mutated):
                with self.assertRaisesRegex(
                    VERIFIER.EvidenceError,
                    "inner maintainer confirmation wording mismatch",
                ):
                    VERIFIER.verify_repository_metadata("POSTPUBLICATION")

    def test_generic_release_note_identity_removal_fails_closed(self) -> None:
        original_path = VERIFIER.RELEASE_NOTES["generic-myth-v0.2.0"]
        original = original_path.read_text(encoding="utf-8")
        mutated_text = original.replace(VERIFIER.GENERIC_FINAL["sha256"], "")
        with tempfile.TemporaryDirectory(prefix="shadow-generic-token-test-") as temp:
            mutated = Path(temp) / original_path.name
            mutated.write_text(mutated_text, encoding="utf-8")
            with mock.patch.dict(
                VERIFIER.RELEASE_NOTES,
                {"generic-myth-v0.2.0": mutated},
            ):
                with self.assertRaisesRegex(
                    VERIFIER.EvidenceError,
                    "release notes for generic-myth-v0.2.0 omit",
                ):
                    VERIFIER.verify_repository_metadata("POSTPUBLICATION")

    def test_rekor_documentation_mutation_fails_closed(self) -> None:
        original = VERIFIER.VERIFICATION_GUIDE.read_text(encoding="utf-8")
        mutated_text = original.replace(VERIFIER.REKOR_ENTRY_UUID, "0" * 80)
        self.assertNotEqual(mutated_text, original)
        with tempfile.TemporaryDirectory(prefix="shadow-rekor-doc-test-") as temp:
            mutated = Path(temp) / "VERIFY_RELEASES.md"
            mutated.write_text(mutated_text, encoding="utf-8")
            with mock.patch.object(VERIFIER, "VERIFICATION_GUIDE", mutated):
                with self.assertRaisesRegex(
                    VERIFIER.EvidenceError,
                    "required custody marker missing from verification guide",
                ):
                    VERIFIER.validate_public_documentation()

    def test_myth_authorization_link_mutation_fails_closed(self) -> None:
        original_path = VERIFIER.RELEASE_NOTES["myth-v0.3.4"]
        original = original_path.read_text(encoding="utf-8")
        mutated_text = original.replace(VERIFIER.AUTHORIZATION_JSON_URL, "")
        self.assertNotEqual(mutated_text, original)
        with tempfile.TemporaryDirectory(prefix="shadow-myth-link-test-") as temp:
            mutated = Path(temp) / original_path.name
            mutated.write_text(mutated_text, encoding="utf-8")
            with mock.patch.dict(
                VERIFIER.RELEASE_NOTES,
                {"myth-v0.3.4": mutated},
            ):
                with self.assertRaisesRegex(
                    VERIFIER.EvidenceError,
                    "required custody marker missing from Myth release notes",
                ):
                    VERIFIER.validate_public_documentation()

    def test_continuity_stale_date_mutation_fails_closed(self) -> None:
        original = VERIFIER.CONTINUITY_POLICY.read_text(encoding="utf-8")
        mutated_text = original.replace("2026-10-13", "DATE-REMOVED")
        self.assertNotEqual(mutated_text, original)
        with tempfile.TemporaryDirectory(prefix="shadow-continuity-test-") as temp:
            mutated = Path(temp) / "MAINTAINER_CONTINUITY.md"
            mutated.write_text(mutated_text, encoding="utf-8")
            with mock.patch.object(VERIFIER, "CONTINUITY_POLICY", mutated):
                with self.assertRaisesRegex(
                    VERIFIER.EvidenceError,
                    "required custody marker missing from maintainer continuity policy",
                ):
                    VERIFIER.validate_public_documentation()

    def test_true_nonclaim_boolean_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory(prefix="shadow-claims-test-") as temp:
            path = Path(temp) / "claim.json"
            path.write_text(
                json.dumps({"production_authorized": True}),  # permitted-claim-mutation-fixture
                encoding="utf-8",
            )
            findings = VERIFIER.prohibited_claim_findings([path])
        self.assertTrue(any("production_authorized=true" in row for row in findings))

    def test_positive_prose_claim_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory(prefix="shadow-claims-test-") as temp:
            path = Path(temp) / "claim.md"
            path.write_text("Project Shadow is production" + "-ready.\n", encoding="utf-8")
            findings = VERIFIER.prohibited_claim_findings([path])
        self.assertTrue(any("production" + "-ready" in row for row in findings))

    def test_positive_claim_in_citation_metadata_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory(prefix="shadow-claims-test-") as temp:
            path = Path(temp) / "CITATION.cff"
            path.write_text(
                "abstract: Project Shadow is production" + " software.\n",
                encoding="utf-8",
            )
            findings = VERIFIER.prohibited_claim_findings([path])
        self.assertTrue(any("production" + " software" in row for row in findings))

    def test_unmarked_positive_claim_in_test_source_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory(prefix="shadow-claims-test-") as temp:
            path = Path(temp) / "test_unrelated.py"
            path.write_text(
                'DESCRIPTION = "Project Shadow is production' + '-grade."\n',
                encoding="utf-8",
            )
            findings = VERIFIER.prohibited_claim_findings([path])
        self.assertTrue(any("production" + "-grade" in row for row in findings))

    def test_authenticated_github_api_request_uses_no_redirect_opener(self) -> None:
        response = mock.Mock()
        response.geturl.return_value = (
            "https://api.github.com/repos/PauseBeforeHarmProtocol/Project-Shadow/releases/latest"
        )
        opener = mock.Mock()
        opener.open.return_value = response
        with (
            mock.patch.dict(VERIFIER.os.environ, {"GITHUB_TOKEN": "test-token"}),
            mock.patch.object(VERIFIER.urllib.request, "build_opener", return_value=opener) as build,
            mock.patch.object(VERIFIER.urllib.request, "urlopen") as urlopen,
        ):
            returned = VERIFIER.request(response.geturl.return_value)
        self.assertIs(returned, response)
        build.assert_called_once_with(VERIFIER.RejectRedirects)
        urlopen.assert_not_called()
        request_object = opener.open.call_args.args[0]
        self.assertEqual(request_object.get_header("Authorization"), "Bearer test-token")
        self.assertIsNone(
            VERIFIER.RejectRedirects().redirect_request(
                request_object,
                None,
                302,
                "Found",
                {},
                "https://example.invalid/redirect",
            )
        )

    def test_explicit_nonclaim_is_allowed(self) -> None:
        with tempfile.TemporaryDirectory(prefix="shadow-claims-test-") as temp:
            path = Path(temp) / "nonclaim.md"
            path.write_text(
                "Project Shadow is not production-ready and is not certified.\n",
                encoding="utf-8",
            )
            findings = VERIFIER.prohibited_claim_findings([path])
        self.assertEqual(findings, [])

    def test_derived_publication_status_mutation_fails_closed(self) -> None:
        original = json.loads(VERIFIER.PUBLIC_STATUS.read_text(encoding="utf-8"))
        original["resolution"]["exact_public_artifacts_published"] = False
        with tempfile.TemporaryDirectory(prefix="shadow-status-test-") as temp:
            mutated = Path(temp) / "PUBLIC_RELEASE_STATUS_2026-08-14.json"
            mutated.write_text(json.dumps(original), encoding="utf-8")
            with mock.patch.object(VERIFIER, "PUBLIC_STATUS", mutated):
                with self.assertRaisesRegex(
                    VERIFIER.EvidenceError,
                    "resolved publication state",
                ):
                    VERIFIER.verify_repository_metadata()

    def test_derived_publication_status_missing_nonclaim_fails_closed(self) -> None:
        original = json.loads(VERIFIER.PUBLIC_STATUS.read_text(encoding="utf-8"))
        del original["nonclaims"]["production_authorized"]
        with tempfile.TemporaryDirectory(prefix="shadow-status-test-") as temp:
            mutated = Path(temp) / "PUBLIC_RELEASE_STATUS_2026-08-14.json"
            mutated.write_text(json.dumps(original), encoding="utf-8")
            with mock.patch.object(VERIFIER, "PUBLIC_STATUS", mutated):
                with self.assertRaisesRegex(
                    VERIFIER.EvidenceError,
                    "must explicitly set nonclaim false",
                ):
                    VERIFIER.verify_repository_metadata()


if __name__ == "__main__":
    unittest.main()
