(function () {
  "use strict";
  var reduce = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  // 1. Numbers count up once when results arrive (skipped for reduced motion)
  function countUp(el) {
    var raw = el.textContent.trim();
    var m = raw.match(/^([+-]?)(\d+(?:\.\d+)?)(.*)$/);
    if (!m) return;
    var sign = m[1], target = parseFloat(m[2]), suffix = m[3];
    var dec = (m[2].split(".")[1] || "").length;
    if (!isFinite(target) || target === 0) return;
    var start = performance.now(), dur = 650;
    function frame(now) {
      var p = Math.min((now - start) / dur, 1);
      var e = p === 1 ? 1 : 1 - Math.pow(2, -10 * p);
      el.textContent = p === 1 ? raw : sign + (target * e).toFixed(dec) + suffix;
      if (p < 1) requestAnimationFrame(frame);
    }
    requestAnimationFrame(frame);
  }
  if (!reduce) {
    document.querySelectorAll(".kpi .num, .stat .v").forEach(countUp);
  }

  // 2. Buttons show a spinner while they are disabled (a request is running)
  function syncLoading(btn) {
    var busy = btn.disabled && !btn.classList.contains("chip") && !btn.hasAttribute("data-no-spin");
    btn.classList.toggle("is-loading", busy);
  }
  if ("MutationObserver" in window) {
    new MutationObserver(function (list) {
      list.forEach(function (r) {
        if (r.target.tagName === "BUTTON") syncLoading(r.target);
      });
    }).observe(document.body, { attributes: true, attributeFilter: ["disabled"], subtree: true });
  }

  // 3. Normal form posts (like Analyze): show the spinner and block double clicks
  document.querySelectorAll("form").forEach(function (f) {
    f.addEventListener("submit", function (e) {
      if (e.defaultPrevented) return;
      var b = f.querySelector('button[type="submit"], button:not([type])');
      if (b) {
        b.classList.add("is-loading");
        setTimeout(function () { b.disabled = true; }, 0);
      }
    });
  });
  window.addEventListener("pageshow", function (e) {
    if (e.persisted) {
      document.querySelectorAll("button.is-loading").forEach(function (b) {
        b.disabled = false;
        b.classList.remove("is-loading");
      });
    }
  });

  // 4. Chat: the waiting message pulses until the answer replaces it
  var log = document.getElementById("chatLog");
  function markThinking() {
    log.querySelectorAll(".msg.bot, .msg.assistant").forEach(function (el) {
      el.classList.toggle("thinking", /^Thinking(\u2026|\.\.\.)?$/.test(el.textContent.trim()));
    });
  }
  if (log && "MutationObserver" in window) {
    new MutationObserver(markThinking).observe(log, { childList: true, subtree: true, characterData: true });
  }

  // 5. Back-to-top button on long pages
  var up = document.createElement("button");
  up.type = "button";
  up.className = "to-top";
  up.setAttribute("aria-label", "Back to top");
  up.innerHTML = '<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M6 15l6-6 6 6"/></svg>';
  document.body.appendChild(up);
  var ticking = false;
  window.addEventListener("scroll", function () {
    if (ticking) return;
    ticking = true;
    requestAnimationFrame(function () {
      up.classList.toggle("show", window.scrollY > 600);
      ticking = false;
    });
  }, { passive: true });
  up.addEventListener("click", function () {
    window.scrollTo({ top: 0, behavior: reduce ? "auto" : "smooth" });
  });
})();
// end motion.js
