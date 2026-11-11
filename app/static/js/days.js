// Page Pronos, affichage seulement : la carte d'avancement du jour (« 2 sur 3 joués » et sa barre)
// et le point orange du calendrier sont mis à jour après un enregistrement.
(function () {
  document.addEventListener("prediction-saved", function (event) {
    var day = event.target.closest("[data-day]");
    var label = day && day.querySelector("[data-day-done]");
    if (!label) return;
    var total = parseInt(label.dataset.total, 10);
    var done = day.querySelectorAll(".match-card[data-open][data-predicted]").length;
    label.textContent = label.dataset.fmt.replace("{done}", done).replace("{total}", total);
    var bar = day.querySelector("[data-day-bar]");
    if (bar) bar.style.width = Math.round(100 * done / total) + "%";
    var link = document.querySelector('[data-filter-days] [data-day-key="' + day.dataset.dayKey + '"]');
    if (link && done === total) link.querySelector(".pr-dot").classList.add("off");
  });
})();
