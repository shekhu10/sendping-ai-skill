# Domains and deliverability

Use this reference for production sender setup.

## Dashboard setup

1. Open `https://www.sendping.co/app/domains`.
2. Add the exact organizational or sending subdomain.
3. Publish every record shown by SendPing at the DNS provider.
4. Re-run verification from the dashboard after propagation.
5. Use a `from` mailbox under that verified domain.

SendPing's generated records establish DKIM and a custom MAIL FROM/SPF path;
the dashboard also provides DMARC guidance. Copy the live record names and
values from the dashboard. Never hardcode generic DNS values from this skill.

Start DMARC in monitoring mode and tighten it only after confirming every
legitimate sender for the domain aligns. Do not overwrite an existing DMARC
policy without reviewing it.

## Application configuration

Track only non-secret defaults such as:

```dotenv
SENDPING_FROM=Acme <hello@example.com>
SENDPING_REPLY_TO=support@example.com
```

Validate that the configured address belongs to an approved domain. Separate
environment-specific senders if staging and production use different domains.

## Safe validation

Use SendPing's simulator domain for integration tests:

- `delivered+label@test.sendping.co`
- `bounced+label@test.sendping.co`
- `complained+label@test.sendping.co`
- `suppressed@test.sendping.co`

Simulator sends create normal SendPing email/events without delivering to an
external mailbox. Reserved documentation domains (`example.com`, `.test`,
`.invalid`, and similar) are suppressed on the send path and are not a
successful delivery test.

## Receiving caution

Sending-domain verification does not enable inbound mail. Receiving needs an
explicit receiving configuration and MX decision. Changing MX can redirect
mail away from an existing mailbox provider. Inspect current DNS and confirm
the desired routing with the user before making any inbound change.
