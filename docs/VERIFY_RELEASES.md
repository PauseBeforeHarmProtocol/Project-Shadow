# Verify the exact Project Shadow releases

Do not rely on a filename alone. Verify both byte count and SHA-256 before
extracting an archive.

## Expected identities

| File | Bytes | SHA-256 |
|---|---:|---|
| `Project_Shadow_R1_Public_Release_Candidate_2026-08-14.zip` | 7,679,812 | `2f8fe1530b6a83294d15011df95853aaecf08fa4dba756f0c2e91dd089e1b1ec` |
| `Project_Shadow_Full_Canon_Myth_Sidecar_v0.3.4_OPTIONAL_EXTERNAL_RESEARCH_2026-08-14.zip` | 1,418,194 | `3c8c8c0d3d9582c76b685c1b685260cc8179478ab310037c858b46257aa314c7` |

## Windows PowerShell

```powershell
$r1 = ".\Project_Shadow_R1_Public_Release_Candidate_2026-08-14.zip"
$myth = ".\Project_Shadow_Full_Canon_Myth_Sidecar_v0.3.4_OPTIONAL_EXTERNAL_RESEARCH_2026-08-14.zip"

(Get-Item -LiteralPath $r1).Length
(Get-FileHash -LiteralPath $r1 -Algorithm SHA256).Hash.ToLowerInvariant()

(Get-Item -LiteralPath $myth).Length
(Get-FileHash -LiteralPath $myth -Algorithm SHA256).Hash.ToLowerInvariant()
```

## macOS or Linux

```bash
wc -c Project_Shadow_R1_Public_Release_Candidate_2026-08-14.zip
sha256sum Project_Shadow_R1_Public_Release_Candidate_2026-08-14.zip

wc -c Project_Shadow_Full_Canon_Myth_Sidecar_v0.3.4_OPTIONAL_EXTERNAL_RESEARCH_2026-08-14.zip
sha256sum Project_Shadow_Full_Canon_Myth_Sidecar_v0.3.4_OPTIONAL_EXTERNAL_RESEARCH_2026-08-14.zip
```

On macOS, `shasum -a 256` may be used when `sha256sum` is unavailable.

## Verify R1 after extraction

From the extracted R1 root:

```bash
python3 -I -S -B tools/verify_public_release.py .
```

The R1 verifier checks the exact admitted component identities, package member
allowlist, manifests, exclusion rules, signature bundle and independent
verification receipt, external-sidecar reference, archive safety controls, and
release scope. It does not make safety, efficacy, production, certification,
or legal-compliance claims.

The exact admission record, Sigstore bundle, and independent verification
receipt are also preserved under this repository's `governance/` directory.
The R1 archive's embedded verifier is the controlling packaged copy.

## Verify the optional sidecar after extraction

From the extracted sidecar root:

```bash
python3 -I -S -B tools/verify_package.py .
```

For the sidecar's full test and five-profile compatibility replay, first
extract the R1 archive, then supply its nested R1 family ZIP:

```bash
python3 -I -S -B tools/verify_package.py . --run-tests \
  --r1-family-zip /path/to/extracted-r1/05_COMPONENTS/R1/Project_Shadow_R1_BETA2_Runtime_Successor_Candidate_2026-08-10.zip
```

A verifier pass is integrity and compatibility evidence only. The sidecar
remains optional, default off, external, unadmitted, mixed-rights,
nonauthorizing, and outside R1 conformance.

