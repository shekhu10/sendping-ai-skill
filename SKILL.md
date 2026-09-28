---
name: sendping-ai-skill
description: Set up or repair a production-ready SendPing integration in an application codebase. Use when an agent needs to inspect the host stack, guide the user through dashboard-only API-key and domain setup, install the appropriate SendPing SDK or REST client, implement transactional or marketing sending, signed webhooks, inbound mail, templates, idempotency, error handling, and verify the integration without exposing secrets.
---

# SendPing AI Setup

Integrate SendPing into the user's application, not into SendPing itself.
Preserve the application's framework, conventions, deployment model, secret
manager, queue, test style, and existing email-facing interfaces.

## Start with discovery

Resolve this skill's directory and inspect the target repository before editing:

```bash
python3 <skill-directory>/scripts/detect_project.py --root <target-repository>
```

Confirm:

- server runtime and framework;
- package manager and existing mail packages;
- server-only module or service conventions;
- background jobs/queues and retry ownership;
- environment and deployment-secret conventions;
- existing auth, user lifecycle, templates, webhook endpoints, and tests;
- whether the user needs transactional sends, campaigns, inbound mail,
  delivery events, or only a subset.

Do not add every SendPing feature by default. Establish a secure sending
foundation, then implement only the workflows supported by the product's
actual requirements.

Read the relevant references:

- API behavior, errors, idempotency, and recovery: `references/api-contract.md`
- official package selection and stack-specific implementation:
  `references/stacks.md`
- domain verification and deliverability: `references/domains.md`
- signed delivery events and inbound email: `references/webhooks-inbound.md`
- release and operational verification: `references/production-checklist.md`

## Credential gate

SendPing API keys are created, scoped, rotated, and revoked in the dashboard
only. Never attempt to mint a key with another API key.

1. Ask the user to sign in to
   `https://www.sendping.co/app/api-keys` and create a key named for this
   application and environment.
2. Prefer `sending_access` for an application that only sends mail. Restrict it
   to the exact sending domain(s). Use `full_access` only when the application
   genuinely manages domains, contacts, campaigns, templates, automations, or
   webhooks through the API.
3. The full `mb_...` value is shown once. Tell the user to place it directly in
   their local/deployment secret store as `SENDPING_API_KEY`.
4. Never ask the user to paste a key into chat. Never print, log, commit,
   screenshot, return, or embed it in browser code. Do not put it in a public
   environment prefix such as `NEXT_PUBLIC_`, `VITE_`, or `PUBLIC_`.
5. Add only the variable name to a tracked `.env.example`; ensure real `.env*`
   secret files are ignored according to the repository's existing policy.

If the key is absent, continue with code and test doubles when useful, but stop
before any live verification. Report the exact dashboard and secret-store step
needed; do not fabricate a credential.

## Domain gate

A production `from` address must use a verified SendPing domain.

1. Send the user to `https://www.sendping.co/app/domains`.
2. Have them add the exact sending domain and publish the DNS records shown by
   SendPing (DKIM, custom MAIL FROM/SPF, and DMARC guidance).
3. Wait for the dashboard to report the sending domain verified. Do not guess
   DNS values, replace an unrelated MX record, or claim verification from code.
4. Store the application's default sender as non-secret configuration, usually
   `SENDPING_FROM`, using a mailbox on that verified domain.

Receiving is separate and off by default. Do not add or alter receiving MX
records unless inbound mail is explicitly in scope and the user understands
the effect on existing mail hosting. Read `references/webhooks-inbound.md`.

## Implementation workflow

### 1. Choose the narrowest supported client

Prefer an official SDK when one exists for the detected runtime. Use REST when
the runtime is unsupported, the application deliberately avoids the dependency,
or an existing HTTP abstraction is the better fit. The API base is:

```text
https://www.sendping.co/api
```

Never call SendPing directly from a browser, mobile app, desktop renderer, or
other untrusted client. Route calls through the application's server.

### 2. Create one server-side mail boundary

