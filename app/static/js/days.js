// Page Pronos, affichage seulement :
// - bande des jours : le jour touché est souligné (le défilement se fait par l'ancre #d2026-11-20),
//   et le jour affiché à l'écran suit le défilement ;
// - carte d'avancement de chaque jour (« 2 sur 3 joués » et sa barre) mise à jour après un enregistrement.
(function () {
  var strip = document.querySelector("[data-day-strip]");
  var links = strip ? Array.prototype.slice.call(strip.querySelectorAll("[data-day-link]")) : [];

  function select(id) {
    links.forEach(function (link) {
      var active = link.hash === "#" + id;
      link.classList.toggle("active", active);
      if (active) link.setAttribute("aria-current", "true");
      else link.removeAttribute("aria-current");
    });
  }

  if (strip) {
    strip.addEventListener("click", function (event) {
      var link = event.target.closest("[data-day-link]");
      if (link) select(link.hash.slice(1));
    });
  }

  if (links.length && "IntersectionObserver" in window) {
    var observer = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) { if (entry.isIntersecting) select(entry.target.id); });
    }, { rootMargin: "-20% 0px -70% 0px" });
    links.forEach(function (link) {
      var day = document.getElementById(link.hash.slice(1));
      if (day) observer.observe(day);
    });
  }

  document.addEventListener("prediction-saved", function (event) {
    var day = event.target.closest("[data-day]");
    var label = day && day.querySelector("[data-day-done]");
    if (!label) return;
    var total = parseInt(label.dataset.total, 10);
    var done = day.querySelectorAll(".match-card[data-open][data-predicted]").length;
    label.textContent = label.dataset.fmt.replace("{done}", done).replace("{total}", total);
    var bar = day.querySelector("[data-day-bar]");
    if (bar) bar.style.width = Math.round(100 * done / total) + "%";
    var dot = links.filter(function (link) { return link.hash === "#" + day.id; })[0];
    if (dot && done === total) dot.querySelector(".pr-dot").classList.add("off");
  });
})();
