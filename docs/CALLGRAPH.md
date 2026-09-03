# Call graph

**Generated — do not edit.** Regenerate with `python scripts/callgraph.py`
after changing routes or module imports.

Built by walking the AST of everything in `game/`. It answers three
questions: how the modules stack up, what a given route touches, and
whether anything is wired backwards.

---

## Module layers

Dependencies run downward only. A module may use anything in a layer
below it and nothing above — routes call services, services call data,
and nothing calls back up.

```mermaid
graph TD
    subgraph L0["entrypoint"]
        wsgi["wsgi.py"]
        manage["manage.py"]
        migrate_json["migrate_json.py"]
        selftest["selftest.py"]
        selftest_billing["selftest_billing.py"]
    end
    subgraph L1["web"]
        app["app.py"]
    end
    subgraph L2["service"]
        billing["billing.py"]
        security["security.py"]
        emailer["emailer.py"]
    end
    subgraph L3["data"]
        db["db.py"]
    end
    subgraph L4["platform"]
        config["config.py"]
        logsetup["logsetup.py"]
    end
    app --> billing
    app --> config
    app --> db
    app --> emailer
    app --> logsetup
    app --> security
    billing --> db
    manage --> billing
    manage --> config
    manage --> db
    manage --> logsetup
    migrate_json --> config
    migrate_json --> db
    security --> db
    selftest --> app
    selftest --> db
    selftest --> security
    selftest_billing --> app
    selftest_billing --> billing
    selftest_billing --> db
    wsgi --> app
```

No layering violations: every import points downward.

---

## Routes

46 routes. **Guards** are the decorators that must pass before
the handler runs; **touches** is every other module the handler reaches,
following local helpers.

| Route | Methods | Guards | Handler | Touches |
|---|---|---|---|---|
| `/` | GET | — | `app.home` | `db` |
| `/api/example` | POST | signed in | `app.api_example` | `billing`, `db` |
| `/api/examples/<lesson_id>` | GET | signed in | `app.api_examples` | `billing`, `db` |
| `/api/progress` | POST | signed in | `app.api_progress` | `billing`, `db` |
| `/api/quiz` | POST | signed in | `app.api_quiz` | `billing`, `db` |
| `/api/quiz/finish` | POST | signed in | `app.api_quiz_finish` | `billing`, `db` |
| `/art-placeholder/<path:name>` | GET | — | `app.art_placeholder` | — |
| `/art/<path:name>` | GET | — | `app.art_url` | — |
| `/billing` | GET | signed in, approved member | `app.billing_home` | `billing`, `db` |
| `/billing/invoice-request` | POST | org admin | `app.billing_invoice_request` | `db`, `emailer`, `security` |
| `/billing/portal` | POST | signed in, approved member | `app.billing_portal` | `billing`, `db` |
| `/billing/return` | GET | signed in | `app.billing_return` | `billing`, `db` |
| `/billing/subscribe` | POST | signed in, approved member | `app.billing_subscribe` | `billing`, `db` |
| `/classroom` | GET | signed in, approved member | `app.classroom` | `db` |
| `/forgot` | GET/POST | — | `app.forgot_password` | `db`, `emailer`, `security` |
| `/groups` | GET | signed in | `app.groups_home` | `db` |
| `/groups/<int:gid>` | GET | signed in | `app.group_detail` | `db` |
| `/groups/<int:gid>/add` | POST | signed in | `app.group_add_member` | `db` |
| `/groups/<int:gid>/delete` | POST | signed in | `app.group_delete` | `db` |
| `/groups/<int:gid>/remove` | POST | signed in | `app.group_remove_member` | `db` |
| `/groups/new` | POST | signed in | `app.group_create` | `db` |
| `/grownup` | GET | signed in, approved member | `app.grownup_home` | `db` |
| `/grownup/link` | POST | signed in | `app.link_child` | `db` |
| `/grownup/student/<username>` | GET | signed in | `app.student_detail` | `db` |
| `/grownup/student/<username>/assign` | POST | signed in | `app.student_assign` | `db` |
| `/healthz` | GET | — | `app.healthz` | `db` |
| `/kit/<path:filename>` | GET | — | `app.kit_asset` | — |
| `/lesson/<lesson_id>` | GET | signed in, approved member | `app.lesson` | `billing`, `db` |
| `/lessons` | GET | signed in, approved member | `app.lessons` | `billing`, `db` |
| `/lessons/<lesson_id>/<path:filename>` | GET | — | `app.lesson_asset` | — |
| `/locked` | GET | signed in | `app.locked` | `billing`, `db` |
| `/login` | GET/POST | — | `app.login` | `db`, `security` |
| `/logout` | POST | — | `app.logout` | — |
| `/org` | GET | org admin | `app.org_home` | `billing`, `db` |
| `/org/join-policy` | POST | org admin | `app.org_join_policy` | `db` |
| `/org/members/<member_id>/admin` | POST | org admin | `app.org_set_admin` | `db` |
| `/org/members/<member_id>/approve` | POST | org admin | `app.org_approve_member` | `billing`, `db` |
| `/org/members/<member_id>/remove` | POST | org admin | `app.org_remove_member` | `billing`, `db` |
| `/org/rotate-code` | POST | org admin | `app.org_rotate_code` | `db` |
| `/pending` | GET | signed in | `app.pending` | `db` |
| `/reset/<token>` | GET/POST | — | `app.reset_password` | `db`, `security` |
| `/satchel` | GET | signed in, approved member | `app.satchel` | `db` |
| `/signup` | GET/POST | — | `app.signup` | `db`, `emailer`, `security` |
| `/stripe/webhook` | POST | CSRF exempt | `app.stripe_webhook` | `billing`, `db` |
| `/verify/<token>` | GET | — | `app.verify_email` | `db`, `security` |
| `/verify/resend` | POST | — | `app.resend_verification` | `db`, `emailer`, `security` |

