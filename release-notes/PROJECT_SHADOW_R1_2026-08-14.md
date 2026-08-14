# Project Shadow 1.0 — R1 Reference (PRELIVE)

**Tag:** `r1-2026-08-14`  
**Release identity:** `PROJECT SHADOW 1.0 / R1 REFERENCE / BETA-ACTIVE-TESTING / PRELIVE`  
**Asset:** `Project_Shadow_R1_Public_Release_Candidate_2026-08-14.zip`  
**Bytes:** 7,679,812  
**SHA-256:** `2f8fe1530b6a83294d15011df95853aaecf08fa4dba756f0c2e91dd089e1b1ec`

This is the exact-hash authorized canonical R1 reference archive. Its immutable
filename and internal status retain the build-time word `Candidate`; the later
external authorization recorded in
`governance/RELEASE_AUTHORIZATION_2026-08-14.json` satisfies the publication
gate for these exact bytes without rewriting the archive.

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
extraction, run:

```bash
python3 -I -S -B tools/verify_public_release.py .
```

This release does not authorize production or operational deployment,
efficacy, safety, certification, legal-compliance claims, or expansion beyond
the stated scope.

Publish this release after the sidecar and mark it as the latest release.

