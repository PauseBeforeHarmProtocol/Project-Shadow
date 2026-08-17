# Security policy

Project Shadow is released only as a PRELIVE reference and beta-active-testing
artifact. It is not authorized for production or operational deployment.

For a suspected vulnerability in this repository or either exact release
artifact, use [GitHub private vulnerability
reporting](https://github.com/PauseBeforeHarmProtocol/Project-Shadow/security/advisories/new).
If that private reporting surface is unavailable, email
`projectshadowqa@protonmail.com` with the subject prefix `[SECURITY]`.

We aim to acknowledge a private report within **seven calendar days**. This is
an acknowledgment target, not a promise of resolution or a statement about
severity.

Do not put secrets, personal data, exploit details, or private evidence in a
public issue. A public issue may say only that a private report was submitted
and identify a non-sensitive component. Use a synthetic reproduction whenever
possible; arrange a private transfer method before sending sensitive evidence.

Include:

- the exact artifact filename and SHA-256;
- the affected path or component;
- minimal reproduction steps using synthetic data;
- expected and observed behavior; and
- whether the issue reproduces after the package's embedded verifier passes.

Do not send passwords, one-time codes, authenticator seeds, recovery codes,
private keys, protected health information, or unnecessary personal data.

Historical email addresses and certificate identities may remain in exact-hash
archives, signed records, commits, tags, and verification commands. They are
preserved evidence, not current security mailboxes. Do not replace a preserved
certificate identity in a Cosign command with the current contact address.

The full contact, correction, and CAPA routing policy is in
[`CONTACT_AND_CORRECTIONS.md`](CONTACT_AND_CORRECTIONS.md).

A verification pass establishes only the checks implemented by that verifier.
It is not a safety, efficacy, certification, production-readiness, or
legal-compliance claim.