---

## What each route calls

Expanded one level through local helpers, so this is what the
handler ultimately reaches — not just what its own body names.

### `GET /`

`app.home` — game/app.py:543

- **db** → `user_by_id`

### `POST /api/example`

Record one practice-example answer and hand back the same correct/explain shape /api/quiz gives — Spark uses i

`app.api_example` — game/app.py:1182

- **billing** → `entitlement_for`, `lesson_is_free`
- **db** → `record_example`, `user_by_id`

### `GET /api/examples/<lesson_id>`

Prompts and choices for a lesson's practice examples, answer key stripped — the same treatment the quiz gets.

`app.api_examples` — game/app.py:1164

- **billing** → `entitlement_for`, `lesson_is_free`
- **db** → `user_by_id`

### `POST /api/progress`

Called by the lesson player, and by lessons via the kit's postMessage.

`app.api_progress` — game/app.py:1101

- **billing** → `entitlement_for`, `lesson_is_free`
- **db** → `set_lesson_status`, `summaries_for`, `user_by_id`

### `POST /api/quiz`

Check one answer and record the attempt.

`app.api_quiz` — game/app.py:1129

- **billing** → `entitlement_for`, `lesson_is_free`
- **db** → `record_answer`, `user_by_id`

### `POST /api/quiz/finish`

Score the quiz, complete the lesson, and hand back any reward earned.

`app.api_quiz_finish` — game/app.py:1219

- **billing** → `entitlement_for`, `lesson_is_free`
- **db** → `lesson_entries`, `set_lesson_status`, `summaries_for`, `user_by_id`

### `GET /billing`

`app.billing_home` — game/app.py:1696

- **billing** → `entitlement_for`
- **db** → `count_billable_seats`, `invoices_for`, `org_by_id`, `subscription_for_org`, `subscription_for_parent`, `user_by_id`, `visible_students`

### `POST /billing/invoice-request`

Ask to be billed by invoice on terms instead of by card.

`app.billing_invoice_request` — game/app.py:1801

- **db** → `count_billable_seats`, `org_by_id`, `set_billing_profile`, `user_by_id`
- **emailer** → `send`
- **security** → `email_problem`

### `POST /billing/portal`

Stripe's hosted account page: change card, cancel, download invoices.

`app.billing_portal` — game/app.py:1760

