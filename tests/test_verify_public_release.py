from __future__ import annotations

import importlib.util
import shutil
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "verify_public_release",
    ROOT / "tools" / "verify_public_release.py",
)
if SPEC is None or SPEC.loader is None:  # pragma: no cover - import setup guard
    raise RuntimeError("could not load tools/verify_public_release.py")
VERIFIER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VERIFIER)


class ArchivePreflightTests(unittest.TestCase):
    def make_zip(
        self,
        entries: dict[str, bytes],
        *,
        compression: int = zipfile.ZIP_STORED,
    ) -> Path:
        temp_dir = Path(tempfile.mkdtemp(prefix="shadow-archive-test-"))
        self.addCleanup(shutil.rmtree, temp_dir)
        path = temp_dir / "fixture.zip"
        with zipfile.ZipFile(path, "w", compression=compression) as archive:
            for name, data in entries.items():
                archive.writestr(name, data)
        return path

    def assert_rejected_before_read(
        self,
        path: Path,
        expected_message: str,
    ) -> None:
        with mock.patch.object(
            zipfile.ZipFile,
            "read",
            side_effect=AssertionError("archive.read() ran before metadata rejection"),
        ):
            with self.assertRaisesRegex(VERIFIER.VerificationError, expected_message):
                VERIFIER.load_target(path)

    def test_safe_archive_passes_preflight_and_loads(self) -> None:
        path = self.make_zip(
            {"root/a.txt": b"alpha", "root/b.txt": b"beta"},
            compression=zipfile.ZIP_STORED,
        )
        with (
            mock.patch.object(VERIFIER, "MAX_ARCHIVE_MEMBERS", 3),
            mock.patch.object(VERIFIER, "MAX_ARCHIVE_UNCOMPRESSED_BYTES", 20),
            mock.patch.object(VERIFIER, "MAX_INDIVIDUAL_COMPRESSION_RATIO", 2.0),
            mock.patch.object(VERIFIER, "MAX_CUMULATIVE_COMPRESSION_RATIO", 2.0),
        ):
            self.assertEqual(
                VERIFIER.load_target(path),
                {"a.txt": b"alpha", "b.txt": b"beta"},
            )

    def test_member_count_limit_fails_closed_before_read(self) -> None:
        path = self.make_zip(
            {"root/a": b"a", "root/b": b"b", "root/c": b"c"}
        )
        with mock.patch.object(VERIFIER, "MAX_ARCHIVE_MEMBERS", 2):
            self.assert_rejected_before_read(path, "member-count limit exceeded")

    def test_cumulative_uncompressed_limit_fails_closed_before_read(self) -> None:
        path = self.make_zip({"root/a": b"a" * 8, "root/b": b"b" * 8})
        with mock.patch.object(VERIFIER, "MAX_ARCHIVE_UNCOMPRESSED_BYTES", 15):
            self.assert_rejected_before_read(
                path,
                "cumulative uncompressed-size limit exceeded",
            )

    def test_individual_compression_ratio_fails_closed_before_read(self) -> None:
        path = self.make_zip(
            {"root/compressible.txt": b"a" * 10_000},
            compression=zipfile.ZIP_DEFLATED,
        )
        with (
            mock.patch.object(VERIFIER, "MAX_INDIVIDUAL_COMPRESSION_RATIO", 2.0),
            mock.patch.object(VERIFIER, "MAX_CUMULATIVE_COMPRESSION_RATIO", 1_000.0),
        ):
            self.assert_rejected_before_read(
                path,
                "member compression-ratio limit exceeded",
            )

    def test_cumulative_compression_ratio_fails_closed_before_read(self) -> None:
        path = self.make_zip(
            {
                "root/compressible-a.txt": b"a" * 10_000,
                "root/compressible-b.txt": b"b" * 10_000,
            },
            compression=zipfile.ZIP_DEFLATED,
        )
        with (
            mock.patch.object(VERIFIER, "MAX_INDIVIDUAL_COMPRESSION_RATIO", 1_000.0),
            mock.patch.object(VERIFIER, "MAX_CUMULATIVE_COMPRESSION_RATIO", 2.0),
        ):
            self.assert_rejected_before_read(
                path,
                "cumulative compression-ratio limit exceeded",
            )

    def test_directory_payload_fails_closed_before_read_or_crc_scan(self) -> None:
        path = self.make_zip(
            {"root/bomb/": b"a" * 10_000},
            compression=zipfile.ZIP_DEFLATED,
        )
        with mock.patch.object(
            zipfile.ZipFile,
            "testzip",
            side_effect=AssertionError("testzip() ran before metadata rejection"),
        ):
            self.assert_rejected_before_read(
                path,
                "directory ZIP member carries payload bytes",
            )


if __name__ == "__main__":
    unittest.main()
