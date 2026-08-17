# Releases

Release assets are intentionally kept out of Git history and attached to two
separate GitHub Releases.

1. `myth-v0.3.4` — **Project Shadow Myth Sidecar v0.3.4 — Optional External Research**
2. `r1-2026-08-14` — **Project Shadow 1.0 — R1 Reference (PRELIVE)**

The sidecar was published first. R1 was published last and is the latest
release. Neither release is marked as a GitHub prerelease: both exact artifacts
are publicly released, while the controlling `BETA-ACTIVE-TESTING / PRELIVE`
scope label explicitly withholds production and operational authority. That
scope label must remain visible in the R1 title and notes.

Always download the explicitly named release assets. GitHub's automatically
generated source-code ZIP and TAR archives are repository snapshots, not the
authorized R1 or sidecar artifacts.

Exact filenames, sizes, hashes, and ordering are machine-readable in
[`PUBLICATION_MANIFEST.json`](PUBLICATION_MANIFEST.json).

## Current contact

For release questions, corrections, CAPA proposals, research, press,
collaboration, or security routing, use `projectshadowqa@protonmail.com` with
the subject prefix described in
[`CONTACT_AND_CORRECTIONS.md`](CONTACT_AND_CORRECTIONS.md).

Historical addresses and signing identities in exact-hash archives, signed
records, certificates, tags, commits, and verification commands remain
preserved evidence. They are not current correspondence routes.

## Prospective custody procedure

The two 2026-08-14 tags are preserved lightweight tags pointing to the original
public commit. They are historical facts and must not be rewritten merely to
retrofit later controls.

For every future release:

1. land the release record through the protected `main` pull-request and CI
   path;
2. create a signed annotated tag from the intended verified commit;
3. verify that tag locally before pushing it;
4. publish exact-hash-authorized assets without replacing them afterward; and
5. anonymously download each public asset and record its byte count and
   SHA-256.

Example maintainer commands:

```bash
git tag -s <release-tag> -m "<release title>" <verified-commit-sha>
git tag -v <release-tag>
git push origin <release-tag>
```

A release-tag ruleset must protect the release-tag patterns prospectively.
GitHub's release-immutability setting is also prospective and does not rewrite
or retroactively relabel the two original releases.