- **billing** → `portal_session`
- **db** → `count_billable_seats`, `org_by_id`, `subscription_for_org`, `subscription_for_parent`, `user_by_id`, `visible_students`

### `GET /billing/return`

Where Stripe sends the browser after Checkout.

`app.billing_return` — game/app.py:1788

- **billing** → `entitlement_for`
- **db** → `user_by_id`

### `POST /billing/subscribe`

Send the payer to Stripe's hosted Checkout.

`app.billing_subscribe` — game/app.py:1715

- **billing** → `checkout_session`, `enabled`, `ensure_customer`
- **db** → `count_billable_seats`, `org_by_id`, `subscription_for_org`, `subscription_for_parent`, `user_by_id`, `visible_students`

### `GET /classroom`

`app.classroom` — game/app.py:1008

- **db** → `summaries_for`, `user_by_id`

### `GET/POST /forgot`

`app.forgot_password` — game/app.py:769

- **db** → `invalidate_tokens`, `store_token`, `user_by_email`, `write`
- **emailer** → `send_reset`
- **security** → `client_ip`, `new_token`, `over_limit`, `record_attempt`

### `GET /groups`

`app.groups_home` — game/app.py:1396

- **db** → `group_members`, `group_summary_rows`, `summaries_for`, `unresolved_counts`, `user_by_id`, `visible_students`

### `GET /groups/<int:gid>`

`app.group_detail` — game/app.py:1448

- **db** → `group_in_org`, `group_members`, `summaries_for`, `unresolved_counts`, `user_by_id`, `visible_students`

### `POST /groups/<int:gid>/add`

`app.group_add_member` — game/app.py:1478

- **db** → `add_group_member`, `can_see_student`, `group_in_org`, `user_by_id`, `user_by_username`

### `POST /groups/<int:gid>/delete`

`app.group_delete` — game/app.py:1502

- **db** → `delete_group`, `user_by_id`

### `POST /groups/<int:gid>/remove`

`app.group_remove_member` — game/app.py:1490

- **db** → `can_see_student`, `group_in_org`, `remove_group_member`, `user_by_id`, `user_by_username`

### `POST /groups/new`

`app.group_create` — game/app.py:1427

- **db** → `create_group`, `user_by_id`

### `GET /grownup`

Answers "is my kid doing the work?" without any digging: a headline per student, and anything needing attentio

`app.grownup_home` — game/app.py:1258

- **db** → `org_by_id`, `summaries_for`, `unresolved_counts`, `user_by_id`, `visible_students`

### `POST /grownup/link`

A parent attaches themselves to a student with the student's link code.

`app.link_child` — game/app.py:1374

- **db** → `link_parent`, `student_by_link_code`, `user_by_id`

### `GET /grownup/student/<username>`

`app.student_detail` — game/app.py:1318

- **db** → `assigned_lesson_ids`, `can_see_student`, `lesson_entries`, `summaries_for`, `user_by_id`, `user_by_username`

### `POST /grownup/student/<username>/assign`

Narrow (or re-widen) which lessons show up on one student's menu.

`app.student_assign` — game/app.py:1354

- **db** → `can_see_student`, `set_assignment`, `user_by_id`, `user_by_username`

### `GET /healthz`

Liveness plus readiness.

`app.healthz` — game/app.py:416

- **db** → `healthy`

### `GET /lesson/<lesson_id>`

`app.lesson` — game/app.py:1048

- **billing** → `entitlement_for`, `lesson_is_free`
- **db** → `assigned_lesson_ids`, `lesson_entries`, `set_lesson_status`, `summaries_for`, `user_by_id`

### `GET /lessons`

`app.lessons` — game/app.py:1019

- **billing** → `entitlement_for`, `lesson_is_free`
- **db** → `assigned_lesson_ids`, `lesson_entries`, `summaries_for`, `user_by_id`

### `GET /locked`

Where a student lands on a lesson their account does not cover.

`app.locked` — game/app.py:1514

- **billing** → `entitlement_for`
- **db** → `user_by_id`

### `GET/POST /login`

`app.login` — game/app.py:553

