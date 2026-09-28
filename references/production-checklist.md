# Production checklist

## Credentials and configuration

- [ ] API key created in the dashboard and stored in local/deployment secrets.
- [ ] Narrowest permission selected; sending key restricted to the required domains.
- [ ] No key or webhook secret appears in source, logs, screenshots, test snapshots, or browser bundles.
- [ ] `.env.example` lists names only; real secret files are ignored.
- [ ] `SENDPING_FROM` belongs to a dashboard-verified domain.

## Code

- [ ] One server-side SendPing boundary owns client creation and error mapping.
- [ ] Product code calls intent-level mail methods.
- [ ] HTML mail has a useful plain-text alternative.
- [ ] Stable idempotency keys come from durable business/job identities.
- [ ] Email ids are persisted or logged safely for support correlation.
- [ ] Retries are bounded and uncertain/partial sends cannot duplicate mail.
- [ ] Marketing flows preserve consent, topics, suppressions, and unsubscribe behavior.

## Webhooks/inbound (when used)

- [ ] Signature verified against exact raw body before parsing.
- [ ] Timestamp checked and `svix-id` deduplicated durably.
- [ ] Endpoint responds quickly; business work is queued/transactional.
- [ ] Bounce/complaint handlers update local eligibility without bypassing SendPing suppression.
- [ ] Inbound HTML/attachments are treated as untrusted.

## Verification

- [ ] Static verifier passes.
- [ ] Formatter, type checker, and focused tests pass.
- [ ] Production build passes.
- [ ] Simulator delivery succeeds with a test-only recipient.
- [ ] Bounce/complaint simulator paths pass when those handlers are in scope.
- [ ] Dashboard logs show the expected request and email ids.
- [ ] Webhook test delivery is verified and deduplicated when webhooks are used.
- [ ] Deployment environment contains the same variable names as local setup.

## Operations

- [ ] Key owner and 90-day rotation process are documented.
- [ ] Alerts distinguish authentication, quota, reputation, validation, and provider availability failures.
- [ ] Runbook explains where to inspect SendPing Logs, Emails, Domains, and Webhooks.
- [ ] Rollback disables the application sender or revokes its key without affecting unrelated applications.
