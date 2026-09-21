# Security policy — Owlet Home Assistant integration

This independent community continuation is maintained by
[Rogash1](https://github.com/Rogash1). It is experimental and not production-ready.
No formal security audit, vulnerability-free status or manufacturer endorsement
is claimed. See [SECURITY-REVIEW.md](SECURITY-REVIEW.md).

## Supported versions

Only the current maintenance branch and candidate **2026.9.20rc1** are considered
for fixes in this fork, on a best-effort basis. The candidate has not yet been
published as a release asset. Older upstream/fork versions are not supported by
this maintainer. No response-time or patch-delivery SLA is offered.

## Reporting a vulnerability

Use **Security > Report a vulnerability** on
[the maintained repository](https://github.com/Rogash1/owlet/security) if private
reporting is available. Its availability is not assumed or claimed enabled.
If that option is absent, open a minimal issue requesting a private security
contact, without exploit details or sensitive data; the maintainer must arrange
a private channel before you send the report. Do not post passwords, account
emails, access/refresh tokens, raw device responses, device identifiers, production
configuration, private keys or the inherited application-credential values.
No dedicated security email address is advertised.

Include affected version/commit, a sanitized impact description and reproduction
using synthetic data. Do not test against somebody else's account/device or
interrupt monitoring. A maintainer will acknowledge when available, investigate,
agree on a disclosure timeline with the reporter and publish an advisory/fix
when appropriate. Coordinate relevant upstream/provider issues privately; no
automatic upstream disclosure or claim of provider permission is implied.

## Disclosure and remediation

Prefer a new version with a documented fix; never silently replace a release asset.
Credit reporters with their consent. Coordinate credential revocation with the
credential owner if a genuine leak is discovered. The maintainer cannot rotate
third-party application credentials. Never request real credentials in an issue
or a pull request. Preserve relevant evidence privately and publish only sanitized
findings after coordination.
