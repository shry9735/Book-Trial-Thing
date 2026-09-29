# Running the demo

One command, from a fresh clone to a populated school:

```bash
git clone <your-repo-url> Book-Trial-Thing
cd Book-Trial-Thing
./demo.sh
```

That builds the images, starts Postgres and the app, waits for the app to
report ready, loads a demo school, and prints the URL and the logins.

First run on a **Raspberry Pi 5** takes roughly 4–6 minutes, nearly all of
it pulling images. Later runs start in about 20 seconds. On a laptop,
halve both.

```
./demo.sh            start; seed only if the demo is not already there
./demo.sh --reset    put the demo data back to its starting state
./demo.sh --fresh    destroy the database volume and start over
./demo.sh --stop     stop everything, keep the data
./demo.sh --logins   reprint the accounts and the URL
```

---

## On a laptop

The same `./demo.sh`, and usually faster — about 2–3 minutes for a first
run, ten seconds after that. Every image in the stack is multi-arch, so
Apple Silicon and x86-64 both pull a native build with nothing to
configure.

| | What you need |
|---|---|
| **macOS** | Docker Desktop. Run `./demo.sh` in Terminal. |
| **Linux** | Docker Engine plus the Compose v2 plugin, same as the Pi. |
| **Windows** | Docker Desktop with the WSL2 backend, and **run `./demo.sh` from inside WSL** — it is a bash script, and the paths and networking work there. Cloning into the WSL filesystem rather than `/mnt/c` also makes the build noticeably faster. |

Running it on both the Pi and a laptop at once is fine — they are separate
databases and neither knows about the other. Worth doing if the Pi is the
demo and the laptop is the backup.

---

## What you need on the Pi

64-bit Raspberry Pi OS, and Docker with the Compose v2 plugin:

```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER      # then log out and back in
sudo apt install -y docker-compose-plugin
```

Nothing else. No Python on the host, no Postgres on the host.

`demo.sh` checks all of this before it builds anything and tells you the
exact command to run if something is missing. The one thing it refuses
outright is a **32-bit** OS: the Postgres driver ships 64-bit wheels only,
so a 32-bit build tries to compile libpq from source and fails after
several minutes. Confirm with `getconf LONG_BIT` — you want `64`.

---

## Demoing from another device

`demo.sh` writes `BASE_URL` in `.env` using this machine's LAN address, so
the app is reachable from a phone or a second laptop on the same wifi. The
banner prints that address when it finishes.

If the Pi is on a different interface from the one it guessed, edit
`BASE_URL` and `APP_PORT` in `.env` and run `./demo.sh` again.

> Conference wifi often blocks device-to-device traffic. If a phone cannot
> reach the Pi, tether the Pi to your own hotspot, or demo from the Pi's
> own browser. Worth testing this in the room before you present, not on
> the slide before.

---

## The accounts

Every account uses the same password: **`rivera-demo-2026`**

| Role | Username | What it shows |
|---|---|---|
| teacher | `ms_chen` | Org admin — sees every student, plus billing and the roster |
| teacher | `mr_diaz` | Not an admin — sees Period 3 only |
| parent | `parent_reyes` | Two children, in different classrooms |
| student | `maya` | Ahead — a finished track, trinkets earned |
| student | `theo` | Stuck on two questions — what the teacher view exists to catch |
| student | `jordan` | Quiet for 11 days — flagged as idle |
| student | `lena` | Only two lessons assigned — the gating story |
| student | `elliot` | In no classroom — only an admin can see them |

The demo org is comped for a year, so no lesson hits a paywall while
you are talking.

---

## A run of show

Fifteen minutes, in the order the product makes sense.

**1. The student (`maya`) — 3 min.**
Land on the classroom, open *Today's Lessons*. Point out that lessons are
grouped into tracks and that later ones say *"Opens when you finish…"*.
Open **Meet the Breadboard**, answer a question wrong on purpose, and show
that the explanation teaches rather than scolds. Check the backpack.

**2. The gate (`lena`) — 1 min.**
Sign in as Lena. Her menu has two lessons on it, not eight, because her
teacher assigned exactly those. This is the difference between "the
catalog" and "your work".

**3. The teacher (`ms_chen`) — 5 min.**
This is the centrepiece. *Worth a look* has already sorted the class: Theo
is stuck, Jordan has gone quiet. Open **Theo** and show **Still getting
these wrong** — the actual questions, what he chose, and why the right
answer is right. That is the thing a gradebook cannot do.

Then hit **Against the standards**: his lessons mapped to NGSS, CSTA and
Common Core codes for his grade, with an honest note that no national
curriculum exists and the match is our own reading.

**4. The boundary (`mr_diaz`) — 1 min.**
Sign in as Mr. Diaz. Same school, but he sees three students, not eight,
because he teaches one classroom. Privacy is structural here, not a
setting somebody has to remember to switch on.

**5. The parent (`parent_reyes`) — 3 min.**
Two children in different classrooms, one view. Then **Helping at home** —
guides and answer keys that only a grown-up account can reach. Worth
saying plainly: a student who guesses the URL gets a 404, not the answers.

**6. Where content comes from — 2 min.**
`docs/SUBAPPS.md` if anyone asks how new lessons get built. The short
version: a lesson is a folder with a manifest, it runs in its own iframe,
it talks to the platform through one small bridge, and it shares artwork
with every other lesson so updating a character updates all of them.

---

## If something goes wrong

**The app never becomes ready.** `demo.sh` prints the last 40 lines of the
app log when it gives up. Usually the database is still starting on a cold
Pi; run `./demo.sh` again.

**Port 8000 is taken.** Edit `APP_PORT` in `.env`, then `./demo.sh`.

**The demo data looks wrong** — you clicked through it in rehearsal and
completed something. `./demo.sh --reset` puts it back in about five
seconds. Do this between rehearsal and the real thing.

**Everything is wedged.** `./demo.sh --fresh` destroys the database volume
and rebuilds from nothing. Two minutes on a Pi, and it regenerates `.env`.

**You need the logins again.** `./demo.sh --logins`.

---

## What this is not

Worth knowing before somebody asks a question you have to dodge.

- **No TLS.** `APP_ENV=local` deliberately waives the checks a machine with
  no certificate cannot pass. Do not point this at the internet.
- **Known passwords, printed on a terminal.** `seed_demo.py` refuses to run
  when `APP_ENV=production`.
- **Payments are not configured.** Without Stripe keys the billing screens
  say so rather than erroring. Add keys to `.env` if you want to demo
  checkout; see `DEPLOY.md`.
- **The lesson artwork is generated stand-in vector art**, drawn by
  `scripts/make_thumbs.py`. Drop a real `.webp` or `.png` into
  `game/static/art/lessons/<lesson-id>.<ext>` and it wins automatically.
- **The Terms and Privacy pages are unreviewed boilerplate** and say so on
  the page. See `docs/LEGAL.md`.
