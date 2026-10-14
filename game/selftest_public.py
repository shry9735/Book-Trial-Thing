#!/usr/bin/env python3
"""
selftest_public.py — the public site: landing page, blog, books, feeds.

These are the only pages a visitor sees before they have an account, which
makes them the only pages anybody at all can reach. What this suite holds
them to:

    the way in     Log in and Create account at the top of every public
                   page, and a signed-in visitor sent straight past the
                   landing page to where they work
    publishing     drafts visible on a laptop or the demo Pi and invisible
                   in production; a post dated in the future hidden until
                   its date; a broken post skipped rather than fatal
    caching        one URL, two different pages (signed in or not), so
                   never a `public` cache header on any of them
    privacy        nothing loaded from another site: these pages are read
                   by parents of children
    input          the slug is a URL segment that becomes a folder name,
                   so anything that is not a plain slug is a 404

Every check that needs particular posts builds them in a temporary content
folder and points the app at it, so the real posts in game/content/blog are
never touched and the suite does not change when they do.

    DATABASE_URL=postgresql://.../ignite_test python selftest_public.py
"""

import json
import os
import re
import shutil
import sys
import tempfile
import xml.etree.ElementTree as ET
from contextlib import contextmanager
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

os.environ.setdefault("APP_ENV", "development")
os.environ.setdefault("REQUIRE_EMAIL_VERIFICATION", "0")
os.environ.setdefault("SECRET_KEY", "0" * 64)
os.environ.setdefault("RL_SIGNUP_IP", "10000")

if os.environ.get("APP_ENV") == "production":
    sys.exit("selftest refuses to run against APP_ENV=production")

import app as appmod        # noqa: E402
import blog                 # noqa: E402
import db                   # noqa: E402

PASSED, FAILED = [], []
PASSWORD = "correct-horse-battery"
ATOM = "{http://www.w3.org/2005/Atom}"
SITEMAP = "{http://www.sitemaps.org/schemas/sitemap/0.9}"


def check(name):
    def decorator(fn):
        def run():
            try:
                fn()
                PASSED.append(name)
                print(f"  \033[32mPASS\033[0m  {name}")
            except Exception as exc:
                FAILED.append((name, exc))
                print(f"  \033[31mFAIL\033[0m  {name}\n          {type(exc).__name__}: {exc}")
        run.__name__ = fn.__name__
        return run
    return decorator


def reset_database():
    with db.write() as cur:
        cur.execute("DROP SCHEMA public CASCADE")
        cur.execute("CREATE SCHEMA public")
    db.migrate()


def client():
    return appmod.app.test_client()


def token_from(html: str) -> str:
    match = re.search(r'name="csrf_token" value="([^"]+)"', html)
    assert match, "no CSRF token in the page"
    return match.group(1)


def signup(c, role, **fields):
    page = c.get(f"/signup?role={role}").get_data(as_text=True)
    data = {"csrf_token": token_from(page), "name": fields.get("name", "Test"),
            "username": fields["username"], "email": fields["email"],
            "password": PASSWORD, "password_confirm": PASSWORD, "terms_ok": "1"}
    if role == "student":
        data["age_ok"] = "1"
        data["join_code"] = fields["join_code"]
    elif role == "parent":
        data["join_code"] = fields["join_code"]
    else:
        data["org_name"] = fields.get("org_name", "Test School")
    return c.post(f"/signup?role={role}", data=data, follow_redirects=True)


def signed_in(username):
    c = client()
    page = c.get("/login").get_data(as_text=True)
    c.post("/login", data={"csrf_token": token_from(page),
                           "username": username, "password": PASSWORD},
           follow_redirects=True)
    return c


def top_bar(html: str) -> str:
    match = re.search(r'<header class="site-top">(.*?)</header>', html, re.S)
    assert match, "no site header on the page"
    return match.group(1)


# ── Content fixtures ────────────────────────────────────────────────────────────

def today() -> date:
    """The date the app schedules by: UTC, not this machine's local date."""
    return datetime.now(timezone.utc).date()


