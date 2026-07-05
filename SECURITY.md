# Security Policy

## Supported Versions

Only the latest released version of this integration is supported with
security fixes.

| Version | Supported |
| ------- | --------- |
| 0.4.x   | ✅ |
| < 0.4   | ❌ |

## Reporting a Vulnerability

Please **do not** report security vulnerabilities through public GitHub
issues. Instead, use GitHub's private vulnerability reporting for this
repository (Security tab → "Report a vulnerability") or open a draft
security advisory.

Include as much detail as you can: affected version, reproduction steps,
and the potential impact.

You can expect an initial response within a few days. If the report is
confirmed, a fix will be released and the advisory will be published once
the fix is available. If it's declined (e.g. not reproducible, out of
scope), you'll get an explanation.

## Scope Notes

This integration talks to your ÖkOfen Pellematic device directly over your
local network using the credentials you enter in Home Assistant
(`local_polling`); it does not send any data to third-party services. Your
ÖkOfen username and password are stored by Home Assistant as part of the
config entry, subject to Home Assistant's own storage protections.
