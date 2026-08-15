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

## Apply the current outer-archive preflight before extraction

The exact R1 ZIP is preserved and was not rewritten after publication. Its
embedded verifier is therefore also a frozen historical release artifact and
does not contain later verifier hardening committed to this public repository.
After the byte/hash check above, use a current checkout of this repository to
verify the **outer ZIP before extraction**:

```bash
python3 -I -S -B /path/to/Project-Shadow/tools/verify_public_release.py \
  /path/to/Project_Shadow_R1_Public_Release_Candidate_2026-08-14.zip
```

That current repository copy performs the prospective member-count,
cumulative-uncompressed-size, individual-compression-ratio, and
cumulative-compression-ratio metadata checks before reading ZIP members. Then
extract the archive and run its embedded verifier as described below. The
embedded copy remains controlling evidence of what shipped; the repository
copy adds post-publication verifier hardening without changing the released
bytes.

## Verify R1 after extraction: two distinct levels

The verifier has two deliberately different modes. The first validates the
exact preserved cryptographic evidence and the independent receipt. The second
also invokes Cosign now. A Level 1 pass must not be described as a fresh Cosign
execution.

### Level 1 — offline receipt-bound verification

From the extracted R1 root:

```bash
python3 -I -S -B tools/verify_public_release.py .
```

The R1 verifier checks the exact admitted component identities, package member
allowlist, manifests, exclusion rules, signature bundle and independent
verification receipt, external-sidecar reference, archive safety controls, and
release scope. It does not make safety, efficacy, production, certification,
or legal-compliance claims.

In this mode the verifier confirms that:

- the admission record, Sigstore bundle, and independent receipt have the exact
  expected byte counts and SHA-256 identities;
- the bundle targets the expected admission-record digest and contains a
  transparency-log entry and RFC 3161 timestamp; and
- the exact receipt records successful signature, transparency-log, and RFC
  3161 verification.

It does **not** execute Cosign. This level is receipt-bound verification that
can be performed offline after the files are obtained.

### Level 2 — fresh Sigstore/Cosign verification

Level 2 performs every Level 1 check and freshly runs `cosign verify-blob`
against the preserved admission record and bundle. The verifier deliberately
requires all six options together and checks that the supplied Cosign binary
and Sigstore trusted-root JSON match the exact identities recorded in the
independent receipt.

Expected verification inputs:

| Input | Exact expected value |
|---|---|
| Cosign executable platform | Linux/amd64, matching the independently preserved receipt |
| Cosign executable SHA-256 | `4629c757b7618056f8ddd7e2625ae9fdd94c0372a65049520bc7d9df9efc7f71` |
| Sigstore TrustedRoot JSON SHA-256 | `6494e21ea73fa7ee769f85f57d5a3e6a08725eae1e38c755fc3517c9e6bc0b66` |
| Certificate identity | `pausebeforeharmprotocol_PBHP@protonmail.com` |
| Certificate OIDC issuer | `https://github.com/login/oauth` |

The public Rekor entry for the exact admission record is:

| Rekor field | Exact value |
|---|---|
| Log index | `2465982078` |
| Entry UUID | `108e9186e8c5677a5ce4e9ea6d6aaf7b7a6aabe12b6a3f0d9202da3ede22684c3c90780f2f313a79` |
| Public lookup | [Open the entry in Sigstore Search](https://search.sigstore.dev/?logIndex=2465982078) |

The public lookup is a convenient inspection path, not a substitute for
verifying the preserved bundle against the exact admission record.

From the extracted R1 root on Linux/amd64 (or Windows via WSL on an amd64
machine), replace the first two paths with independently obtained local files
whose hashes match the table:

```bash
python3 -I -S -B tools/verify_public_release.py . \
  --cosign /absolute/path/to/cosign \
  --expected-cosign-sha256 4629c757b7618056f8ddd7e2625ae9fdd94c0372a65049520bc7d9df9efc7f71 \
  --trusted-root /absolute/path/to/trusted-root.json \
  --expected-trusted-root-sha256 6494e21ea73fa7ee769f85f57d5a3e6a08725eae1e38c755fc3517c9e6bc0b66 \
  --certificate-identity 'pausebeforeharmprotocol_PBHP@protonmail.com' \
  --certificate-oidc-issuer 'https://github.com/login/oauth'
```

After separately confirming the pinned Cosign and trusted-root hashes above,
the corresponding direct Level 2 Cosign command is:

```bash
cosign verify-blob \
  --bundle governance/PROJECT_SHADOW_FABLE7_SCOPED_MAINTAINER_ADMISSION_RECORD_2026-08-12.json.sigstore.json \
  --trusted-root /absolute/path/to/trusted-root.json \
  --use-signed-timestamps \
  --certificate-identity 'pausebeforeharmprotocol_PBHP@protonmail.com' \
  --certificate-oidc-issuer 'https://github.com/login/oauth' \
  governance/PROJECT_SHADOW_FABLE7_SCOPED_MAINTAINER_ADMISSION_RECORD_2026-08-12.json
```

That raw command does not itself confirm the Cosign executable hash or the
trusted-root file hash. The repository verifier invocation above performs
those two pin checks before it launches the same `cosign verify-blob` command;
prefer the wrapper when reproducing the independently preserved verification.

On Windows, run that same Linux/amd64 command inside WSL from the extracted R1
directory. Do not substitute native `cosign.exe`: it is a different binary
with a different SHA-256, while this preserved independent receipt pins the
Linux/amd64 executable actually used in the review. A native-Windows Level 2
path would require its own independently verified receipt and exact binary
pin. The same applies to a native macOS Cosign binary. Level 1 remains
platform-independent.

Before running Level 2, independently hash both supplied files. Do not
substitute a different or merely newer Cosign executable or trusted-root file;
the verifier will reject a mismatch. The verifier does not download either
dependency. A successful fresh run prints
`PASS: live Cosign identity/signature/RFC3161 verification`.

The exact admission record, Sigstore bundle, and independent verification
receipt are also preserved under this repository's `governance/` directory.
The R1 archive's embedded verifier is the controlling packaged copy for the
historical release. The current repository verifier should be used first on the
outer ZIP for the later archive-preflight protections documented above.

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
