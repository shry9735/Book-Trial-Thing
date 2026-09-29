/* ==========================================================================
   Ignite Lesson Kit — the only bridge between a lesson and the host.

   Every lesson runs in its own iframe, so it has its own JavaScript
   context. Nothing here is shared state: each lesson gets a fresh copy of
   this file with its own `Ignite` object. Define whatever globals you
   like — no other lesson can see them, and none of theirs can reach you.

   Include it after the stylesheet:

       <link rel="stylesheet" href="/kit/lesson-kit.css">
       <script src="/kit/lesson-kit.js"></script>

   Then:

       Ignite.ready();                 // tell the host you loaded
       Ignite.progress(40);            // optional, 0-100
       Ignite.complete(90);            // done, with an optional score
       Ignite.art('characters/spark'); // shared art URL
       Ignite.award('trinket-led');    // hand out something you declared
       Ignite.save({level: 3});        // your own state, kept per student
       Ignite.load(function (s) {});   // ... and read back next visit

   Ignite.complete() hands control back to the host, which runs the quiz
   and records the score. A lesson never scores itself.

   ── Shared art ────────────────────────────────────────────────────────
   Ignite.art() is how every sub-app reaches the same characters. Replace
   one file and every lesson using it updates at once, including in
   browsers that already cached the old one — the URL carries a content
   hash. Ask /art/manifest.json what already exists before drawing a
   second Spark.

   ── Awards ────────────────────────────────────────────────────────────
   A sub-app can only award items its own lesson.json lists in "awards".
   The server checks that list, not this file: everything here runs in the
   student's browser, so nothing it claims is taken on trust. Declaring an
   award is a content decision; granting it is the platform's.

   ── State ─────────────────────────────────────────────────────────────
   Ignite.save() takes any JSON object, up to 64KB, kept per student per
   lesson. The platform never looks inside it. It is a save file, not a
   database — if you need more than that, this seam is the wrong shape for
   what you are building and it is worth saying so.

   ── Versioning ────────────────────────────────────────────────────────
   Ignite.VERSION is the major version of this contract. Declare the one
   you built against in lesson.json ("bridge": 1) and the server complains
   at boot if it is older than you need, instead of your calls silently
   doing nothing.
   ========================================================================== */

