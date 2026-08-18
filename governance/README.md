# Governance evidence

This directory separates governance and custody evidence:

1. The exact admission record, its Sigstore bundle, and the independent
   signature-verification receipt establish the signature and external-time
   gates for the admitted record.
2. `RELEASE_AUTHORIZATION_2026-08-14.json` records the later, separate
   maintainer authorization for the exact R1 and v0.3.4 sidecar hashes.
3. The top-level `PUBLIC_RELEASE_STATUS_2026-08-14.json` resolves those two
   states without changing the preserved candidate gate: the internal gate is
   open by design, separate human authorization is present, and the exact
   artifacts are published.
4. `PUBLIC_REDOWNLOAD_VERIFICATION_2026-08-15.json` records the later anonymous
   redownload and matching byte-count/SHA-256 observations for both artifacts.
5. [`POST_PUBLICATION_ATTESTATION_2026-08-15.json`](POST_PUBLICATION_ATTESTATION_2026-08-15.json)
   records the historical
   unsigned commit and lightweight-tag facts, publication order, and exact
   public identities without rewriting them. Its signature binding is the
   first `main` commit containing that exact record and is valid only when
   GitHub displays that introducing commit as **Verified**.
6. [`MAINTAINER_CONTINUITY.md`](MAINTAINER_CONTINUITY.md) records sole human
   authority, the absence of a designated successor, the non-authority of AI
   and automation, and the fail-closed stale-after date without changing any
   historical release.

## 2026-08-17 packaging-boundary correction

The records below are additive. They do not modify the frozen August 14
admission, signature bundle, authorization, derived status, redownload
verification, or postpublication attestation.

7. [`PROJECT_SHADOW_GENERIC_MYTH_v0.2.0_PUBLIC_RELEASE_REFERENCE.json`](PROJECT_SHADOW_GENERIC_MYTH_v0.2.0_PUBLIC_RELEASE_REFERENCE.json)
   defines the Generic Myth v0.2.0 external/default-off boundary and publication
   targets and binds its frozen final identity.
8. [`GENERIC_MYTH_v0.2.0_BUILD_AND_TEST_REPORT_2026-08-17.json`](GENERIC_MYTH_v0.2.0_BUILD_AND_TEST_REPORT_2026-08-17.json)
   records the passing final hardened tests for that frozen identity.
9. [`GENERIC_MYTH_v0.2.0_EXACT_HASH_PUBLIC_RELEASE_AUTHORIZATION_2026-08-17.json`](GENERIC_MYTH_v0.2.0_EXACT_HASH_PUBLIC_RELEASE_AUTHORIZATION_2026-08-17.json)
   records the maintainer's exact wording authorizing only that Generic artifact
   for separate GitHub and Hugging Face publication.
10. [`R1_0_1_INNER_EXACT_HASH_ADMISSION_2026-08-17.json`](R1_0_1_INNER_EXACT_HASH_ADMISSION_2026-08-17.json)
    records the maintainer's scoped exact-hash inner admission and exact submitted
    wording. It does not authorize production, deployment, or publication.
11. [`R1_0_1_OUTER_RELEASE_AUTHORIZATION_2026-08-17.json`](R1_0_1_OUTER_RELEASE_AUTHORIZATION_2026-08-17.json)
    records the maintainer's exact wording authorizing the separately built
    final outer archive and corresponding repository/site updates.
12. [`CAPA_PS-R1-PRIVATE-MYTH-PUBLIC-BOUNDARY-001_2026-08-17.json`](CAPA_PS-R1-PRIVATE-MYTH-PUBLIC-BOUNDARY-001_2026-08-17.json)
    records the corrective design as implemented pending effectiveness. Closure
    requires final identity binding, anonymous GitHub and Hugging Face
    redownload verification, recursive zero-Myth verification, and corrected
    wording on all six public sites.

Concrete identity fields are not self-authorizing; the separate authority
records supply the scoped decisions. Generic Myth v0.2.0 and R1.0.1 are now
published on GitHub and Hugging Face, but publication is not CAPA effectiveness
evidence. `tools/verify_repository_evidence.py --phase postpublication`
therefore validates the published identities while preserving
`IMPLEMENTED_PENDING_EFFECTIVENESS` until anonymous redownload and six-site
criteria are evidenced.

The signed admission record did not self-authorize public release. The later
authorization does not modify the signed record or the exact R1 archive; it
satisfies the external publication gate for the named artifacts only.

## Exact evidence identities

| Evidence | Bytes | SHA-256 |
|---|---:|---|
| Admission record | 217,626 | `659d15bf371a1c2b8410d39c040733da43779fbe54730c43140e1d06dc70b424` |
| Sigstore bundle | 6,770 | `a579f1b855ad22eb58be4ece5a580edbff60a171b35517b15ee172e417faaba0` |
| Independent verification receipt | 1,625 | `62e3965891b0f0a11aa46b50854f467acef84645faa569419fc79cf1051c1629` |
| Public-release authorization receipt | 1,995 | `af9e049c73b57224aaa49683908ff8cdd33d744aa538c89f883ee6c75ab2f547` |

The public-release authorization receipt is a session record and makes no
claim of having its own cryptographic signature.
