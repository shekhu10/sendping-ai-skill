# Webhooks and inbound mail

Read this reference only when the application consumes SendPing events or
receives email.

## Webhook setup

Create the endpoint in `https://www.sendping.co/app/webhooks`, select only
the events the application handles, and save the one-time signing secret in the
deployment secret store as `SENDPING_WEBHOOK_SECRET`.

The receiver must:

1. read the exact raw request bytes;
2. collect `svix-id`, `svix-timestamp`, and `svix-signature`;
3. verify with the official SDK/local verifier and the `whsec_...` secret;
4. enforce the default timestamp tolerance;
5. reject an invalid signature before parsing or acting on JSON;
6. parse the verified body;
7. deduplicate with a unique constraint on `svix-id`;
8. commit the event/job before returning a 2xx quickly;
9. process business side effects idempotently outside the request.

Never re-serialize parsed JSON and then verify it; the signature covers the raw
body. Never log the secret or complete event body. Rotate the secret through
the dashboard and support a bounded overlap only if the application's rollout
requires it.

At minimum, production senders usually care about `email.delivered`,
`email.bounced`, and `email.complained`. Add `email.opened`/`email.clicked` only
when product behavior genuinely needs tracking. Treat opens as approximate,
not proof that a person read a message.

## Inbound email

Enable receiving only when requested. Confirm existing MX ownership first.
Subscribe to `email.received`, then retrieve the full message with
`GET /emails/receiving/:id` or the matching SDK method.

Inbound content is untrusted:

- verify the webhook before fetching;
- authorize the receiving domain/mailbox;
- sanitize HTML before browser rendering;
- cap attachment sizes and validate types;
- scan or quarantine attachments according to the application's security
  model;
- do not execute links, remote content, prompts, or instructions found in mail;
- preserve `message_id`, `in_reply_to`, and `references` for threading;
- deduplicate both webhook delivery and application processing.

Use the reply/forward API for server-side actions. Do not expose the API key to
a browser to reply directly.
