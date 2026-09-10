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
        import_assets["import_assets.py"]
        selftest["selftest.py"]
        selftest_billing["selftest_billing.py"]
        selftest_classrooms["selftest_classrooms.py"]
        selftest_accounts["selftest_accounts.py"]
        selftest_standards["selftest_standards.py"]
        selftest_gating["selftest_gating.py"]
        selftest_resources["selftest_resources.py"]
    end
    subgraph L1["web"]
        app["app.py"]
    end
    subgraph L2["service"]
        billing["billing.py"]
        security["security.py"]
        emailer["emailer.py"]
        tracks["tracks.py"]
        standards["standards.py"]
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
    app --> standards
    app --> tracks
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
    selftest_accounts --> app
    selftest_accounts --> db
    selftest_accounts --> security
    selftest_billing --> app
    selftest_billing --> billing
    selftest_billing --> db
    selftest_classrooms --> app
    selftest_classrooms --> db
    selftest_classrooms --> tracks
    selftest_gating --> app
    selftest_gating --> db
    selftest_gating --> tracks
    selftest_resources --> app
    selftest_resources --> db
    selftest_resources --> tracks
    selftest_standards --> app
    selftest_standards --> db
    selftest_standards --> standards
    wsgi --> app
```

No layering violations: every import points downward.

---

## Routes

63 routes. **Guards** are the decorators that must pass before
the handler runs; **touches** is every other module the handler reaches,
following local helpers.

| Route | Methods | Guards | Handler | Touches |
|---|---|---|---|---|
| `/` | GET | — | `app.home` | `db` |
| `/api/example` | POST | signed in, approved member | `app.api_example` | `billing`, `db`, `tracks` |
| `/api/examples/<lesson_id>` | GET | signed in, approved member | `app.api_examples` | `billing`, `db`, `tracks` |
| `/api/progress` | POST | signed in, approved member | `app.api_progress` | `billing`, `db`, `tracks` |
| `/api/quiz` | POST | signed in, approved member | `app.api_quiz` | `billing`, `db`, `tracks` |
| `/api/quiz/finish` | POST | signed in, approved member | `app.api_quiz_finish` | `billing`, `db`, `tracks` |
| `/art-placeholder/<path:name>` | GET | — | `app.art_placeholder` | — |
| `/art/<path:name>` | GET | — | `app.art_url` | — |
| `/billing` | GET | signed in, approved member | `app.billing_home` | `billing`, `db` |
| `/billing/invoice-request` | POST | org admin | `app.billing_invoice_request` | `db`, `emailer`, `security` |
| `/billing/portal` | POST | signed in, approved member | `app.billing_portal` | `billing`, `db` |
| `/billing/return` | GET | signed in | `app.billing_return` | `billing`, `db` |
| `/billing/subscribe` | POST | signed in, approved member | `app.billing_subscribe` | `billing`, `db` |
| `/classroom` | GET | signed in, approved member | `app.classroom` | `db` |
| `/classrooms` | GET | signed in, approved member | `app.classrooms_home` | `db` |
| `/classrooms/<int:classroom_id>` | GET | signed in, approved member | `app.classroom_detail` | `db` |
| `/classrooms/<int:classroom_id>/delete` | POST | org admin | `app.classroom_delete` | `db` |
| `/classrooms/<int:classroom_id>/students/add` | POST | org admin | `app.classroom_add_student` | `db` |
| `/classrooms/<int:classroom_id>/students/import` | GET/POST | signed in, approved member | `app.classroom_import_students` | `billing`, `db`, `security` |
| `/classrooms/<int:classroom_id>/students/new` | POST | signed in, approved member | `app.classroom_new_student` | `billing`, `db`, `security` |
| `/classrooms/<int:classroom_id>/students/remove` | POST | org admin | `app.classroom_remove_student` | `db` |
| `/classrooms/<int:classroom_id>/teachers/add` | POST | org admin | `app.classroom_add_teacher` | `db` |
| `/classrooms/<int:classroom_id>/teachers/remove` | POST | org admin | `app.classroom_remove_teacher` | `db` |
| `/classrooms/new` | POST | org admin | `app.classroom_create` | `db` |
| `/forgot` | GET/POST | — | `app.forgot_password` | `db`, `emailer`, `security` |
| `/grownup` | GET | signed in, approved member | `app.grownup_home` | `db` |
| `/grownup/link` | POST | signed in, approved member | `app.link_child` | `db` |
| `/grownup/resources` | GET | signed in, approved member | `app.resources_home` | `billing`, `db`, `tracks` |
| `/grownup/resources/<kind>/<owner_id>/<path:filename>` | GET | signed in, approved member | `app.resource_download` | `billing`, `db`, `tracks` |
| `/grownup/resources/<kind>/<owner_id>/<path:filename>/read` | GET | signed in, approved member | `app.resource_read` | `billing`, `db`, `tracks` |
| `/grownup/student/<username>` | GET | signed in, approved member | `app.student_detail` | `db`, `standards`, `tracks` |
| `/grownup/student/<username>/assign` | POST | signed in, approved member | `app.student_assign` | `db` |
| `/grownup/student/<username>/delete` | POST | org admin | `app.student_delete` | `billing`, `db` |
| `/grownup/student/<username>/grade` | POST | signed in, approved member | `app.set_student_grade` | `db`, `standards` |
| `/grownup/student/<username>/reset-password` | POST | signed in, approved member | `app.student_reset_password` | `db`, `security` |
| `/grownup/student/<username>/standards` | GET | signed in, approved member | `app.student_standards` | `db`, `standards` |
| `/healthz` | GET | — | `app.healthz` | `db` |
| `/kit/<path:filename>` | GET | — | `app.kit_asset` | — |
| `/legal/<page>` | GET | — | `app.legal` | — |
| `/lesson/<lesson_id>` | GET | signed in, approved member | `app.lesson` | `billing`, `db`, `tracks` |
| `/lessons` | GET | signed in, approved member | `app.lessons` | `billing`, `db`, `tracks` |
| `/lessons/<lesson_id>/<path:filename>` | GET | — | `app.lesson_asset` | — |
| `/livez` | GET | — | `app.livez` | — |
| `/locked` | GET | signed in | `app.locked` | `billing`, `db`, `tracks` |
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
| `/settings` | GET | signed in | `app.settings_home` | `db` |
| `/settings/delete` | POST | signed in | `app.delete_own_account` | `db` |
| `/settings/first-password` | GET/POST | signed in | `app.first_password` | `db`, `security` |
| `/settings/password` | POST | signed in | `app.change_password` | `db`, `security` |
| `/signup` | GET/POST | — | `app.signup` | `db`, `emailer`, `security` |
| `/stripe/webhook` | POST | CSRF exempt | `app.stripe_webhook` | `billing`, `db` |
| `/verify/<token>` | GET | — | `app.verify_email` | `db`, `security` |
| `/verify/resend` | POST | — | `app.resend_verification` | `db`, `emailer`, `security` |

---

## What each route calls

Expanded one level through local helpers, so this is what the
handler ultimately reaches — not just what its own body names.

### `GET /`

Send each role to the screen it actually wants.

`app.home` — game/app.py:800

- **db** → `user_by_id`

### `POST /api/example`

Record one practice-example answer and hand back the same correct/explain shape /api/quiz gives — Spark uses i

`app.api_example` — game/app.py:1808

- **billing** → `entitlement_for`, `lesson_is_free`
- **db** → `assigned_lesson_ids`, `lesson_statuses`, `record_example`, `user_by_id`
- **tracks** → `gate`, `required_lesson_ids`, `requirement_block`

### `GET /api/examples/<lesson_id>`

Prompts and choices for a lesson's practice examples, answer key stripped — the same treatment the quiz gets.

`app.api_examples` — game/app.py:1787

- **billing** → `entitlement_for`, `lesson_is_free`
- **db** → `assigned_lesson_ids`, `lesson_statuses`, `user_by_id`
- **tracks** → `gate`, `required_lesson_ids`, `requirement_block`

### `POST /api/progress`

Called by the lesson player, and by lessons via the kit's postMessage.

`app.api_progress` — game/app.py:1718

- **billing** → `entitlement_for`, `lesson_is_free`
- **db** → `assigned_lesson_ids`, `lesson_statuses`, `set_lesson_status`, `summaries_for`, `user_by_id`
- **tracks** → `gate`, `required_lesson_ids`, `requirement_block`

### `POST /api/quiz`

Check one answer and record the attempt.

`app.api_quiz` — game/app.py:1749

- **billing** → `entitlement_for`, `lesson_is_free`
- **db** → `assigned_lesson_ids`, `lesson_statuses`, `record_answer`, `user_by_id`
- **tracks** → `gate`, `required_lesson_ids`, `requirement_block`

### `POST /api/quiz/finish`

Score the quiz, complete the lesson, and hand back any reward earned.

`app.api_quiz_finish` — game/app.py:1848

- **billing** → `entitlement_for`, `lesson_is_free`
- **db** → `assigned_lesson_ids`, `lesson_entries`, `lesson_statuses`, `set_lesson_status`, `summaries_for`, `user_by_id`
- **tracks** → `gate`, `required_lesson_ids`, `requirement_block`

### `GET /billing`

`app.billing_home` — game/app.py:3159

- **billing** → `entitlement_for`
- **db** → `count_billable_seats`, `invoices_for`, `org_by_id`, `subscription_for_org`, `subscription_for_parent`, `user_by_id`, `visible_students`

### `POST /billing/invoice-request`

Ask to be billed by invoice on terms instead of by card.

`app.billing_invoice_request` — game/app.py:3264

- **db** → `count_billable_seats`, `org_by_id`, `set_billing_profile`, `user_by_id`
- **emailer** → `send`
- **security** → `email_problem`

### `POST /billing/portal`

Stripe's hosted account page: change card, cancel, download invoices.

`app.billing_portal` — game/app.py:3223

- **billing** → `portal_session`
- **db** → `count_billable_seats`, `org_by_id`, `subscription_for_org`, `subscription_for_parent`, `user_by_id`, `visible_students`

### `GET /billing/return`

Where Stripe sends the browser after Checkout.

`app.billing_return` — game/app.py:3251

- **billing** → `entitlement_for`
- **db** → `user_by_id`

### `POST /billing/subscribe`

Send the payer to Stripe's hosted Checkout.

`app.billing_subscribe` — game/app.py:3178

- **billing** → `checkout_session`, `enabled`, `ensure_customer`
- **db** → `count_billable_seats`, `org_by_id`, `subscription_for_org`, `subscription_for_parent`, `user_by_id`, `visible_students`

### `GET /classroom`

`app.classroom` — game/app.py:1541

- **db** → `summaries_for`, `user_by_id`

### `GET /classrooms`

Every classroom this account may see.

`app.classrooms_home` — game/app.py:2420

- **db** → `classroom_membership`, `classroom_rows`, `summaries_for`, `unplaced_students`, `unresolved_counts`, `user_by_id`, `visible_students`

### `GET /classrooms/<int:classroom_id>`

One classroom: who teaches it, who is in it, how they are doing.

`app.classroom_detail` — game/app.py:2510

- **db** → `classroom_in_org`, `classroom_students`, `classroom_teachers`, `org_teachers`, `summaries_for`, `teaches_classroom`, `unresolved_counts`, `user_by_id`, `visible_students`

### `POST /classrooms/<int:classroom_id>/delete`

Delete a classroom.

`app.classroom_delete` — game/app.py:2634

- **db** → `delete_classroom`, `user_by_id`

### `POST /classrooms/<int:classroom_id>/students/add`

Put a student in a classroom, which is what lets its teachers see them.

`app.classroom_add_student` — game/app.py:2561

- **db** → `add_classroom_student`, `can_see_student`, `classroom_in_org`, `teaches_classroom`, `user_by_id`, `user_by_username`

### `GET/POST /classrooms/<int:classroom_id>/students/import`

Create a whole class at once from a pasted list.

`app.classroom_import_students` — game/app.py:2768

- **billing** → `enabled`, `update_seats`
- **db** → `classroom_in_org`, `count_billable_seats`, `create_student_in_classroom`, `subscription_for_org`, `teaches_classroom`, `user_by_id`, `username_taken`, `write`
- **security** → `temp_password`, `username_problem`

### `POST /classrooms/<int:classroom_id>/students/new`

Create one student account straight into this classroom.

`app.classroom_new_student` — game/app.py:2710

- **billing** → `enabled`, `update_seats`
- **db** → `classroom_in_org`, `count_billable_seats`, `create_student_in_classroom`, `subscription_for_org`, `teaches_classroom`, `user_by_id`, `username_taken`, `write`
- **security** → `temp_password`, `username_problem`

### `POST /classrooms/<int:classroom_id>/students/remove`

Take a student out of a classroom.

`app.classroom_remove_student` — game/app.py:2579

- **db** → `can_see_student`, `classroom_in_org`, `remove_classroom_student`, `teaches_classroom`, `user_by_id`, `user_by_username`

### `POST /classrooms/<int:classroom_id>/teachers/add`

Assign a teacher to a classroom.

`app.classroom_add_teacher` — game/app.py:2596

- **db** → `add_classroom_teacher`, `classroom_in_org`, `member_in_org`, `teaches_classroom`, `user_by_id`

### `POST /classrooms/<int:classroom_id>/teachers/remove`

Unassign a teacher, revoking their sight of that classroom's students.

`app.classroom_remove_teacher` — game/app.py:2617

- **db** → `classroom_in_org`, `member_in_org`, `remove_classroom_teacher`, `teaches_classroom`, `user_by_id`

### `POST /classrooms/new`

Create a classroom and put its creator in it.

`app.classroom_create` — game/app.py:2485

- **db** → `add_classroom_teacher`, `create_classroom`, `user_by_id`

### `GET/POST /forgot`

Start a password reset.

`app.forgot_password` — game/app.py:1056

- **db** → `invalidate_tokens`, `store_token`, `user_by_email`, `write`
- **emailer** → `send_reset`
- **security** → `client_ip`, `new_token`, `over_limit`, `record_attempt`

### `GET /grownup`

Answers "is my kid doing the work?" without any digging: a headline per student, and anything needing attentio

`app.grownup_home` — game/app.py:1889

- **db** → `org_by_id`, `summaries_for`, `unresolved_counts`, `user_by_id`, `visible_students`

### `POST /grownup/link`

A parent attaches themselves to a student with the student's link code.

`app.link_child` — game/app.py:2382

- **db** → `link_parent`, `student_by_link_code`, `user_by_id`

### `GET /grownup/resources`

Everything a grown-up can download, by track.

`app.resources_home` — game/app.py:2151

- **billing** → `entitlement_for`, `lesson_is_free`
- **db** → `user_by_id`
- **tracks** → `visible_resources`

### `GET /grownup/resources/<kind>/<owner_id>/<path:filename>`

Hand over one file, to a grown-up who is allowed it.

`app.resource_download` — game/app.py:2194

- **billing** → `entitlement_for`, `lesson_is_free`
- **db** → `user_by_id`
- **tracks** → `visible_resources`

### `GET /grownup/resources/<kind>/<owner_id>/<path:filename>/read`

Read a Markdown guide in the browser rather than downloading it.

`app.resource_read` — game/app.py:2224

- **billing** → `entitlement_for`, `lesson_is_free`
- **db** → `user_by_id`
- **tracks** → `visible_resources`

### `GET /grownup/student/<username>`

One student's full progress, for a grown-up.

`app.student_detail` — game/app.py:1950

- **db** → `assigned_lesson_ids`, `can_see_student`, `lesson_entries`, `summaries_for`, `user_by_id`, `user_by_username`
- **standards** → `grade_for_age`, `report`
- **tracks** → `gate`, `requirement_block`, `visible_resources`

### `POST /grownup/student/<username>/assign`

Narrow (or re-widen) which lessons show up on one student's menu.

`app.student_assign` — game/app.py:2361

- **db** → `can_see_student`, `set_assignment`, `user_by_id`, `user_by_username`

### `POST /grownup/student/<username>/delete`

Erase a student account on request.

`app.student_delete` — game/app.py:2914

- **billing** → `enabled`, `update_seats`
- **db** → `can_see_student`, `count_billable_seats`, `delete_user`, `subscription_for_org`, `user_by_id`, `user_by_username`

### `POST /grownup/student/<username>/grade`

Record which grade a student is in.

`app.set_student_grade` — game/app.py:2324

- **db** → `can_see_student`, `set_grade_level`, `user_by_id`, `user_by_username`
- **standards** → `grade_label`

### `POST /grownup/student/<username>/reset-password`

Give a student a new password, because they forgot theirs.

`app.student_reset_password` — game/app.py:2879

- **db** → `can_see_student`, `set_password`, `user_by_id`, `user_by_username`
- **security** → `clear_attempts`, `temp_password`

### `GET /grownup/student/<username>/standards`

One student against one grade's standards.

`app.student_standards` — game/app.py:2266

- **db** → `can_see_student`, `lesson_statuses`, `user_by_id`, `user_by_username`
- **standards** → `grade_for_age`, `report`

### `GET /healthz`

Readiness: can this process actually do its job right now?

`app.healthz` — game/app.py:643

- **db** → `healthy`

### `GET /lesson/<lesson_id>`

Open one lesson, if this student may.

`app.lesson` — game/app.py:1636

- **billing** → `entitlement_for`, `lesson_is_free`
- **db** → `assigned_lesson_ids`, `lesson_entries`, `lesson_statuses`, `set_lesson_status`, `summaries_for`, `user_by_id`
- **tracks** → `gate`, `required_lesson_ids`, `requirement_block`

### `GET /lessons`

The lesson menu, organised by track.

`app.lessons` — game/app.py:1552

- **billing** → `entitlement_for`, `lesson_is_free`
- **db** → `assigned_lesson_ids`, `lesson_entries`, `summaries_for`, `user_by_id`
- **tracks** → `gate`, `progress`, `requirement_block`

### `GET /locked`

Where a student lands on a lesson that will not open.

`app.locked` — game/app.py:2942

- **billing** → `entitlement_for`
- **db** → `assigned_lesson_ids`, `lesson_statuses`, `user_by_id`
- **tracks** → `gate`, `required_lesson_ids`, `requirement_block`

### `GET/POST /login`

Sign in, without telling an attacker anything they did not already know.

`app.login` — game/app.py:817

- **db** → `touch_login`, `user_by_id`, `user_by_username`
- **security** → `clear_attempts`, `client_ip`, `over_limit`, `record_attempt`, `rotate_csrf_token`, `safe_next`

### `GET /org`

`app.org_home` — game/app.py:2977

- **billing** → `entitlement_for`
- **db** → `count_billable_seats`, `count_org_admins`, `org_by_id`, `org_members`, `pending_members`, `subscription_for_org`, `user_by_id`

### `POST /org/join-policy`

`app.org_join_policy` — game/app.py:3011

- **db** → `set_join_policy`, `user_by_id`

### `POST /org/members/<member_id>/admin`

Promote a teacher to admin, or demote one.

`app.org_set_admin` — game/app.py:3075

- **db** → `count_org_admins`, `member_in_org`, `set_org_admin`, `user_by_id`

### `POST /org/members/<member_id>/approve`

`app.org_approve_member` — game/app.py:3034

- **billing** → `enabled`, `update_seats`
- **db** → `count_billable_seats`, `member_in_org`, `set_membership_status`, `subscription_for_org`, `user_by_id`

### `POST /org/members/<member_id>/remove`

Put a member out of the organisation.

`app.org_remove_member` — game/app.py:3046

- **billing** → `enabled`, `update_seats`
- **db** → `count_billable_seats`, `count_org_admins`, `member_in_org`, `set_membership_status`, `subscription_for_org`, `user_by_id`

### `POST /org/rotate-code`

`app.org_rotate_code` — game/app.py:3025

- **db** → `rotate_join_code`, `user_by_id`

### `GET /pending`

Holding page for a member an admin has not let in yet.

`app.pending` — game/app.py:774

- **db** → `org_by_id`, `user_by_id`

### `GET/POST /reset/<token>`

`app.reset_password` — game/app.py:1094

- **db** → `consume_token`, `set_password`
- **security** → `clear_attempts`, `hash_token`, `password_problem`

### `GET /satchel`

The student's trinket collection.

`app.satchel` — game/app.py:1694

- **db** → `inventory`, `summaries_for`, `user_by_id`

### `GET /settings`

Change your own password, or delete your own account.

`app.settings_home` — game/app.py:1210

- **db** → `active_paid_subscription_for`, `count_org_admins`, `user_by_id`

### `POST /settings/delete`

Erase your own account and everything attached to it.

`app.delete_own_account` — game/app.py:1328

- **db** → `active_paid_subscription_for`, `count_org_admins`, `delete_user`, `user_by_id`

### `GET/POST /settings/first-password`

The one page an account with must_change_password can reach.

`app.first_password` — game/app.py:1272

- **db** → `set_password`, `user_by_id`
- **security** → `password_problem`, `rotate_csrf_token`

### `POST /settings/password`

Change your own password, proving you know the current one first.

`app.change_password` — game/app.py:1221

- **db** → `active_paid_subscription_for`, `count_org_admins`, `set_password`, `user_by_id`
- **security** → `client_ip`, `over_limit`, `password_problem`, `record_attempt`, `rotate_csrf_token`

### `GET/POST /signup`

Self-serve registration for all three roles.

`app.signup` — game/app.py:893

- **db** → `create_org`, `create_user`, `email_taken`, `org_by_join_code`, `store_token`, `user_by_id`, `username_taken`, `write`
- **emailer** → `send_verification`
- **security** → `client_ip`, `email_problem`, `new_token`, `over_limit`, `password_problem`, `record_attempt`, `rotate_csrf_token`, `username_problem`

### `POST /stripe/webhook`

Stripe telling us something changed.

`app.stripe_webhook` — game/app.py:3317

- **billing** → `enabled`, `handle_event`, `verify_webhook`
- **db** → `claim_event`, `finish_event`, `release_event`

### `GET /verify/<token>`

`app.verify_email` — game/app.py:1009

- **db** → `consume_token`, `mark_verified`, `write`
- **security** → `hash_token`, `rotate_csrf_token`

### `POST /verify/resend`

Send another confirmation link, and say nothing about who has an account.

`app.resend_verification` — game/app.py:1024

- **db** → `invalidate_tokens`, `store_token`, `user_by_email`, `write`
- **emailer** → `send_verification`
- **security** → `client_ip`, `new_token`, `over_limit`, `record_attempt`

---

## Module summary

| Module | Layer | Functions | Routes | Imports |
|---|---|---|---|---|
| `import_assets.py` | entrypoint | 5 | 0 | — |
| `manage.py` | entrypoint | 13 | 0 | `billing`, `config`, `db`, `logsetup` |
| `migrate_json.py` | entrypoint | 3 | 0 | `config`, `db` |
| `selftest.py` | entrypoint | 46 | 0 | `app`, `db`, `security` |
| `selftest_accounts.py` | entrypoint | 62 | 0 | `app`, `db`, `security` |
| `selftest_billing.py` | entrypoint | 50 | 0 | `app`, `billing`, `db` |
| `selftest_classrooms.py` | entrypoint | 35 | 0 | `app`, `db`, `tracks` |
| `selftest_gating.py` | entrypoint | 47 | 0 | `app`, `db`, `tracks` |
| `selftest_resources.py` | entrypoint | 37 | 0 | `app`, `db`, `tracks` |
| `selftest_standards.py` | entrypoint | 48 | 0 | `app`, `db`, `standards` |
| `wsgi.py` | entrypoint | 0 | 0 | `app` |
| `app.py` | web | 126 | 63 | `billing`, `config`, `db`, `emailer`, `logsetup`, `security`, `standards`, `tracks` |
| `billing.py` | service | 21 | 0 | `db` |
| `emailer.py` | service | 4 | 0 | — |
| `security.py` | service | 18 | 0 | `db` |
| `standards.py` | service | 8 | 0 | — |
| `tracks.py` | service | 18 | 0 | — |
| `db.py` | data | 93 | 0 | — |
| `config.py` | platform | 3 | 0 | — |
| `logsetup.py` | platform | 2 | 0 | — |
