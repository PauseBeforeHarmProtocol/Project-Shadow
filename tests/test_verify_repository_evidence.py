from __future__ import annotations

import importlib.util
import hashlib
import json
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
    def test_current_repository_metadata_agrees(self) -> None:
        self.assertGreaterEqual(VERIFIER.parse_all_json(), 1)
        rows = VERIFIER.verify_repository_metadata("PREPUBLICATION")
        self.assertEqual([row["order"] for row in rows], [1, 2, 3, 4, 5])
        self.assertEqual(
            [row["tag"] for row in VERIFIER.published_rows(rows)],
            ["myth-v0.3.4", "r1-2026-08-14", "myth-v0.3.5"],
        )
        self.assertEqual(VERIFIER.prohibited_claim_findings(), [])

    def test_historical_public_release_verifier_remains_byte_pinned(self) -> None:
        digest = hashlib.sha256(
            (ROOT / "tools" / "verify_public_release.py").read_bytes()
        ).hexdigest()
        self.assertEqual(
            digest,
            "f1358db6c824319501d0eabf341174eb96217e5d2545d9ac908a81d338c8afa8",
        )

    def test_ready_prepublication_has_no_release_placeholders(self) -> None:
        self.assertEqual(VERIFIER.release_placeholder_findings(), [])

    def test_postpublication_mode_rejects_prepublication_manifest(self) -> None:
        with self.assertRaisesRegex(VERIFIER.EvidenceError, "manifest phase mismatch"):
            VERIFIER.verify_repository_metadata("POSTPUBLICATION")

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
                    VERIFIER.verify_repository_metadata("PREPUBLICATION")

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
                    VERIFIER.verify_repository_metadata("PREPUBLICATION")

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
                    VERIFIER.verify_repository_metadata("PREPUBLICATION")

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
                    VERIFIER.verify_repository_metadata("PREPUBLICATION")

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
                    VERIFIER.verify_repository_metadata("PREPUBLICATION")

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
