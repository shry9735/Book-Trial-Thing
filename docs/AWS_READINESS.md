# AWS readiness

Things that will hurt when this moves onto AWS, found by testing the
behaviour rather than reading the code. Each finding says what happens,
why, and what to do.

Ordered by when it will bite you, not by how interesting it is.

**Status:** findings 2–7 are fixed in code, with regression tests. Finding
1 is partly a process change and finding 8 is infrastructure — both are
still on you. Each section says which.

- [Blockers](#blockers)
- [Will bite you in the first month](#will-bite-you-in-the-first-month)
- [Worth knowing before you wire it up](#worth-knowing-before-you-wire-it-up)
- [What is already right](#what-is-already-right)

---

## Blockers

### 1. Rolling deploys are not safe right now

**Verified.** Migration 3 renames `groups` → `classrooms`. ECS rolling
deploys run old and new tasks side by side, and migrations run at task
start-up. So the moment the *first* new task boots:

```
old task deployed, schema at migration 2
old task serving /groups: OK
new task started, applied migration 3
old task serving /groups: BROKEN -> UndefinedTable: relation "groups" does not exist
```

Every still-draining old task returns 500 on classroom pages until it is
replaced. With a default deployment that is a minute or two of errors for
a fraction of users, on every deploy that contains a renaming migration.

**Fix, in order of effort:**

- For *this* deploy: run it as a stop-the-world release
  (`minimumHealthyPercent: 0`), or take the brief error window knowingly.
- For the future: adopt **expand/contract**. A rename becomes three
  deploys — add the new name and write to both, migrate readers, drop the
  old name. Never rename or drop in the same deploy as the code change.
- Move migrations out of task start-up entirely into a one-shot ECS task
  or CodeBuild step that runs *before* the service updates. `RUN_MIGRATIONS=0`
  already exists for exactly this.

The second and third are the real fix. The first is how you ship next week.

> **Still open — this one is yours.** `RUN_MIGRATIONS` is now passed
> through `docker-compose.yml` and documented in `.env.example`, and
> `init_app()` explains the hazard where you will read it. But nothing can
> make a renaming migration safe for a rolling deploy except not doing it
> that way.

### 2. Production boots with no working email, and only warns

`REQUIRE_EMAIL_VERIFICATION` defaults to on in production.
`EMAIL_BACKEND` defaults to `console`. Together that means a production
container starts happily, and **nobody can complete a signup** — the
verification link is written to CloudWatch instead of being sent.

`config.validate()` prints a warning to stderr and carries on. Nobody
reads container boot logs before a launch.

> **Fixed.** That combination is now a hard boot failure, the way a
> missing `SECRET_KEY` already was. Covered by
> `t_production_guards`.

### 3. Two tables grow forever

`rate_events` gains a row on every failed login, signup and reset attempt.
`stripe_events` gains one per webhook. Both are only ever trimmed by
`manage.py purge`, which nothing schedules.

Left alone, `rate_count()` gets slower and the table gets bigger forever.
It is not dramatic — it is the kind of thing you discover eighteen months
in, on a Sunday.

One correction to an earlier draft of this document: the per-IP bucket
not being cleared on a successful login is **deliberate, not a bug**.
Clearing it would let an attacker holding one valid credential reset the
address counter between sprays, which is the exact thing that limit is
for. Only the per-username bucket clears.

> **Fixed.** `rate_hit()` now sweeps expired rows on roughly one insert in
> fifty, so the table maintains itself whether or not anything is
> scheduled — and it trims hardest under attack, which is when rows pile
> up. Covered by `t_rate_events_trim`.
>
> Still worth adding an EventBridge rule running `manage.py purge` daily:
> it also covers `stripe_events` and expired tokens, which grow far more
> slowly and are not swept inline.

### 4. An RDS failover will be much worse than it needs to be

**Verified.** The application handles a database outage well on its own:

```
before:          200 ok
database down:   503 degraded
recovered after ~2s without a restart
```

The connection pool reconnects by itself. But the deployment around it
will not let that happen:

- `/healthz` returns **503** when the database is unreachable, and it is
  the obvious ALB health check path. During a failover every task goes
  unhealthy *simultaneously*, so ECS replaces the entire service.
- A task that boots while the database is unreachable **dies after 10
  seconds** with `PoolTimeout` (`init_pool(wait=True, timeout=DB_TIMEOUT)`).
  Verified.

So a 60-second failover that the app would have ridden out becomes: all
tasks killed, replacements crash-loop until the database returns, then a
cold start. Minutes of hard downtime instead of seconds of degradation.

> **Fixed**, in three parts:
>
> - **`/livez`** is new: liveness, touching nothing. Point the ALB target
>   group and the ECS container health check here. The Dockerfile's own
>   `HEALTHCHECK` and the nginx config already do.
> - **`/healthz`** keeps its deep check, for dashboards and deploy
>   verification. It is no longer the thing that decides whether your
>   tasks live.
> - **The pool now opens non-blocking**, so a worker starting mid-failover
>   comes up instead of dying. Verified: with the database stopped, boot
>   takes 0.3s, `/livez` returns 200 and `/healthz` returns 503.
>
> Migrations still need a live database, so when `RUN_MIGRATIONS=1` they
> wait up to `DB_BOOT_RETRY` (30s) and then fail loudly rather than
> silently serving against an unverified schema. Covered by `t_livez`.

---

## Will bite you in the first month

### 5. `APP_ENV` is a single switch that silently disables every safeguard

These all default off unless `APP_ENV=production` exactly:

| Setting | Default when `APP_ENV` is anything else |
|---|---|
| `COOKIE_SECURE` | **false** — session cookies sent over plain HTTP |
| `TRUSTED_PROXIES` | **0** — see below |
| `LOG_JSON` | false — unparseable logs in CloudWatch |
| `REQUIRE_EMAIL_VERIFICATION` | false |
| every production check in `validate()` | skipped entirely |

Getting this one variable wrong in a task definition silently downgrades
security everywhere and nothing complains, because the thing that would
have complained is also switched off by it.

`TRUSTED_PROXIES=0` behind an ALB is the worst of them: `request.remote_addr`
becomes the ALB's own private IP, so **every user in the world shares one
rate-limit bucket**. One person fat-fingering their password locks out
everybody.

> **Fixed**, from both ends:
>
> - `TRUSTED_PROXIES=0` with `APP_ENV=production` is now a boot failure.
> - The case that guard *cannot* catch — `APP_ENV` not being set at all,
>   which switches off the guard too — is caught at runtime instead: an
>   `X-Forwarded-For` arriving while `TRUSTED_PROXIES` is 0 logs one loud
>   ERROR per process. Covered by `t_proxy_warning`.
>
> Set `APP_ENV=production` in the task definition before anything else
> regardless. It remains the switch everything else hangs off.

### 6. Nothing forces TLS to the database

`sslmode` is only mentioned in a comment in `.env.example`. psycopg
defaults to `prefer`, which **silently falls back to plaintext** if the
server allows it — and RDS allows it unless you set `rds.force_ssl=1`.

This is student data, including minors' names and email addresses,
crossing a VPC unencrypted, with nothing that would tell you.

> **Fixed.** Production now refuses to boot unless `DATABASE_URL` carries
> `sslmode=require`, `verify-ca` or `verify-full`. Covered by
> `t_production_guards`.
>
> Still set `rds.force_ssl=1` in the RDS parameter group as well, so the
> server refuses plaintext regardless of what any client asks for.

### 7. Worker count is read from the host, not the task

```python
workers = min(multiprocessing.cpu_count() * 2 + 1, 8)
```

`cpu_count()` reports the **host's** CPUs, not the container's CPU limit.
On Fargate that happens to be close enough. On EC2-backed ECS it is not:
a 0.5-vCPU task on a 16-core instance spawns the full 8 workers, each with
its own pool of 5 — **40 database connections from one small task**, plus
CPU thrash from oversubscription.

`db.t4g.micro` tops out around 80 connections. Two such tasks during a
rolling deploy exhausts it, and new connections are refused.

> **Fixed.** The default now reads the container's cgroup CPU quota, then
> CPU affinity, and only falls back to the host count when neither is
> available.
>
> Set `WEB_CONCURRENCY` explicitly in the task definition anyway. The
> `WEB_CONCURRENCY × DB_POOL_MAX` arithmetic in `DEPLOY.md` only holds if
> you know the number rather than inferring it.

### 8. Secrets are plain environment variables

`docker-compose.yml` passes `SECRET_KEY`, `STRIPE_SECRET_KEY`,
`SMTP_PASSWORD` and the database URL as `environment` entries. Translated
literally into an ECS task definition, every one of those is readable by
anyone with `ecs:DescribeTaskDefinition` and visible in the console.

> **Still open — this one is yours.** Use the task definition's `secrets`
> block with `valueFrom` pointing at Secrets Manager or SSM Parameter
> Store. The application needs no change: they still arrive as
> environment variables, so nothing in the code has to know.

### 9. The ALB's default health check path fails

The ALB default is `GET /` expecting a 200. This app returns:

```
GET /        -> 302  Location: /login
GET /healthz -> 200
```

Leave the default and **every target is marked unhealthy immediately** and
the service never comes up. It is a five-minute debugging session the
first time, and an obvious one only in hindsight.

> **Fixed** as far as code can fix it: `/livez` now exists and is the
> right target. Set the target group health check path to **`/livez`** —
> not `/`, and not `/healthz`, for the reason in finding 4.

---

## Worth knowing before you wire it up

**CloudFront in front of the whole app will break sessions.** Default
cache policies strip cookies. Either put CloudFront only in front of
`/static` (which is what `CDN_URL` is for), or use a cache policy that
forwards the session cookie and disables caching on everything dynamic.

**An HTTP-only ALB listener makes login silently impossible.**
`COOKIE_SECURE=true` means the browser will not return the session cookie
over plain HTTP, so you get an endless redirect back to the login page
with no error anywhere. Terminate TLS before you test signup.

**RDS Proxy and pgbouncer interact badly with the migration lock.**
`db.migrate()` uses `pg_advisory_lock`, which is session-scoped. RDS Proxy
will pin the connection (losing multiplexing for its duration, which is
fine). pgbouncer in *transaction* pooling mode is not fine: the lock and
unlock can land on different backends. If you put either in front, run
migrations against the database directly, bypassing the proxy.

**SES starts in sandbox mode** and will only send to verified addresses.
Since verification gates signup, nobody can register until you request
production access — a support ticket with a day or two of turnaround. Do
it early, not on launch day.

**Every worker runs migrations at boot.** They serialise on the advisory
lock, so it is safe, but a slow migration delays readiness for the whole
task. Another reason to move migrations to a pre-deploy step.

---

## What is already right

Worth knowing so you do not spend effort re-solving it:

- **No local disk state.** Nothing durable is written to the container
  filesystem, so tasks are genuinely disposable.
- **The pool self-heals.** Verified: a database outage recovers in ~2s
  with no restart. The app is more resilient than the platform config
  currently allows it to be.
- **No sticky sessions needed.** Sessions are signed cookies, so any task
  can serve any request.
- **`X-Forwarded-For` is read from the right end.** It takes the *last*
  entries, which is what ALB writes; the common mistake of reading the
  leftmost value would let anyone spoof their rate-limit bucket.
- **`keepalive` is 75s**, deliberately above the ALB's 60s idle timeout,
  which avoids the intermittent-502 class of bug.
- **No scheme-dependent URL building.** Absolute URLs come from
  `BASE_URL`, so TLS termination at the ALB does not produce `http://`
  links in emails.
- **Non-root container**, and Postgres is not published to the host in the
  compose file.
