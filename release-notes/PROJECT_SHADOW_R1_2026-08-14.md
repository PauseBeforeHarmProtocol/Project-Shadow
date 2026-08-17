**Public PRELIVE reference only—not production or operational software.**

# Project Shadow 1.0 — R1 Reference (PRELIVE)

**Tag:** `r1-2026-08-14`  
**Release identity:** `PROJECT SHADOW 1.0 / R1 REFERENCE / BETA-ACTIVE-TESTING / PRELIVE`  
**Asset:** `Project_Shadow_R1_Public_Release_Candidate_2026-08-14.zip`  
**Bytes:** 7,679,812  
**SHA-256:** `2f8fe1530b6a83294d15011df95853aaecf08fa4dba756f0c2e91dd089e1b1ec`  
**Current contact:** `projectshadowqa@protonmail.com`

Use `[CORRECTION]`, `[CAPA]`, `[SECURITY]`, `[RESEARCH]`, `[PRESS]`, or
`[COLLABORATION]` in the subject line. See
[`CONTACT_AND_CORRECTIONS.md`](../CONTACT_AND_CORRECTIONS.md).

This is the exact-hash authorized canonical R1 reference archive. Its preserved
filename and internal status retain the build-time word `Candidate`; the later
external authorization recorded in the commit-pinned [human-readable
receipt][authorization-receipt] and [machine-readable
record][authorization-json] satisfies the publication gate for these exact
bytes without rewriting the archive.

The package contains:

- exact admitted R1 Beta2 family root SHA-256
  `075b41ea4186b2d2edb0ed246ab7662cf8bbdf3160294e3eca176b9d0857b108`;
- exact Primitive Commons beta.5 family root SHA-256
  `1ffdba41025c0b81da92d0bbb22d0eaa69488cffbc80936365034669110448d7`;
- the exact admission record and Sigstore evidence;
- the independent signature-verification receipt; and
- public governance, audit, rights, limitation, manifest, checksum, and
  verification material.

The optional v0.3.4 external research sidecar is not embedded. It is distributed
separately under its own mixed-rights terms and remains default off, unadmitted,
and outside R1 conformance.

Verify the downloaded file against both the byte count and SHA-256 above. After
that check, a current checkout of this repository can apply the prospective
outer-archive preflight before extraction:

```bash
python3 -I -S -B tools/verify_public_release.py \
  /path/to/Project_Shadow_R1_Public_Release_Candidate_2026-08-14.zip
```

The exact ZIP and its embedded verifier remain frozen historical artifacts;
the repository verifier adds later archive-safety limits without rewriting the
release. After extraction, run the packaged verifier:

```bash
python3 -I -S -B tools/verify_public_release.py .
```

For fresh Level 2 cryptographic verification, the admission record's Rekor log
index is `2465982078` and its entry UUID is
`108e9186e8c5677a5ce4e9ea6d6aaf7b7a6aabe12b6a3f0d9202da3ede22684c3c90780f2f313a79`.
[Inspect that exact entry in Sigstore Search](https://search.sigstore.dev/?logIndex=2465982078),
then run from the extracted R1 root:

```bash
cosign verify-blob \
  --bundle governance/PROJECT_SHADOW_FABLE7_SCOPED_MAINTAINER_ADMISSION_RECORD_2026-08-12.json.sigstore.json \
  --trusted-root /absolute/path/to/trusted-root.json \
  --use-signed-timestamps \
  --certificate-identity 'pausebeforeharmprotocol_PBHP@protonmail.com' \
  --certificate-oidc-issuer 'https://github.com/login/oauth' \
  governance/PROJECT_SHADOW_FABLE7_SCOPED_MAINTAINER_ADMISSION_RECORD_2026-08-12.json
```

The certificate identity above is the frozen historical signing identity in the
preserved Sigstore evidence. It is required for verification and is **not** the
current Project Shadow contact mailbox. Do not replace it with
`projectshadowqa@protonmail.com` in the verification command.

Before using that direct command, separately confirm the Linux/amd64 Cosign
SHA-256 `4629c757b7618056f8ddd7e2625ae9fdd94c0372a65049520bc7d9df9efc7f71`
and trusted-root SHA-256
`6494e21ea73fa7ee769f85f57d5a3e6a08725eae1e38c755fc3517c9e6bc0b66`.
The raw command does not enforce those file hashes; the [full two-level
guide](https://github.com/PauseBeforeHarmProtocol/Project-Shadow/blob/main/docs/VERIFY_RELEASES.md)
documents the repository wrapper that does.

Download the named release asset above. Do **not** substitute GitHub's
automatically generated “Source code (zip)” or “Source code (tar.gz)” archives;
those are repository snapshots, not the authorized R1 release archive.

This release does not authorize production or operational deployment,
efficacy, safety, certification, legal-compliance claims, or expansion beyond
the stated scope.

[authorization-receipt]: https://github.com/PauseBeforeHarmProtocol/Project-Shadow/blob/93bde4f2fd4b7b8824622150a03a14cbf5b4b30e/governance/RELEASE_AUTHORIZATION_2026-08-14.md
[authorization-json]: https://github.com/PauseBeforeHarmProtocol/Project-Shadow/blob/93bde4f2fd4b7b8824622150a03a14cbf5b4b30e/governance/RELEASE_AUTHORIZATION_2026-08-14.json
