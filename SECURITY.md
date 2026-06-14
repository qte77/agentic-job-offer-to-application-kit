# Security Policy

## Supported versions

This project is pre-1.0; only the latest `main` is supported. Security fixes land
on `main` and ship in the next release.

## Reporting a vulnerability

Please report vulnerabilities **privately** via
[GitHub private vulnerability disclosure](https://github.com/qte77/agentic-job-offer-to-application-kit/security/advisories/new).
Do not open a public issue for a security report.

We aim to acknowledge a report within a few days and will coordinate a fix and a
disclosure timeline with you.

## Scope

The kit fetches only public, no-auth data and keeps a human in the loop for
submission (see [docs/research.md §Delivery](docs/research.md#delivery)); it stores
no credentials. In scope: the ingestion/relevance pipeline, the `ajoa-kit` CLI, and
dependency vulnerabilities. Handling of applicant PII (kept out of the repo — see
[docs/architecture.md §Data layout](docs/architecture.md#data-layout)) is also in scope.
