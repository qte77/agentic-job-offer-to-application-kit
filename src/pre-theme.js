// Anti-flash: apply a saved explicit theme before first paint (auto = no attr). Loaded as a
// synchronous (render-blocking) external script rather than inline so the page can ship a strict
// Content-Security-Policy without an inline-script allowance (#52). Keep it tiny and dependency-free.
(function () {
  try {
    var t = localStorage.getItem("qte77-theme");
    if (t === "light" || t === "dark")
      document.documentElement.setAttribute("data-theme", t);
  } catch (e) {}
})();
