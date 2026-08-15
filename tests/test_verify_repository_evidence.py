from __future__ import annotations

import importlib.util
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
        rows = VERIFIER.verify_repository_metadata()
        self.assertEqual([row["order"] for row in rows], [1, 2])
        self.assertEqual(VERIFIER.prohibited_claim_findings(), [])

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