def write_post(root: Path, slug: str, *, title=None, when=None, draft=False,
               body="Some words.\n\n## A heading\n\nMore words.", **extra):
    folder = root / "blog" / slug
    folder.mkdir(parents=True)
    manifest = {"title": title or slug.replace("-", " ").title(),
                "date": (when or today()).isoformat(),
                "summary": f"Summary of {slug}.", "draft": draft, **extra}
    (folder / "post.json").write_text(json.dumps(manifest), encoding="utf-8")
    (folder / "post.md").write_text(body, encoding="utf-8")
    return folder


@contextmanager
def content(build=None, books=None, prod=False):
    """
    Point the app at a temporary content folder for the length of a check.

    CONTENT_DIR moves with BLOG_DIR, because a post's body is rendered
    through render_content(), which reads relative to CONTENT_DIR. `prod`
    flips IS_PROD, which is what decides whether drafts show.
    """
    tmp = Path(tempfile.mkdtemp(prefix="ignite-public-"))
    saved = (appmod.CONTENT_DIR, appmod.BLOG_DIR, appmod.BOOKS_FILE, appmod.cfg.IS_PROD)
    try:
        (tmp / "blog").mkdir()
        if build:
            build(tmp)
        books_file = tmp / "books.json"
        books_file.write_text(json.dumps(books or []), encoding="utf-8")
        appmod.CONTENT_DIR, appmod.BLOG_DIR, appmod.BOOKS_FILE = tmp, tmp / "blog", books_file
        appmod.cfg.IS_PROD = prod
        appmod.refresh_catalog()
        yield tmp
    finally:
        appmod.CONTENT_DIR, appmod.BLOG_DIR, appmod.BOOKS_FILE, appmod.cfg.IS_PROD = saved
        appmod.refresh_catalog()
        shutil.rmtree(tmp, ignore_errors=True)


WORLD = {}


def build_world():
    signup(client(), "teacher", username="head", email="head@p.test",
           org_name="Public School", name="Head Teacher")
    code = db.org_by_id(db.user_by_username("head")["org_id"])["join_code"]
    signup(client(), "student", username="kid", email="kid@p.test",
           join_code=code, name="Kid")
    signup(client(), "parent", username="mum", email="mum@p.test",
           join_code=code, name="Mum")
    WORLD["code"] = code


# ── The way in ──────────────────────────────────────────────────────────────────

@check("a signed-out visitor at / gets the landing page, not the login form")
def t_landing_signed_out():
    res = client().get("/", follow_redirects=False)
    assert res.status_code == 200, f"/ answered {res.status_code} {res.headers.get('Location')}"
    html = res.get_data(as_text=True)
    assert "Kids learn" in html, "the landing page did not render"
    assert 'name="password"' not in html, "the landing page is the login form"


@check("Log in and Create account sit in the top bar of every public page")
def t_way_in_at_the_top():
    with content(lambda root: write_post(root, "hello")):
        for path in ("/", "/blog", "/blog/hello"):
            bar = top_bar(client().get(path).get_data(as_text=True))
            assert 'href="/login"' in bar and ">Log in<" in bar, f"{path}: no Log in in the top bar"
            assert 'href="/signup"' in bar and ">Create account<" in bar, \
                f"{path}: no Create account in the top bar"


@check("the landing page leads into the existing sign-up for each role")
def t_landing_links_into_signup():
    html = client().get("/").get_data(as_text=True)
    for role in ("parent", "teacher"):
        assert f'href="/signup?role={role}"' in html, f"no way in for a {role}"
    # And those links really land on the existing form, with that role's tab.
    page = client().get("/signup?role=parent").get_data(as_text=True)
    assert "join_code" in page, "the parent sign-up form is not where the link points"


@check("a signed-in visitor at / goes straight to where they work")
def t_signed_in_skips_landing():
    for username, target in (("kid", "/classroom"), ("head", "/grownup"), ("mum", "/grownup")):
        res = signed_in(username).get("/", follow_redirects=False)
        assert res.status_code == 302, f"{username} got {res.status_code} at /"
        assert res.headers["Location"].endswith(target), \
            f"{username} was sent to {res.headers['Location']}, expected {target}"


