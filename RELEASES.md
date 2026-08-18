# Releases

Release assets are kept out of Git history and attached to separate GitHub
Releases. Automatically generated source ZIP/TAR archives are repository
snapshots, not Project Shadow release artifacts.

## Current public releases

Publication phase: **POSTPUBLICATION**. Packaging-correction effectiveness is
verified.

1. `generic-myth-v0.2.0` — Generic Myth Sidecar v0.2.0, optional public
   companion. Its final identity is frozen, its final tests pass, and its exact
   hash is published separately on GitHub and Hugging Face.
2. `r1.0.1-2026-08-17` — Project Shadow 1.0.1 R1 reference packaging
   correction. Its exact inner is admitted and its deterministic outer build is
   frozen, separately exact-hash authorized, and published on GitHub and
   Hugging Face.

The Generic sidecar was published first. R1.0.1 was published last so the
corrected R1 is the latest release. Subsequent anonymous GitHub and Hugging
Face redownloads, bounded package verification, and all six public-site checks
passed; the packaging-boundary CAPA is `CLOSED_EFFECTIVE`.

## Existing public releases

- `myth-v0.3.5` — Full-Canon Myth Sidecar v0.3.5, optional public companion.
- `myth-v0.3.4` — preserved historical optional research sidecar.
- `r1-2026-08-14` — preserved historical R1 release. Its bytes are immutable;
  R1.0.1 supersedes it as the current reference because the old outer package
  included a nested Generic Myth v0.1.1 member carrying non-public metadata.

Historical release notes and governance records remain in place. Nothing in
the 2026-08-17 correction back-writes the August 14 authorization, status,
redownload receipt, tags, or archive.

Files under `release-notes/` are content-aligned publication-time snapshots of
the live GitHub release bodies (line endings and trailing Markdown spaces are
normalized). Any open/pending CAPA wording retained there records the
then-current release-time state; current lifecycle status is defined only by
`PUBLIC_RELEASE_STATUS_2026-08-17.json`, `PUBLICATION_MANIFEST.json`, and the
two retained effectiveness receipts.

## Completed effectiveness sequence

1. The recorded Generic, inner, and outer exact-hash authorities were
   preserved without broadening them.
2. GitHub and Hugging Face copies of Generic v0.2.0 and R1.0.1 were anonymously
   redownloaded and matched their exact byte counts and SHA-256 values.
3. Both downloaded Generic archives passed the bounded 23-path verifier, and
   R1.0.1 passed recursive zero-Myth verification.
4. All six public sites passed the corrected-boundary semantic checks,
   including the current Project Shadow status surface and the National Trump
   Record route.
5. CAPA `PS-R1-PRIVATE-MYTH-PUBLIC-BOUNDARY-001` was closed effective on the
   retained redownload and six-site receipts.

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
