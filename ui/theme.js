// EyeRest theme toggle — auto/light/dark cycle, persisted to localStorage and
// applied as data-theme on <html>. Mirrors qte77/qte77.github.io/assets/theme.js.
// Dispatches a "themechange" event so the dashboard can rebuild Chart.js, which
// caches the CSS-variable colors at construction time. Keyboard: native <button>;
// the current state is announced via a dynamic aria-label.
(function () {
  var root = document.documentElement;
  var btn = document.getElementById("theme-toggle");
  if (!btn) return;

  var ORDER = ["auto", "light", "dark"];
  var WORD = { auto: "Auto", light: "Light", dark: "Dark" };
  var GLYPH = { auto: "◐", light: "○", dark: "●" };

  function current() {
    try {
      var t = localStorage.getItem("theme");
      return t === "light" || t === "dark" ? t : "auto";
    } catch (e) {
      return "auto";
    }
  }

  function apply(mode) {
    if (mode === "light" || mode === "dark") {
      root.setAttribute("data-theme", mode);
    } else {
      root.removeAttribute("data-theme");
    }
    try {
      if (mode === "auto") localStorage.removeItem("theme");
      else localStorage.setItem("theme", mode);
    } catch (e) {}
    btn.textContent = GLYPH[mode] + " " + WORD[mode];
    btn.setAttribute("aria-label", "Color theme: " + WORD[mode] + " (click to change)");
    btn.title = "Color theme: " + WORD[mode];
    document.dispatchEvent(new CustomEvent("themechange", { detail: { mode: mode } }));
  }

  apply(current());

  btn.addEventListener("click", function () {
    var next = ORDER[(ORDER.indexOf(current()) + 1) % ORDER.length];
    apply(next);
  });
})();