(function (global) {
  'use strict';

  /* Which lesson this frame is. Read from the path the host loaded us
     from — /lessons/<id>/index.html — so a sub-app never has to be told
     its own name and cannot get it wrong. */
  var LESSON_ID = (function () {
    var parts = global.location.pathname.split('/').filter(Boolean);
    var at = parts.indexOf('lessons');
    return at >= 0 && parts[at + 1] ? decodeURIComponent(parts[at + 1]) : '';
  })();

  /* Awards and state go over fetch rather than postMessage: they need an
     answer back, and the host would only be relaying them to the same
     endpoints anyway. Same origin, so the session cookie rides along; the
     server re-checks the lesson is one this student may be working on. */
  function request(path, payload, done) {
    payload.lesson_id = LESSON_ID;
    global.fetch(path, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    }).then(function (r) { return r.json().catch(function () { return null; }); })
      .then(function (res) {
        if (res && res.error && global.console) {
          console.warn('[Ignite] ' + path + ': ' + res.error);
        }
        if (done) done(res);
      })
      .catch(function (err) {
        if (global.console) console.warn('[Ignite] ' + path + ' failed', err);
        if (done) done(null);
      });
  }

  function requestGet(path, done) {
    global.fetch(path)
      .then(function (r) { return r.json().catch(function () { return null; }); })
      .then(function (res) { if (done) done(res); })
      .catch(function () { if (done) done(null); });
  }

  function post(type, payload) {
    try {
      global.parent.postMessage(Object.assign({ type: type }, payload || {}), '*');
    } catch (err) {
      /* Standalone preview outside the host — harmless. */
      if (global.console) console.info('[Ignite] no host to receive "' + type + '"');
    }
  }

  var Ignite = {

    /** Major version of this contract. Declare it as "bridge" in lesson.json. */
    VERSION: 1,

    /** Which lesson this is, taken from the URL the host loaded. */
    lessonId: LESSON_ID,

    /* ── Host messages ──────────────────────────────────────────────── */

    /** Announce the lesson has loaded. Hides the host's loading state. */
    ready: function () {
      post('lesson:ready');
      return this;
    },

    /** Report partial progress, 0-100. Optional. */
    progress: function (percent) {
      post('lesson:progress', { score: clampPercent(percent) });
      return this;
    },

    /**
     * Finish the lesson. The host takes over: it runs the quiz, records
     * the score and grants any trinket. Safe to call more than once.
     */
    complete: function (score) {
      post('lesson:complete', { score: score == null ? null : clampPercent(score) });
      return this;
    },

    /** Show a toast in the host's frame, outside the lesson. */
    toast: function (message) {
      post('lesson:toast', { message: String(message) });
      return this;
    },

    /**
     * Hand the student something for the satchel.
     *
     *     Ignite.award('trinket-led');
     *     Ignite.award(['badge-loop', 'trinket-led'], function (granted) {});
     *
     * Only items this lesson declares in its own "awards" list are
     * granted; the server decides, and refuses anything else. Awarding the
     * same item twice is harmless — the second call grants nothing and the
     * callback gets an empty list, so it is safe to call on every win.
     */
    award: function (items, done) {
      request('/api/award', { items: [].concat(items) }, function (res) {
        if (done) done((res && res.granted) || []);
      });
      return this;
    },

    /* ── Your own state ─────────────────────────────────────────────── */

    /**
     * Keep something between visits, per student. Any JSON object, 64KB.
     *
     *     Ignite.save({ level: 3, wires: [[1,2],[4,5]] });
     *
     * Replaces whatever was there — the sub-app owns the shape, so the
     * platform will not try to merge two versions of a format it does not
     * understand.
     */
    save: function (state, done) {
      request('/api/state', { state: state || {} }, function (res) {
        if (done) done(!!(res && res.ok));
      });
      return this;
    },

    /** Read back what save() last stored. Gets {} the first time. */
    load: function (done) {
      requestGet('/api/state/' + encodeURIComponent(LESSON_ID), function (res) {
        if (done) done((res && res.state) || {});
      });
      return this;
    },

    /* ── Shared assets ──────────────────────────────────────────────── */

    /**
     * URL for a shared graphic, extension resolved by the server.
     *
     *     <img src="" id="hero">
     *     hero.src = Ignite.art('characters/spark');
     *
     * Never hardcode /static/art/characters/spark.png in a lesson —
     * going through here means re-exporting the file as .webp updates
     * every lesson at once, and a missing file shows a labelled
     * placeholder instead of a broken image.
     */
    art: function (name) {
      return '/art/' + String(name).replace(/^\/+/, '');
    },

    /** Preload shared art so a lesson doesn't pop in mid-animation. */
    preload: function (names, done) {
      var list    = [].concat(names);
      var left    = list.length;
      var results = {};
      if (!left) { if (done) done(results); return; }

      list.forEach(function (name) {
        var img = new Image();
        img.onload = img.onerror = function () {
          results[name] = img;
          if (--left === 0 && done) done(results);
        };
        img.src = Ignite.art(name);
      });
      return this;
    },

    /* ── Small helpers ──────────────────────────────────────────────── */

    /** Shorthand for querySelector, scoped to this lesson's document. */
    $: function (selector, root) {
      return (root || document).querySelector(selector);
    },

    $$: function (selector, root) {
      return Array.prototype.slice.call((root || document).querySelectorAll(selector));
    },

    /** Run a callback once the DOM is ready. */
    onReady: function (fn) {
      if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', fn);
      } else {
        fn();
      }
      return this;
    }
  };

  function clampPercent(value) {
    var n = Number(value);
    if (isNaN(n)) return 0;
    return Math.max(0, Math.min(100, Math.round(n)));
  }

  global.Ignite = Ignite;

  /* Surface lesson errors in the host console with the lesson named, so a
     broken lesson is obvious and still cannot affect any other one. */
  global.addEventListener('error', function (e) {
    post('lesson:error', { message: e.message, source: e.filename, line: e.lineno });
  });

})(window);