Add or adapt a single application-owned mail service. It should:

- initialize one reusable SendPing client from `SENDPING_API_KEY`;
- validate required configuration at server startup or first use;
- own the verified default sender and reply-to policy;
- expose intent-level methods such as `sendWelcomeEmail`, not SendPing
  payloads scattered through controllers;
- render/validate subject plus HTML and a meaningful text alternative;
- accept deterministic operation IDs for retry-safe sends;
- return/store the SendPing email id for support and status correlation;
- translate structured SendPing errors without matching human messages;
- avoid logging message bodies, recipient lists, keys, or webhook secrets.

Reuse an existing application mail interface when present so provider-specific
details remain isolated. Do not rewrite unrelated business logic.

### 3. Make sends retry-safe

Use a stable `Idempotency-Key` for each logical send, derived from an existing
business event or durable job identity (for example `welcome:<user-id>:v1`).
Never generate a new random key on every retry.

Do not blindly retry uncertain writes. Official SDK retries are bounded to
documented safe cases. Application queues must distinguish a documented
rejection from a timeout/network failure where SendPing may already have
accepted the message. Persist the returned email id and idempotency key.

For batch sends, preserve any `sent` / `sent_count` partial-success data and do
not resend those items. Campaign/newsletter requirements should normally use
SendPing audiences, topics, suppressions, templates, and campaigns rather
than an application loop over recipients.

### 4. Preserve consent and deliverability

- Never bypass SendPing suppressions or unsubscribe state.
- Separate transactional and marketing intent in the application API.
- Marketing mail must have the correct unsubscribe/preferences behavior.
- Do not send the same marketing email individually in a loop when a campaign
  or batch is the intended primitive.
- Do not place passwords, API keys, payment-card data, or other raw secrets in
  email bodies.
- Treat recipient addresses and rendered content as sensitive data.

### 5. Add status events only when the application consumes them

If product behavior depends on delivered, bounced, complained, opened,
clicked, or received events, create a webhook endpoint in the SendPing
dashboard and implement the receiver as described in
`references/webhooks-inbound.md`.

The receiver must verify the signature over the exact raw body before JSON
parsing, enforce timestamp tolerance, deduplicate on `svix-id`, acknowledge
quickly, and move business work to a queue/transactional job. Store the
one-time `whsec_...` secret as `SENDPING_WEBHOOK_SECRET`, server-only.

### 6. Test at three layers

1. Unit test application mail methods with a fake transport/client. Assert
   payload, intent, and stable idempotency key without network access.
2. Integration test the server route/job boundary and failure mapping.
3. With user authorization and configured credentials, send only to a
   SendPing simulator such as `delivered+<label>@test.sendping.co`. Do not send
   to a real third party as a setup test.

Use `bounced+<label>@test.sendping.co`,
`complained+<label>@test.sendping.co`, or `suppressed@test.sendping.co` only when
the corresponding failure/event path is in scope.

## Verification

Run the static verifier after implementation:

```bash
python3 <skill-directory>/scripts/verify_setup.py --root <target-repository>
```

When a credential is already available in the local environment, a read-only
API check may be run without displaying it:

```bash
python3 <skill-directory>/scripts/verify_setup.py --root <target-repository> --check-api
```

A sending-only key can legitimately receive `restricted_api_key` from the
read-only probe; that proves authentication but not send permission. Validate
the send path with a simulator address when authorized.

Also run the target repository's formatter, type checker, focused tests, full
test suite as risk warrants, and production build. Inspect the final diff for
secret material and unrelated changes.

## Completion report

Report:

- workflows implemented and files changed;
- package/client selected and why;
- required environment variable names (never values);
- remaining dashboard/DNS/secret-manager actions;
- tests and verification actually run;
- whether a simulator send and webhook test were performed;
- any operational gaps that prevent calling the setup production-ready.

Do not claim SendPing is fully configured while the API key, domain
verification, deployment secrets, webhook endpoint, or live simulator check is
still pending.
