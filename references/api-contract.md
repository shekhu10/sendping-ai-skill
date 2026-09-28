# SendPing API contract

Use this reference when implementing transport, error handling, retries, or
idempotency.

## Connection

- Base URL: `https://www.sendping.co/api`
- Authentication: `Authorization: Bearer $SENDPING_API_KEY`
- Keys minted by the dashboard start with `mb_` and are secrets.
- REST clients must send `Content-Type: application/json` for JSON bodies and a
  non-empty `User-Agent`. Official SDKs set these headers.
- Successful single sends return a durable email `id`.

## Send shape

`POST /emails` accepts a verified `from`, 1–50 `to` recipients, optional `cc`,
`bcc`, `reply_to`, `headers`, `attachments`, `scheduled_at`, and either direct
`html`/`text`/`subject` content or a template reference and variables. Prefer a
text alternative even when HTML is present.

`POST /emails/batch` accepts up to 100 emails. Attachments and `scheduled_at`
belong on individual sends, not batch items. Larger accepted batches may be
queued; acceptance is not proof of delivery.

## Idempotency and recovery

Pass `Idempotency-Key` on sends that may be retried. Reuse the same key for the
same logical operation. Keys are retained for the documented 24-hour window.

Retry only when the operation is known safe:

- honor `Retry-After` on 429/503;
- keep retries bounded with jitter/backoff;
- reads are safe to retry;
- a send with a stable idempotency key can be retried under the SDK's recovery
  contract;
- a timeout or network failure without an operation key is uncertain, not a
  documented rejection;
- never automatically replay a partial batch; remove the entries reported in
  `sent`/`sent_count` first.

## Errors

Errors use structured JSON with `statusCode`, `name`, and `message`, sometimes
plus `limit`, `reputation`, `sent`, or `sent_count`.

Branch on `name` and inspect the actual HTTP status. Never match `message`.
Important names include:

- `missing_api_key`, `invalid_api_key`, `restricted_api_key`;
- `validation_error`, `not_found`, `conflict`;
- `plan_limit_reached`, `daily_quota_exceeded`,
  `monthly_quota_exceeded`, `rate_limit_exceeded`;
- `reputation_paused`, `reputation_limit_exceeded`,
  `sending_service_unavailable`.

Treat `limit.next_plan`, `reputation.retryable`, and `reputation.retry_at` as
data, not as inferred text. Provider-internal details are intentionally
sanitized.

## API key permissions

- `sending_access`: send scope only; may be restricted to specific domains.
- `full_access`: read, write, send, and webhook management across the account.
- Creating, re-scoping, rotating, and revoking API keys is dashboard-only.
  Every API-key caller is refused with `dashboard_only` for those mutations.

Use the least privilege that satisfies the application.
