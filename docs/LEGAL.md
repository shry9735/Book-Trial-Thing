# Legal pages

Signup requires ticking a box that says *I agree to the Terms of Service and
the Privacy Notice*. This is what sits behind that box, how to fill it in,
and what it does not do.

- [What ships](#what-ships)
- [Read this first](#read-this-first)
- [Filling it in](#filling-it-in)
- [Editing the wording](#editing-the-wording)
- [What a lawyer should look at](#what-a-lawyer-should-look-at)
- [What is still missing](#what-is-still-missing)

---

## What ships

| Path | Rendered at |
|---|---|
| `game/content/legal/terms.md` | `/legal/terms` |
| `game/content/legal/privacy.md` | `/legal/privacy` |

Markdown, rendered by the same function that renders lesson prose, wrapped
in `templates/legal.html`. Both pages are public — somebody deciding whether
to sign up has nowhere to sign in to yet — and both are reachable by a
student who is being held on the first-password page.

They are linked from the signup consent checkbox, the login box, and the
account settings page.

## Read this first

**This wording has not been reviewed by a lawyer.** It was written to
describe how this software actually behaves — accurately, and in plain
language — which is a genuinely useful starting point and is not the same
thing as being legally sound where you operate.

Until you set `LEGAL_REVIEWED=true`:

- every legal page carries a visible **"Draft — not yet reviewed by a
  lawyer"** banner, and
- production prints a warning on every boot.

Set that flag when a lawyer has actually read the pages, and not before. It
is the only thing that removes the banner.

Separately, `APP_ENV=production` **refuses to boot** until `LEGAL_ENTITY`,
`LEGAL_EMAIL` and `LEGAL_JURISDICTION` are set. That one is not a judgement
call: the pages would otherwise render `[YOUR COMPANY NAME]` to people being
asked to agree to them, which makes the consent worthless.

## Filling it in

Six environment variables, all in `.env.example`:

| Variable | Example | Notes |
|---|---|---|
| `LEGAL_ENTITY` | `Ignite Academy LLC` | The legal entity, exactly as it should appear |
| `LEGAL_EMAIL` | `privacy@example.com` | Where deletion requests and complaints go. Somebody has to actually read it |
| `LEGAL_ADDRESS` | `1 Example Way, Columbus, OH 43215` | Optional in the code, expected in most jurisdictions |
| `LEGAL_JURISDICTION` | `the State of Ohio, USA` | Reads as "governed by the laws of ___" |
| `LEGAL_EFFECTIVE` | `1 September 2026` | The date this wording took effect |
| `LEGAL_REVIEWED` | `false` | See above |

## Editing the wording

Edit the Markdown. `{{TOKEN}}` placeholders are substituted at render time
from `app._legal_tokens()`:

`{{ENTITY}}` `{{EMAIL}}` `{{ADDRESS}}` `{{JURISDICTION}}` `{{EFFECTIVE}}`
`{{MIN_AGE}}` `{{INVOICE_DUE_DAYS}}` `{{GRACE_DAYS_CARD}}`
`{{GRACE_DAYS_INVOICE}}`

The last four are read from the same config the billing and signup code
reads. That is deliberate: the terms promise a 30-day invoice period and a
14-day card grace period, and those are promises the software has to keep.
Typing the numbers into the prose would let the page and the behaviour drift
apart silently, so `selftest_accounts.py` asserts the rendered page still
quotes the configured values.

Substitution happens *before* the Markdown is rendered, so a config value
cannot inject markup.

If you change the wording materially, update `LEGAL_EFFECTIVE` and tell your
existing account holders — the terms themselves promise you will.

## What a lawyer should look at

Points where the boilerplate takes a position you may want changed:

- **Teacher-created student accounts.** §2 of the terms puts the burden of
  parental notice and consent on the school. That mirrors how districts
  normally work and how the software behaves, but whether it is sufficient
  depends on your state and on whether you are a "school official" under
  FERPA. If you sell to districts you will be handed a DPA to sign, and it
  will override some of this.
- **Age 13.** The whole product assumes it. Below 13, COPPA applies and this
  application is not built for it — there is no verifiable parental consent
  flow. `MIN_AGE` is configurable; lowering it does not make you compliant.
- **Limitation of liability** (§9) is capped at twelve months of fees. Some
  jurisdictions will not enforce that; some customers will negotiate it.
- **Refunds** (§4) are discretionary beyond "it didn't work". Consumer law
  where you sell may require more, particularly for subscriptions.
- **Governing law** (§11) assumes you can compel your customers into your
  own courts. Against a school district that is often the first thing struck
  out.
- **The privacy notice claims no third-party analytics or advertising.** That
  is true today — there are no third-party scripts, cookies or pixels in the
  templates. If you ever add one, that sentence becomes false and you must
  change it.
- **Sub-processors.** §4 of the notice names Stripe, a hosting provider and
  an email provider generically. GDPR and several US state laws expect them
  named specifically; fill them in once you have chosen.

## What is still missing

Deliberately out of scope here, and worth knowing:

- **No versioned consent.** `users.terms_accepted_at` records *when*
  somebody agreed, not *which version* they agreed to. If you materially
  change the terms you cannot currently prove who accepted what. Adding a
  `terms_version` column and re-prompting on change is the fix.
- **No cookie banner.** None is needed for the one first-party session
  cookie the app sets, which is strictly necessary for sign-in. Add any
  third-party cookie and that changes.
- **No DPA template** for school customers, and no signed sub-processor
  agreements.
- **No accessibility statement**, which some public-sector buyers require.

---

**Next:** [Data model](DATA_MODEL.md) · [Architecture](ARCHITECTURE.md) ·
[Deploying](../DEPLOY.md)
