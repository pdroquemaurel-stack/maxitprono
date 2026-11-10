// Comptes à rebours jusqu'à la clôture des pronos, mis à jour chaque minute.
// Élément : data-countdown="<date de clôture ISO>", formats dans data-fmt-days/hours/minutes.
(function () {
  var items = document.querySelectorAll("[data-countdown]");
  if (!items.length) return;

  function text(item) {
    var minutes = Math.max(1, Math.floor((new Date(item.dataset.countdown) - Date.now()) / 60000));
    var days = Math.floor(minutes / 1440), hours = Math.floor(minutes / 60) % 24, mins = minutes % 60;
    if (days) return item.dataset.fmtDays.replace("{days}", days).replace("{hours}", hours);
    if (hours) return item.dataset.fmtHours.replace("{hours}", hours).replace("{minutes}", (mins < 10 ? "0" : "") + mins);
    return item.dataset.fmtMinutes.replace("{minutes}", mins);
  }

  function refresh() {
    Array.prototype.forEach.call(items, function (item) { item.textContent = text(item); });
  }
  setInterval(refresh, 60000);
})();
