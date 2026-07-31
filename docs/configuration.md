# Configuration reference

## Local development

The default `server.environment: development` keeps authentication optional and stores runtime data under `data/`. Model keys, messaging tokens, JWT secrets, signing keys, databases and generated runtime files must remain outside version control.

Supported model secrets are `OPENAI_API_KEY`, `ANTHROPIC_API_KEY` and `DEEPSEEK_API_KEY`. Optional integrations use `GITHUB_TOKEN`, `TELEGRAM_BOT_TOKEN`, `SLACK_BOT_TOKEN` and `DISCORD_BOT_TOKEN`.

## Production boundary

Set `server.environment: production`. Startup then refuses unsafe configuration unless authentication is enabled, `JWT_SECRET` has at least 32 characters, CORS origins are explicit, and sandbox network access is disabled.

Set `TOOL_PACKAGE_SIGNING_KEY` to require signed tool packages. Configure a webhook secret and sender allow-list for each enabled messaging provider. Put TLS termination, request size limits and rate limiting in the reverse proxy.

## Persistent paths

- Conversations: configured database URL.
- RAG and memory: `data/` by default or the configured backend.
- Multi-agent plans: `multi_agent.storage_path`.
- Messaging sessions: `messaging.state_path`.
- Verified tool packages: `tool_market.package_path`.

Back up these locations together. Never copy `.env` or raw provider credentials into an archive committed to Git.
