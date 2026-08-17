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

   Ignite.complete() hands control back to the host, which runs the quiz
   and awards XP and trinkets. A lesson never scores itself.
   ========================================================================== */

(function (global) {
  'use strict';

  function post(type, payload) {
    try {
      global.parent.postMessage(Object.assign({ type: type }, payload || {}), '*');
    } catch (err) {
      /* Standalone preview outside the host — harmless. */
      if (global.console) console.info('[Ignite] no host to receive "' + type + '"');
    }
  }

  var Ignite = {

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
