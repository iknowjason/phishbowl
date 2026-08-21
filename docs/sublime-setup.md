# Sublime Security setup

PhishBowl reads mail from your **Sublime Security** tenant via its REST API. You
need two things: an **API key** and your tenant's **API base URL**.

> Reference: <https://docs.sublime.security/reference/introduction>

## 1. Get an API key

1. Sign in to your Sublime console.
2. Go to **Settings ▸ API** (or **Settings ▸ API Keys**).
3. Create an API key. Copy it — you'll put it in Terraform (`sublime_api_key`),
   which stores it in AWS Secrets Manager. It is **not** committed anywhere.

The API authenticates with a Bearer token:

```
Authorization: Bearer <YOUR_API_KEY>
```

## 2. Confirm your API base URL

The base URL depends on how your tenant is hosted:

| Deployment | Typical base URL |
|------------|------------------|
| Sublime Cloud (managed) | `https://api.platform.sublime.security` |
| Self-hosted / on-prem   | `https://<your-sublime-host>` |

Set it via the `sublime_api_base` Terraform variable (default is the cloud value).
If triage calls come back empty or 404, the base URL is the first thing to check —
confirm the exact host in your console.

## 3. Endpoints PhishBowl uses

| Purpose | Method & path |
|---------|---------------|
| List messages a mailbox received recently | `GET /v0/message-groups?mailbox=<addr>&created_at[gte]=<iso8601>&limit=<n>` |
| Retrieve one message (headers, links) | `GET /v0/messages/{id}` |

The `created_at[gte]` filter is how PhishBowl scopes to "the last 5 minutes," and
`mailbox` scopes to the target user.

## 4. Permissions / scope

Use a key with at least **read** access to messages and message groups. PhishBowl
never writes, quarantines, or deletes — it only reads for analysis.

## 5. Quick manual check (optional)

Confirm your key + base URL before deploying:

```bash
curl -s -H "Authorization: Bearer $SUBLIME_API_KEY" \
  "https://api.platform.sublime.security/v0/message-groups?limit=1" | head
```

A `200` with JSON means you're good. A `401` means the key is wrong; a `404`
usually means the base URL is wrong.
