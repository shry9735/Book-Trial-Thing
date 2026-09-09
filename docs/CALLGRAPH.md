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
    selftest_standards --> app
    selftest_standards --> db
    selftest_standards --> standards
    wsgi --> app
```

No layering violations: every import points downward.

---

## Routes

60 routes. **Guards** are the decorators that must pass before
the handler runs; **touches** is every other module the handler reaches,
following local helpers.

| Route | Methods | Guards | Handler | Touches |
|---|---|---|---|---|
| `/` | GET | — | `app.home` | `db` |
| `/api/example` | POST | signed in | `app.api_example` | `billing`, `db`, `tracks` |
| `/api/examples/<lesson_id>` | GET | signed in | `app.api_examples` | `billing`, `db`, `tracks` |
| `/api/progress` | POST | signed in | `app.api_progress` | `billing`, `db`, `tracks` |
| `/api/quiz` | POST | signed in | `app.api_quiz` | `billing`, `db`, `tracks` |
| `/api/quiz/finish` | POST | signed in | `app.api_quiz_finish` | `billing`, `db`, `tracks` |
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
| `/grownup/link` | POST | signed in | `app.link_child` | `db` |
| `/grownup/student/<username>` | GET | signed in | `app.student_detail` | `db` |
| `/grownup/student/<username>/assign` | POST | signed in | `app.student_assign` | `db` |
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

`app.home` — game/app.py:721

- **db** → `user_by_id`

### `POST /api/example`

Record one practice-example answer and hand back the same correct/explain shape /api/quiz gives — Spark uses i

`app.api_example` — game/app.py:1664

- **billing** → `entitlement_for`, `lesson_is_free`
- **db** → `assigned_lesson_ids`, `lesson_statuses`, `record_example`, `user_by_id`
- **tracks** → `gate`

### `GET /api/examples/<lesson_id>`

Prompts and choices for a lesson's practice examples, answer key stripped — the same treatment the quiz gets.

`app.api_examples` — game/app.py:1644

- **billing** → `entitlement_for`, `lesson_is_free`
- **db** → `assigned_lesson_ids`, `lesson_statuses`, `user_by_id`
- **tracks** → `gate`

### `POST /api/progress`

Called by the lesson player, and by lessons via the kit's postMessage.

`app.api_progress` — game/app.py:1577

- **billing** → `entitlement_for`, `lesson_is_free`
- **db** → `assigned_lesson_ids`, `lesson_statuses`, `set_lesson_status`, `summaries_for`, `user_by_id`
- **tracks** → `gate`

### `POST /api/quiz`

Check one answer and record the attempt.

`app.api_quiz` — game/app.py:1607

- **billing** → `entitlement_for`, `lesson_is_free`
- **db** → `assigned_lesson_ids`, `lesson_statuses`, `record_answer`, `user_by_id`
- **tracks** → `gate`

### `POST /api/quiz/finish`

Score the quiz, complete the lesson, and hand back any reward earned.

`app.api_quiz_finish` — game/app.py:1703

- **billing** → `entitlement_for`, `lesson_is_free`
- **db** → `assigned_lesson_ids`, `lesson_entries`, `lesson_statuses`, `set_lesson_status`, `summaries_for`, `user_by_id`
- **tracks** → `gate`

### `GET /billing`

`app.billing_home` — game/app.py:2734

- **billing** → `entitlement_for`
- **db** → `count_billable_seats`, `invoices_for`, `org_by_id`, `subscription_for_org`, `subscription_for_parent`, `user_by_id`, `visible_students`

### `POST /billing/invoice-request`

Ask to be billed by invoice on terms instead of by card.

`app.billing_invoice_request` — game/app.py:2839

- **db** → `count_billable_seats`, `org_by_id`, `set_billing_profile`, `user_by_id`
- **emailer** → `send`
- **security** → `email_problem`

### `POST /billing/portal`

Stripe's hosted account page: change card, cancel, download invoices.

`app.billing_portal` — game/app.py:2798

- **billing** → `portal_session`
- **db** → `count_billable_seats`, `org_by_id`, `subscription_for_org`, `subscription_for_parent`, `user_by_id`, `visible_students`

### `GET /billing/return`

Where Stripe sends the browser after Checkout.

`app.billing_return` — game/app.py:2826

- **billing** → `entitlement_for`
- **db** → `user_by_id`

### `POST /billing/subscribe`

Send the payer to Stripe's hosted Checkout.

`app.billing_subscribe` — game/app.py:2753

- **billing** → `checkout_session`, `enabled`, `ensure_customer`
- **db** → `count_billable_seats`, `org_by_id`, `subscription_for_org`, `subscription_for_parent`, `user_by_id`, `visible_students`

### `GET /classroom`

`app.classroom` — game/app.py:1435

- **db** → `summaries_for`, `user_by_id`

### `GET /classrooms`

Every classroom this account may see.

`app.classrooms_home` — game/app.py:2011

- **db** → `classroom_membership`, `classroom_rows`, `summaries_for`, `unplaced_students`, `unresolved_counts`, `user_by_id`, `visible_students`

### `GET /classrooms/<int:classroom_id>`

One classroom: who teaches it, who is in it, how they are doing.

`app.classroom_detail` — game/app.py:2101

- **db** → `classroom_in_org`, `classroom_students`, `classroom_teachers`, `org_teachers`, `summaries_for`, `teaches_classroom`, `unresolved_counts`, `user_by_id`, `visible_students`

### `POST /classrooms/<int:classroom_id>/delete`

Delete a classroom.

`app.classroom_delete` — game/app.py:2225

- **db** → `delete_classroom`, `user_by_id`

### `POST /classrooms/<int:classroom_id>/students/add`

Put a student in a classroom, which is what lets its teachers see them.

`app.classroom_add_student` — game/app.py:2152

- **db** → `add_classroom_student`, `can_see_student`, `classroom_in_org`, `teaches_classroom`, `user_by_id`, `user_by_username`

### `GET/POST /classrooms/<int:classroom_id>/students/import`

Create a whole class at once from a pasted list.

`app.classroom_import_students` — game/app.py:2359

- **billing** → `enabled`, `update_seats`
- **db** → `classroom_in_org`, `count_billable_seats`, `create_student_in_classroom`, `subscription_for_org`, `teaches_classroom`, `user_by_id`, `username_taken`, `write`
- **security** → `temp_password`, `username_problem`

### `POST /classrooms/<int:classroom_id>/students/new`

Create one student account straight into this classroom.

`app.classroom_new_student` — game/app.py:2301

- **billing** → `enabled`, `update_seats`
- **db** → `classroom_in_org`, `count_billable_seats`, `create_student_in_classroom`, `subscription_for_org`, `teaches_classroom`, `user_by_id`, `username_taken`, `write`
- **security** → `temp_password`, `username_problem`

### `POST /classrooms/<int:classroom_id>/students/remove`

Take a student out of a classroom.

`app.classroom_remove_student` — game/app.py:2170

- **db** → `can_see_student`, `classroom_in_org`, `remove_classroom_student`, `teaches_classroom`, `user_by_id`, `user_by_username`

### `POST /classrooms/<int:classroom_id>/teachers/add`

Assign a teacher to a classroom.

`app.classroom_add_teacher` — game/app.py:2187

- **db** → `add_classroom_teacher`, `classroom_in_org`, `member_in_org`, `teaches_classroom`, `user_by_id`

### `POST /classrooms/<int:classroom_id>/teachers/remove`

Unassign a teacher, revoking their sight of that classroom's students.

`app.classroom_remove_teacher` — game/app.py:2208

- **db** → `classroom_in_org`, `member_in_org`, `remove_classroom_teacher`, `teaches_classroom`, `user_by_id`

### `POST /classrooms/new`

Create a classroom and put its creator in it.

`app.classroom_create` — game/app.py:2076

- **db** → `add_classroom_teacher`, `create_classroom`, `user_by_id`

### `GET/POST /forgot`

`app.forgot_password` — game/app.py:958

- **db** → `invalidate_tokens`, `store_token`, `user_by_email`, `write`
- **emailer** → `send_reset`
- **security** → `client_ip`, `new_token`, `over_limit`, `record_attempt`

### `GET /grownup`

Answers "is my kid doing the work?" without any digging: a headline per student, and anything needing attentio

`app.grownup_home` — game/app.py:1744

- **db** → `org_by_id`, `summaries_for`, `unresolved_counts`, `user_by_id`, `visible_students`

### `POST /grownup/link`

A parent attaches themselves to a student with the student's link code.

`app.link_child` — game/app.py:1973

- **db** → `link_parent`, `student_by_link_code`, `user_by_id`

### `GET /grownup/student/<username>`

One student's full progress, for a grown-up.

`app.student_detail` — game/app.py:1804

- **db** → `assigned_lesson_ids`, `can_see_student`, `lesson_entries`, `summaries_for`, `user_by_id`, `user_by_username`

### `POST /grownup/student/<username>/assign`

Narrow (or re-widen) which lessons show up on one student's menu.

`app.student_assign` — game/app.py:1953

- **db** → `can_see_student`, `set_assignment`, `user_by_id`, `user_by_username`

### `POST /grownup/student/<username>/delete`

Erase a student account on request.

`app.student_delete` — game/app.py:2505

- **billing** → `enabled`, `update_seats`
- **db** → `can_see_student`, `count_billable_seats`, `delete_user`, `subscription_for_org`, `user_by_id`, `user_by_username`

### `POST /grownup/student/<username>/grade`

Record which grade a student is in.

`app.set_student_grade` — game/app.py:1917

- **db** → `can_see_student`, `set_grade_level`, `user_by_id`, `user_by_username`
- **standards** → `grade_label`

### `POST /grownup/student/<username>/reset-password`

Give a student a new password, because they forgot theirs.

`app.student_reset_password` — game/app.py:2470

- **db** → `can_see_student`, `set_password`, `user_by_id`, `user_by_username`
- **security** → `clear_attempts`, `temp_password`

### `GET /grownup/student/<username>/standards`

One student against one grade's standards.

`app.student_standards` — game/app.py:1859

- **db** → `can_see_student`, `lesson_statuses`, `user_by_id`, `user_by_username`
- **standards** → `grade_for_age`, `report`

### `GET /healthz`

Readiness: can this process actually do its job right now?

`app.healthz` — game/app.py:577

- **db** → `healthy`

### `GET /lesson/<lesson_id>`

Open one lesson, if this student may.

`app.lesson` — game/app.py:1501

- **billing** → `entitlement_for`, `lesson_is_free`
- **db** → `assigned_lesson_ids`, `lesson_entries`, `lesson_statuses`, `set_lesson_status`, `summaries_for`, `user_by_id`
- **tracks** → `gate`

### `GET /lessons`

The lesson menu, organised by track.

`app.lessons` — game/app.py:1446

- **billing** → `entitlement_for`, `lesson_is_free`
- **db** → `assigned_lesson_ids`, `lesson_entries`, `summaries_for`, `user_by_id`
- **tracks** → `gate`, `progress`

### `GET /locked`

Where a student lands on a lesson that will not open.

`app.locked` — game/app.py:2533

- **billing** → `entitlement_for`
- **db** → `assigned_lesson_ids`, `lesson_statuses`, `user_by_id`
- **tracks** → `gate`

### `GET/POST /login`

`app.login` — game/app.py:738

- **db** → `touch_login`, `user_by_id`, `user_by_username`
- **security** → `clear_attempts`, `client_ip`, `over_limit`, `record_attempt`, `rotate_csrf_token`, `safe_next`

### `GET /org`

`app.org_home` — game/app.py:2568

- **billing** → `entitlement_for`
- **db** → `count_billable_seats`, `count_org_admins`, `org_by_id`, `org_members`, `pending_members`, `subscription_for_org`, `user_by_id`

### `POST /org/join-policy`

`app.org_join_policy` — game/app.py:2602

- **db** → `set_join_policy`, `user_by_id`

### `POST /org/members/<member_id>/admin`

`app.org_set_admin` — game/app.py:2658

- **db** → `count_org_admins`, `member_in_org`, `set_org_admin`, `user_by_id`

### `POST /org/members/<member_id>/approve`

`app.org_approve_member` — game/app.py:2625

- **billing** → `enabled`, `update_seats`
- **db** → `count_billable_seats`, `member_in_org`, `set_membership_status`, `subscription_for_org`, `user_by_id`

### `POST /org/members/<member_id>/remove`

`app.org_remove_member` — game/app.py:2637

- **billing** → `enabled`, `update_seats`
- **db** → `count_billable_seats`, `count_org_admins`, `member_in_org`, `set_membership_status`, `subscription_for_org`, `user_by_id`

### `POST /org/rotate-code`

`app.org_rotate_code` — game/app.py:2616

- **db** → `rotate_join_code`, `user_by_id`

### `GET /pending`

Holding page for a member an admin has not let in yet.

`app.pending` — game/app.py:695

- **db** → `org_by_id`, `user_by_id`

### `GET/POST /reset/<token>`

`app.reset_password` — game/app.py:988

- **db** → `consume_token`, `set_password`
- **security** → `clear_attempts`, `hash_token`, `password_problem`

### `GET /satchel`

The student's trinket collection.

`app.satchel` — game/app.py:1554

- **db** → `inventory`, `summaries_for`, `user_by_id`

### `GET /settings`

Change your own password, or delete your own account.

`app.settings_home` — game/app.py:1104

- **db** → `active_paid_subscription_for`, `count_org_admins`, `user_by_id`

### `POST /settings/delete`

Erase your own account and everything attached to it.

`app.delete_own_account` — game/app.py:1222

- **db** → `active_paid_subscription_for`, `count_org_admins`, `delete_user`, `user_by_id`

### `GET/POST /settings/first-password`

The one page an account with must_change_password can reach.

`app.first_password` — game/app.py:1166

- **db** → `set_password`, `user_by_id`
- **security** → `password_problem`, `rotate_csrf_token`

### `POST /settings/password`

Change your own password, proving you know the current one first.

`app.change_password` — game/app.py:1115

- **db** → `active_paid_subscription_for`, `count_org_admins`, `set_password`, `user_by_id`
- **security** → `client_ip`, `over_limit`, `password_problem`, `record_attempt`, `rotate_csrf_token`

### `GET/POST /signup`

Self-serve registration for all three roles.

`app.signup` — game/app.py:803

- **db** → `create_org`, `create_user`, `email_taken`, `org_by_join_code`, `store_token`, `user_by_id`, `username_taken`, `write`
- **emailer** → `send_verification`
- **security** → `client_ip`, `email_problem`, `new_token`, `over_limit`, `password_problem`, `record_attempt`, `rotate_csrf_token`, `username_problem`

### `POST /stripe/webhook`

`app.stripe_webhook` — game/app.py:2892

- **billing** → `enabled`, `handle_event`, `verify_webhook`
- **db** → `claim_event`, `finish_event`, `release_event`

### `GET /verify/<token>`

`app.verify_email` — game/app.py:919

- **db** → `consume_token`, `mark_verified`, `write`
- **security** → `hash_token`, `rotate_csrf_token`

### `POST /verify/resend`

`app.resend_verification` — game/app.py:934

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
| `selftest.py` | entrypoint | 44 | 0 | `app`, `db`, `security` |
| `selftest_accounts.py` | entrypoint | 62 | 0 | `app`, `db`, `security` |
| `selftest_billing.py` | entrypoint | 50 | 0 | `app`, `billing`, `db` |
| `selftest_classrooms.py` | entrypoint | 35 | 0 | `app`, `db`, `tracks` |
| `selftest_standards.py` | entrypoint | 48 | 0 | `app`, `db`, `standards` |
| `wsgi.py` | entrypoint | 0 | 0 | `app` |
| `app.py` | web | 117 | 60 | `billing`, `config`, `db`, `emailer`, `logsetup`, `security`, `standards`, `tracks` |
| `billing.py` | service | 21 | 0 | `db` |
| `emailer.py` | service | 4 | 0 | — |
| `security.py` | service | 18 | 0 | `db` |
| `standards.py` | service | 8 | 0 | — |
| `tracks.py` | service | 9 | 0 | — |
| `db.py` | data | 93 | 0 | — |
| `config.py` | platform | 3 | 0 | — |
| `logsetup.py` | platform | 2 | 0 | — |