- **db** → `touch_login`, `user_by_id`, `user_by_username`
- **security** → `clear_attempts`, `client_ip`, `over_limit`, `record_attempt`, `rotate_csrf_token`, `safe_next`

### `GET /org`

`app.org_home` — game/app.py:1530

- **billing** → `entitlement_for`
- **db** → `count_billable_seats`, `count_org_admins`, `org_by_id`, `org_members`, `pending_members`, `subscription_for_org`, `user_by_id`

### `POST /org/join-policy`

`app.org_join_policy` — game/app.py:1564

- **db** → `set_join_policy`, `user_by_id`

### `POST /org/members/<member_id>/admin`

`app.org_set_admin` — game/app.py:1620

- **db** → `count_org_admins`, `member_in_org`, `set_org_admin`, `user_by_id`

### `POST /org/members/<member_id>/approve`

`app.org_approve_member` — game/app.py:1587

- **billing** → `enabled`, `update_seats`
- **db** → `count_billable_seats`, `member_in_org`, `set_membership_status`, `subscription_for_org`, `user_by_id`

### `POST /org/members/<member_id>/remove`

`app.org_remove_member` — game/app.py:1599

- **billing** → `enabled`, `update_seats`
- **db** → `count_billable_seats`, `count_org_admins`, `member_in_org`, `set_membership_status`, `subscription_for_org`, `user_by_id`

### `POST /org/rotate-code`

`app.org_rotate_code` — game/app.py:1578

- **db** → `rotate_join_code`, `user_by_id`

### `GET /pending`

`app.pending` — game/app.py:523

- **db** → `org_by_id`, `user_by_id`

### `GET/POST /reset/<token>`

`app.reset_password` — game/app.py:799

- **db** → `consume_token`, `set_password`
- **security** → `clear_attempts`, `hash_token`, `password_problem`

### `GET /satchel`

`app.satchel` — game/app.py:1083

- **db** → `inventory`, `summaries_for`, `user_by_id`

### `GET/POST /signup`

Self-serve registration for all three roles.

`app.signup` — game/app.py:614

- **db** → `create_org`, `create_user`, `email_taken`, `org_by_join_code`, `store_token`, `user_by_id`, `username_taken`, `write`
- **emailer** → `send_verification`
- **security** → `client_ip`, `email_problem`, `new_token`, `over_limit`, `password_problem`, `record_attempt`, `rotate_csrf_token`, `username_problem`

### `POST /stripe/webhook`

`app.stripe_webhook` — game/app.py:1854

- **billing** → `enabled`, `handle_event`, `verify_webhook`
- **db** → `claim_event`, `finish_event`, `release_event`

### `GET /verify/<token>`

`app.verify_email` — game/app.py:730

- **db** → `consume_token`, `mark_verified`, `write`
- **security** → `hash_token`, `rotate_csrf_token`

### `POST /verify/resend`

`app.resend_verification` — game/app.py:745

- **db** → `invalidate_tokens`, `store_token`, `user_by_email`, `write`
- **emailer** → `send_verification`
- **security** → `client_ip`, `new_token`, `over_limit`, `record_attempt`

---

## Module summary

| Module | Layer | Functions | Routes | Imports |
|---|---|---|---|---|
| `manage.py` | entrypoint | 12 | 0 | `billing`, `config`, `db`, `logsetup` |
| `migrate_json.py` | entrypoint | 3 | 0 | `config`, `db` |
| `selftest.py` | entrypoint | 38 | 0 | `app`, `db`, `security` |
| `selftest_billing.py` | entrypoint | 50 | 0 | `app`, `billing`, `db` |
| `wsgi.py` | entrypoint | 0 | 0 | `app` |
| `app.py` | web | 88 | 46 | `billing`, `config`, `db`, `emailer`, `logsetup`, `security` |
| `billing.py` | service | 21 | 0 | `db` |
| `emailer.py` | service | 4 | 0 | — |
| `security.py` | service | 17 | 0 | `db` |
| `db.py` | data | 78 | 0 | — |
| `config.py` | platform | 3 | 0 | — |
| `logsetup.py` | platform | 2 | 0 | — |
| `import_assets.py` | — | 5 | 0 | — |
