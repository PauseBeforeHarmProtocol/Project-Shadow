# Releases

Release assets are kept out of Git history and attached to separate GitHub
Releases. Automatically generated source ZIP/TAR archives are repository
snapshots, not Project Shadow release artifacts.

## Current release plan

Publication phase: **PREPUBLICATION**.

1. `generic-myth-v0.2.0` — Generic Myth Sidecar v0.2.0, optional public
   companion. Its final identity is frozen, its final tests pass, and its exact
   hash is authorized for separate GitHub and Hugging Face publication.
2. `r1.0.1-2026-08-17` — Project Shadow 1.0.1 R1 reference packaging
   correction. Its exact inner is admitted and its deterministic outer build is
   frozen and separately exact-hash authorized. It is ready to publish, not yet
   published.

The Generic sidecar must be published first. R1.0.1 must be published last so
the corrected R1 becomes the latest release. Neither pending release is marked
published in repository evidence before the public asset exists.

## Existing public releases

- `myth-v0.3.5` — Full-Canon Myth Sidecar v0.3.5, optional public companion.
- `myth-v0.3.4` — preserved historical optional research sidecar.
- `r1-2026-08-14` — preserved historical R1 release. Its bytes are immutable;
  R1.0.1 supersedes it as the current reference because the old outer package
  included a nested Generic Myth v0.1.1 member carrying non-public metadata.

Historical release notes and governance records remain in place. Nothing in
the 2026-08-17 correction back-writes the August 14 authorization, status,
redownload receipt, tags, or archive.

## Required publication sequence

1. Preserve the recorded Generic, inner, and outer exact-hash authorities
   without broadening them.
2. Run `tools/verify_repository_evidence.py --phase prepublication`.
3. Publish Generic v0.2.0, then R1.0.1.
4. Anonymously redownload the GitHub and Hugging Face assets and verify exact
   byte counts and SHA-256 values.
5. Verify all six public sites, add the redownload record, close the CAPA, and
   run postpublication mode.

## Prospective custody procedure

Future release tags should be signed annotated tags from the intended verified
commit. Release assets must not be replaced after publication. GitHub release
immutability and tag protection do not rewrite the original August 14 tags.

```bash
git tag -s <release-tag> -m "<release title>" <verified-commit-sha>
git tag -v <release-tag>
git push origin <release-tag>
```

For questions or corrections, use `projectshadowqa@protonmail.com` with the
subject prefix described in
[`CONTACT_AND_CORRECTIONS.md`](CONTACT_AND_CORRECTIONS.md).