@check("a signed-in visitor on the blog gets a way back, not a sign-in button")
def t_signed_in_blog_header():
    bar = top_bar(signed_in("kid").get("/blog").get_data(as_text=True))
    assert "Go to your classroom" in bar, "no way back to the classroom"
    assert ">Log in<" not in bar and ">Create account<" not in bar, \
        "a signed-in visitor was offered the sign-in buttons"
    bar = top_bar(signed_in("head").get("/blog").get_data(as_text=True))
    assert "Go to your dashboard" in bar, "no way back to the dashboard"


# ── Caching ─────────────────────────────────────────────────────────────────────

@check("public pages are private to the browser and vary on the session")
def t_public_cache_headers():
    """
    One URL, two pages: "Log in" for a visitor, "Go to your classroom" for a
    student. `public` would let a shared cache hand one to the other — the
    same mistake /legal once made.
    """
    with content(lambda root: write_post(root, "hello")):
        for path in ("/", "/blog", "/blog/hello"):
            res = client().get(path)
            cache = res.headers.get("Cache-Control", "")
            assert cache.startswith("private"), f"{path}: Cache-Control {cache!r}"
            assert "cookie" in res.headers.get("Vary", "").lower(), \
                f"{path}: Vary {res.headers.get('Vary')!r}"


# ── Publishing ──────────────────────────────────────────────────────────────────

@check("posts are listed newest first, and the landing page shows the latest three")
def t_post_order():
    now = today()

    def build(root):
        for days, slug in ((9, "oldest"), (1, "newest"), (5, "middle"), (7, "older")):
            write_post(root, slug, when=now - timedelta(days=days))

    with content(build):
        html = client().get("/blog").get_data(as_text=True)
        order = [m for m in re.findall(r'href="/blog/([a-z-]+)"', html)]
        seen = list(dict.fromkeys(order))
        assert seen == ["newest", "middle", "older", "oldest"], seen

        landing = client().get("/").get_data(as_text=True)
        shown = list(dict.fromkeys(re.findall(r'href="/blog/([a-z-]+)"', landing)))
        assert shown == ["newest", "middle", "older"], f"landing showed {shown}"


@check("a draft shows on a laptop and is invisible in production")
def t_drafts():
    def build(root):
        write_post(root, "published")
        write_post(root, "unfinished", draft=True)

    with content(build, prod=False):
        assert "/blog/unfinished" in client().get("/blog").get_data(as_text=True), \
            "a draft is hidden outside production"
        assert client().get("/blog/unfinished").status_code == 200

    with content(build, prod=True):
        for path in ("/", "/blog", "/feed.xml", "/sitemap.xml"):
            assert "unfinished" not in client().get(path).get_data(as_text=True), \
                f"a draft leaked into {path} in production"
        assert client().get("/blog/unfinished").status_code == 404, \
            "a draft is reachable by URL in production"
        assert client().get("/blog/published").status_code == 200


@check("a post dated in the future waits for its date")
def t_scheduled():
    def build(root):
        write_post(root, "tomorrow", when=today() + timedelta(days=2))
        write_post(root, "today")

    with content(build):
        for path in ("/", "/blog", "/feed.xml", "/sitemap.xml"):
            assert "tomorrow" not in client().get(path).get_data(as_text=True), \
                f"a future post showed early on {path}"
        assert client().get("/blog/tomorrow").status_code == 404


@check("a broken post is left out, and the site stays up")
def t_broken_post():
    def build(root):
        write_post(root, "fine")
        bad = root / "blog" / "broken"
        bad.mkdir()
        (bad / "post.json").write_text("{ not json", encoding="utf-8")
        (bad / "post.md").write_text("words", encoding="utf-8")
        undated = write_post(root, "undated")
        (undated / "post.json").write_text(json.dumps({"title": "x", "summary": "y"}))

    with content(build) as root:
        assert client().get("/").status_code == 200, "one bad file took the landing page down"
        html = client().get("/blog").get_data(as_text=True)
        assert "/blog/fine" in html, "the good post went missing"
        assert "/blog/broken" not in html and "/blog/undated" not in html
        post, problems = blog.read_post(root / "blog" / "broken")
        assert post is None and problems, "a broken post was not reported"


