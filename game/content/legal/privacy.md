# Privacy Notice

**Effective:** {{EFFECTIVE}}  
**Controller:** {{ENTITY}}

This explains what Ignite Academy collects, why, and what you can do about
it. It is written to be read, not to be survived.

**The short version.** We collect the minimum needed to run a lesson and
show a grown-up how a child is getting on. We do not sell it, we do not
advertise, we do not track you around the internet, and we never see your
card number.

## 1. What we collect

**When you make an account:** your name, a username, a password (stored only
as a scrambled hash we cannot reverse), your role, and the organisation you
belong to. An email address, **unless** a teacher created the account for
you — school-created student accounts have no email address at all.

**As you use the lessons:** which lessons you opened and finished, your quiz
and practice answers, whether they were right, how many tries you took, and
any rewards earned.

**Automatically:** a first-party session cookie so you stay signed in, and
ordinary server logs (IP address, time, page requested, errors). We keep a
one-way hash of your IP address or username for a short period to stop
password-guessing attacks — the record cannot be turned back into either.

**If you pay:** your billing email and a Stripe customer reference, plus
invoice amounts and dates. **Card numbers never reach our servers.** Payment
happens on Stripe's own pages.

**We do not use** third-party analytics, advertising networks, social
plug-ins, or tracking pixels. There are no third-party cookies.

## 2. Why we collect it

| What | Why |
|---|---|
| Account details | To let you sign in and to keep organisations separate |
| Lesson and quiz records | To show progress, and to tell a teacher where a student is stuck |
| Email address | To confirm the account and reset a password |
| Payment records | To take payment and meet accounting and tax obligations |
| Logs and rate-limit records | To keep the Service secure and working |

We do not use anything a student does to build an advertising profile, and
we do not sell or rent personal information to anyone.

## 3. Children

Accounts require the holder to be at least {{MIN_AGE}}. We do not knowingly
collect information from children under 13, and we delete it if we find it.

**In a school setting**, we act on the school's instructions in respect of
student data. The school decides who is enrolled, which teacher sees which
students, and when a record is deleted. Parents should raise questions about
a school-created account with the school first — they can act on it
immediately, and we will support them.

A parent who links to their child's account can see that child's progress.
A teacher sees only students in the classrooms they are assigned to. An
organisation administrator sees their whole organisation. Nobody can see
into another organisation at all.

## 4. Who we share it with

Only the processors that make the Service work:

| Who | What they get | Why |
|---|---|---|
| Our hosting provider | Everything, at rest and in transit | To run the servers and database |
| Stripe | Billing name, email, and payment details you give them directly | To take payment |
| Our email provider | Address and message content | To send confirmation and password-reset emails |

We may also disclose information if the law requires it, or to protect
someone's safety. If the business is ever sold or merged, account data may
transfer with it — you would be told before that happened.

## 5. Where it lives, and how long

Data is stored on servers operated by our hosting provider. Connections
between your browser and us, and between our servers and the database, are
encrypted.

We keep account and progress data while the account is open. When an account
is deleted, its work is deleted with it, straight away — there is no
recovery window. Two exceptions:

- **Invoices** are kept for as long as tax and accounting law requires. They
  hold amounts and dates, not schoolwork.
- **Security logs** age out on their own within a short period.

## 6. Your rights

You can:

- **See and correct** your details from your account settings.
- **Change your password** at any time from the same place.
- **Delete your account**, and everything attached to it, from your account
  settings. This is permanent.
- **Ask for a copy** of your data, or ask us to delete an account you cannot
  reach yourself, by writing to {{EMAIL}}.
- **Complain** to your local data protection authority if you think we have
  got this wrong.

Students in a school organisation cannot delete their own account, because
it belongs to the school. Ask a teacher or an administrator — they can
delete it, including all of the work in it.

Depending on where you live you may have further rights (for example under
the GDPR or the CCPA), including to object to or restrict processing, and to
data portability. Write to {{EMAIL}} and we will honour them. We do not
discriminate against anyone for exercising a privacy right.

## 7. Security

Passwords are stored using scrypt with a per-account salt. Password-reset
and email-confirmation links are stored only as hashes, so a copy of our
database would not yield a working link. Session cookies are signed,
HTTP-only, and invalidated the moment a password changes. Access to the
production database is restricted to the people who operate the Service.

No system is perfectly secure. If we suffer a breach affecting your data, we
will tell you and the relevant authority as the law requires.

## 8. Changes

If we change this notice materially we will tell account holders before it
takes effect. The effective date at the top tells you which version you are
reading.

## 9. Contact

Questions, requests, or complaints:

{{ENTITY}}  
{{ADDRESS}}  
{{EMAIL}}
