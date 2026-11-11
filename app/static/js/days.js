// Page Pronos, affichage seulement : la carte d'avancement du jour (« 2 sur 3 joués » et sa barre)
// est mise à jour après un enregistrement. Le rond du calendrier, lui, suit au rechargement.
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
  });
})();