@check("anything that is not a plain slug is a 404")
def t_slug_input():
    with content(lambda root: write_post(root, "real-post")):
        for path in ("/blog/nope", "/blog/Real-Post", "/blog/real.post",
                     "/blog/..%2F..%2Fapp.py", "/blog/%2e%2e", "/blog/real-post-"):
            assert client().get(path).status_code == 404, f"{path} did not 404"
    for good in ("a", "spark-lost-signal", "post-2026"):
        assert blog.valid_slug(good), good
    for bad in ("", "-a", "a-", "a--b", "A", "a.b", "a/b", "..", "a b", "x" * 81, None, 3):
        assert not blog.valid_slug(bad), f"{bad!r} passed as a slug"


@check("a post renders its Markdown, and its title is escaped")
def t_post_render():
    with content(lambda root: write_post(
            root, "markup", title="Fuses <script>alert(1)</script> & you",
            body="Intro.\n\n## Why fuses blow\n\n- one\n- two")):
        html = client().get("/blog/markup").get_data(as_text=True)
        assert "<h2>Why fuses blow</h2>" in html, "the Markdown was not rendered"
        assert "<li>one</li>" in html
        assert "<script>alert(1)</script>" not in html, "a title was rendered as HTML"
        assert "&lt;script&gt;" in html, "the title is missing or not escaped"


@check("the landing page copes with no posts and no books")
def t_landing_empty():
    with content():
        html = client().get("/").get_data(as_text=True)
        assert "News is on its way" in html, "no empty state for the news section"
        assert 'id="books"' not in html, "an empty books section was drawn"


# ── Books ───────────────────────────────────────────────────────────────────────

@check("a book with no link says coming soon; a link becomes a buy button")
def t_books():
    books = [
        {"id": "first-book", "title": "First Book", "blurb": "About a fuse."},
        {"id": "second-book", "title": "Second Book", "status": "available",
         "links": [{"label": "Buy on Amazon", "url": "https://example.com/buy"}]},
    ]
    with content(books=books):
        html = client().get("/").get_data(as_text=True)
        section = html[html.index('id="books"'):]
        first = section[section.index("First Book"):section.index("Second Book")]
        assert "Coming soon" in first, "a book with no link did not say coming soon"
        assert 'href="https://example.com/buy"' in section, "the buy link is missing"
        assert ">Buy on Amazon<" in section


@check("books.json refuses non-https links and 'available' with nowhere to buy")
def t_books_validation():
    tmp = Path(tempfile.mkdtemp(prefix="ignite-books-"))
    try:
        path = tmp / "books.json"
        path.write_text(json.dumps([
            {"id": "plain", "title": "Plain", "status": "available",
             "links": [{"label": "Buy", "url": "http://insecure.example/buy"}]},
            {"id": "plain", "title": "Duplicate"},
            {"id": "Bad Id", "title": "Bad"},
        ]))
        books, problems = blog.read_books(path)
        assert [b["id"] for b in books] == ["plain"], books
        assert books[0]["links"] == [], "an http:// buy link was accepted"
        assert books[0]["status"] == "coming-soon", "available with no links was kept"
        text = " ".join(problems)
        assert "https://" in text and "duplicate" in text and "available" in text, problems
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ── Feeds and search engines ────────────────────────────────────────────────────

@check("the Atom feed parses, and every link in it is absolute")
def t_feed():
    with content(lambda root: write_post(root, "hello", title="Hello & welcome")):
        res = client().get("/feed.xml")
        assert res.headers["Content-Type"].startswith("application/atom+xml"), res.headers["Content-Type"]
        root = ET.fromstring(res.get_data())
        assert root.tag == f"{ATOM}feed", root.tag
        entries = root.findall(f"{ATOM}entry")
        assert len(entries) == 1, f"{len(entries)} entries"
        assert entries[0].find(f"{ATOM}title").text == "Hello & welcome"
        for link in root.iter(f"{ATOM}link"):
            assert link.get("href", "").startswith(appmod.cfg.BASE_URL), \
                f"relative or foreign link in the feed: {link.get('href')}"


