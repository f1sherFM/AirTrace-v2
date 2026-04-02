# Post-Deploy Hardening

## Objective

Keep the first production rollout stable after the initial VPS launch.

## Immediate checks

1. Confirm only `80/443` are public.
   - `ss -tulpn | grep -E '80|443|3000|8000'`
   - `3000` and `8000` must stay bound to `127.0.0.1`

2. Confirm the compose stack is healthy.
   - `docker compose --env-file .env.production -f docker-compose.prod.yml ps`
   - `docker compose --env-file .env.production -f docker-compose.prod.yml logs api --tail=100`
   - `docker compose --env-file .env.production -f docker-compose.prod.yml logs web --tail=100`

3. Confirm public routes work through the domain.
   - `https://nande.webhop.me`
   - `https://nande.webhop.me/alerts/settings`
   - `https://nande.webhop.me/api/v2/health`

4. Confirm Telegram delivery still works.
   - Create a temporary alert with `AQI = 0`
   - Trigger one manual delivery smoke test
   - Remove or tighten the rule after the check

5. Confirm Sentry is receiving new events.
   - Open the active Sentry project
   - Verify new backend or frontend errors appear there

## Ongoing hygiene

1. Keep `.env.production` only on the server.
2. Avoid `docker compose down -v` unless you intentionally want to remove persisted data.
3. Treat PostgreSQL as the source of truth for alert subscriptions and delivery state.
4. Re-run `docker compose ... config` before structural compose changes.
5. Review `docker compose ... ps` and `/api/v2/health` after each deploy.

## Follow-up work

1. Add a recurring PostgreSQL backup.
2. Reduce noisy degraded health signals that do not affect `public_status`.
3. Add a lightweight deploy/update runbook for routine releases.
