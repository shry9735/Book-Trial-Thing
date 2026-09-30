"""
Content the test suites need that the shipped catalog no longer has.

No shipped lesson waits on a grown-up to hand it out any more — the demo
wants every story open — but the assignment gate is still a feature, and
it still needs something to gate. This puts the old requirements back on
The Day of the Science Fair, for the tests only.

Patched into _build_lessons rather than onto the loaded catalog, so it
survives the refresh_catalog() calls the suites make between fixtures.
"""

GATED_LESSON = "story-science-fair"
GATED_REQUIRES = {
    "tracks": ["basic-electricity"],
    "lessons": ["code-02-debug"],
    "assignment": True,
}


def gate_for_tests(appmod) -> None:
    """Make GATED_LESSON assignment-only, with two prerequisites."""
    if getattr(appmod._build_lessons, "_gated", False):
        return
    real = appmod._build_lessons

    def build():
        lessons = real()
        for lesson in lessons:
            if lesson["id"] == GATED_LESSON:
                lesson["requires"] = dict(GATED_REQUIRES)
        return lessons

    build._gated = True
    appmod._build_lessons = build