@check("the sitemap lists the public pages and the posts, absolutely")
def t_sitemap():
    with content(lambda root: write_post(root, "hello")):
        root = ET.fromstring(client().get("/sitemap.xml").get_data())
        locs = [u.find(f"{SITEMAP}loc").text for u in root.findall(f"{SITEMAP}url")]
        base = appmod.cfg.BASE_URL
        for path in ("/", "/blog", "/blog/hello", "/legal/terms"):
            assert f"{base}{path}" in locs, f"{path} missing from the sitemap"
        assert all(loc.startswith(base) for loc in locs), locs


@check("search engines are kept out of everything but production's public pages")
def t_robots():
    text = client().get("/robots.txt").get_data(as_text=True)
    assert "Disallow: /" in text and "Allow" not in text, \
        f"a non-production robots.txt allows crawling:\n{text}"
    saved = appmod.cfg.IS_PROD
    appmod.cfg.IS_PROD = True
    try:
        text = client().get("/robots.txt").get_data(as_text=True)
    finally:
        appmod.cfg.IS_PROD = saved
    for line in ("Allow: /$", "Allow: /blog", "Disallow: /", "Sitemap: "):
        assert line in text, f"production robots.txt is missing {line!r}:\n{text}"


# ── Privacy ─────────────────────────────────────────────────────────────────────

@check("public pages load nothing from another site")
def t_no_third_parties():
    """
    No web fonts, no analytics, no embeds. A link out (a book's buy button)
    is the reader's choice; a script or a font from another host is a
    request the reader never chose, and it tells that host who visited.
    """
    books = [{"id": "b", "title": "B", "status": "available",
              "links": [{"label": "Buy", "url": "https://shop.example/b"}]}]
    with content(lambda root: write_post(root, "hello", image="characters/spark"), books=books):
        for path in ("/", "/blog", "/blog/hello"):
            html = client().get(path).get_data(as_text=True)
            loads = re.findall(r'<(?:script|img|iframe|source)[^>]+src="([^"]+)"', html)
            loads += re.findall(r'<link[^>]+rel="stylesheet"[^>]+href="([^"]+)"', html)
            foreign = [u for u in loads if u.startswith(("http://", "https://", "//"))
                       and not u.startswith(appmod.cfg.BASE_URL)]
            assert not foreign, f"{path} loads from another site: {foreign}"


@check("a link preview and the canonical URL use the public address")
def t_link_preview():
    with content(lambda root: write_post(root, "hello", image="characters/spark")):
        html = client().get("/blog/hello").get_data(as_text=True)
        base = appmod.cfg.BASE_URL
        assert f'<link rel="canonical" href="{base}/blog/hello"' in html, "canonical URL wrong"
        image = re.search(r'property="og:image" content="([^"]+)"', html)
        assert image and image.group(1).startswith(base + "/static/art/characters/spark"), \
            f"preview image is {image and image.group(1)}"
        assert 'property="og:type" content="article"' in html


TESTS = [
    t_landing_signed_out, t_way_in_at_the_top, t_landing_links_into_signup,
    t_signed_in_skips_landing, t_signed_in_blog_header,
    t_public_cache_headers,
    t_post_order, t_drafts, t_scheduled, t_broken_post, t_slug_input, t_post_render,
    t_landing_empty,
    t_books, t_books_validation,
    t_feed, t_sitemap, t_robots,
    t_no_third_parties, t_link_preview,
]


def main() -> int:
    appmod.db.init_pool(appmod.cfg)
    reset_database()
    appmod.refresh_catalog()
    build_world()

    print(f"\n  {len(TESTS)} checks against {appmod.cfg.DATABASE_URL.rsplit('@', 1)[-1]}\n")
    for test in TESTS:
        test()

    print(f"\n  {len(PASSED)} passed, {len(FAILED)} failed\n")
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
