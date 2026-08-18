# Releases

Release assets are kept out of Git history and attached to separate GitHub
Releases. Automatically generated source ZIP/TAR archives are repository
snapshots, not Project Shadow release artifacts.

## Current public releases

Publication phase: **POSTPUBLICATION**. Effectiveness verification remains
pending.

1. `generic-myth-v0.2.0` — Generic Myth Sidecar v0.2.0, optional public
   companion. Its final identity is frozen, its final tests pass, and its exact
   hash is published separately on GitHub and Hugging Face.
2. `r1.0.1-2026-08-17` — Project Shadow 1.0.1 R1 reference packaging
   correction. Its exact inner is admitted and its deterministic outer build is
   frozen, separately exact-hash authorized, and published on GitHub and
   Hugging Face.

The Generic sidecar was published first. R1.0.1 was published last so the
corrected R1 is the latest release. Publication does not by itself verify
anonymous redownload identity or close the packaging-boundary CAPA.

## Existing public releases

- `myth-v0.3.5` — Full-Canon Myth Sidecar v0.3.5, optional public companion.
- `myth-v0.3.4` — preserved historical optional research sidecar.
- `r1-2026-08-14` — preserved historical R1 release. Its bytes are immutable;
  R1.0.1 supersedes it as the current reference because the old outer package
  included a nested Generic Myth v0.1.1 member carrying non-public metadata.

Historical release notes and governance records remain in place. Nothing in
the 2026-08-17 correction back-writes the August 14 authorization, status,
redownload receipt, tags, or archive.

## Remaining effectiveness sequence

1. Preserve the recorded Generic, inner, and outer exact-hash authorities
   without broadening them.
2. Run `tools/verify_repository_evidence.py --phase postpublication`.
3. Anonymously redownload the GitHub and Hugging Face assets and verify exact
   byte counts and SHA-256 values.
4. Verify all six public sites and add the redownload/effectiveness record.
5. Close the CAPA only if every effectiveness criterion passes.

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
