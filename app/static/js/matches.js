// Filtres de la page Pronos (jour × compétition × statut), sans recharger la page :
// - les matchs de tous les jours sont dans la page, un filtre ne fait que les masquer
//   (les scores saisis restent, et « Valider » enregistre tout ce qui a été saisi) ;
// - seul le jour choisi dans le calendrier est affiché ;
// - les compteurs des compétitions suivent le jour et le statut choisis ;
// - le choix est gardé dans l'adresse (?day=2026-11-12&comp=l1&status=todo),
//   même tri que app/services/match_filters.py ;
// - « N pronos à faire » suit la saisie (tous les jours).
(function () {
  var daysNav = document.querySelector("[data-filter-days]");
  var comps = document.querySelector("[data-filter-comps]");
  var statuses = document.querySelector("[data-filter-status]");
  if (!daysNav || !comps || !statuses) return;
  var cards = Array.prototype.slice.call(document.querySelectorAll(".match-card[data-comp]"));
  var days = Array.prototype.slice.call(document.querySelectorAll("[data-day]"));
  var empty = document.querySelector("[data-empty]");
  var missing = document.querySelector("[data-missing]");
  var params = new URLSearchParams(window.location.search);
  var current = {
    day: daysNav.querySelector(".active").dataset.dayKey,
    comp: comps.querySelector(".active").dataset.compKey,
    status: statuses.querySelector(".active").dataset.statusKey
  };

  function has(card, name) { return name in card.dataset; }

  function dayOf(card) { return card.closest("[data-day]").dataset.dayKey; }

  function matchesStatus(card, status) {
    var predicted = has(card, "predicted");
    if (status === "todo") return has(card, "open") && !predicted;
    if (status === "mine") return predicted && !has(card, "ended");
    return true;
  }

  function plural(element, count) {
    var fmt = count === 0 && element.dataset.fmtZero ? element.dataset.fmtZero
      : count === 1 ? element.dataset.fmtOne : element.dataset.fmt;
    return fmt.replace("{count}", count);
  }

  function address(choice) {
    return "?day=" + choice.day + "&comp=" + choice.comp + "&status=" + choice.status;
  }

  // Lien actif de chaque filtre, et adresses des liens (utiles sans JavaScript ou en nouvel onglet)
  function setActive(container, attribute, name) {
    Array.prototype.forEach.call(container.querySelectorAll("a"), function (link) {
      var active = link.dataset[attribute] === current[name];
      link.classList.toggle("active", active);
      if (active) link.setAttribute("aria-current", "true");
      else link.removeAttribute("aria-current");
      var choice = { day: current.day, comp: current.comp, status: current.status };
      choice[name] = link.dataset[attribute];
      link.href = address(choice);
    });
  }

  function updateCounts() {
    var counts = { all: 0 };
    cards.forEach(function (card) {
      if (dayOf(card) !== current.day || !matchesStatus(card, current.status)) return;
      counts[card.dataset.comp] = (counts[card.dataset.comp] || 0) + 1;
      counts.all += 1;
    });
    Array.prototype.forEach.call(comps.querySelectorAll("[data-comp-key]"), function (link) {
      link.querySelector("[data-count]").textContent = counts[link.dataset.compKey] || 0;
    });
  }

  function apply() {
    var shown = 0;
    cards.forEach(function (card) {
      var visible = dayOf(card) === current.day && matchesStatus(card, current.status) &&
        (current.comp === "all" || card.dataset.comp === current.comp);
      card.hidden = !visible;
      if (visible) shown += 1;
    });
    var dayIsEmpty = true;
    days.forEach(function (day) {
      var selected = day.dataset.dayKey === current.day;
      day.hidden = !selected;
      if (selected) dayIsEmpty = day.dataset.total === "0";
      var label = day.querySelector("[data-day-count]");
      label.textContent = plural(label, day.querySelectorAll(".match-card:not([hidden])").length);
    });
    empty.hidden = shown > 0;
    empty.querySelector("[data-empty-day]").hidden = !dayIsEmpty;
    empty.querySelector("[data-empty-filters]").hidden = dayIsEmpty;
    setActive(daysNav, "dayKey", "day");
    setActive(comps, "compKey", "comp");
    setActive(statuses, "statusKey", "status");
    updateCounts();
    params.set("day", current.day);
    params.set("comp", current.comp);
    params.set("status", current.status);
    history.replaceState(null, "", "?" + params.toString() + window.location.hash);
  }

  // Rangée qui défile : l'élément actif est ramené au centre
  function centerActive(container, smooth) {
    var active = container.querySelector(".active");
    if (!active) return;
    var left = Math.max(0, active.offsetLeft - (container.clientWidth - active.offsetWidth) / 2);
    if (smooth) container.scrollTo({ left: left, behavior: "smooth" });
    else container.scrollLeft = left;
  }

  function onPick(container, attribute, name) {
    container.addEventListener("click", function (event) {
      var link = event.target.closest("[data-" + attribute.replace(/[A-Z]/g, "-$&").toLowerCase() + "]");
      if (!link) return;
      event.preventDefault();
      current[name] = link.dataset[attribute];
      apply();
      centerActive(container, true);
    });
  }

  onPick(daysNav, "dayKey", "day");
  onPick(comps, "compKey", "comp");
  onPick(statuses, "statusKey", "status");

  // « N pronos à faire » : matchs ouverts dont les deux cases ne sont pas remplies
  function updateMissing() {
    if (!missing) return;
    var count = cards.filter(function (card) {
      if (!has(card, "matchId")) return false;
      var inputs = card.querySelectorAll("[data-score]");
      return inputs[0].value === "" || inputs[1].value === "";
    }).length;
    missing.textContent = count === 0 ? missing.dataset.fmtNone : plural(missing, count);
  }

  document.addEventListener("input", updateMissing);
  // Un prono enregistré change de statut : les compteurs suivent, la ligne reste à sa place
  document.addEventListener("prediction-saved", updateCounts);

  // Sans paramètre dans l'adresse : on reprend la dernière compétition et le dernier statut
  // (le jour, lui, repart d'aujourd'hui)
  try {
    if (!params.has("comp") && !params.has("status")) {
      var saved = JSON.parse(localStorage.getItem("pronos-filters") || "null");
      if (saved && comps.querySelector('[data-comp-key="' + saved.comp + '"]')) current.comp = saved.comp;
      if (saved && statuses.querySelector('[data-status-key="' + saved.status + '"]')) current.status = saved.status;
    }
  } catch (e) { /* stockage indisponible : on garde les valeurs par défaut */ }

  // Lien vers un match précis (#m12, depuis l'accueil) : on ouvre son jour, et on le montre
  // même s'il est masqué par les filtres
  var target = window.location.hash && document.getElementById(window.location.hash.slice(1));
  if (target && cards.indexOf(target) >= 0) {
    current.day = dayOf(target);
    var hidden = !matchesStatus(target, current.status) ||
      (current.comp !== "all" && target.dataset.comp !== current.comp);
    if (hidden) { current.comp = "all"; current.status = "all"; }
  }

  var remember = function () {
    try {
      localStorage.setItem("pronos-filters", JSON.stringify({ comp: current.comp, status: current.status }));
    } catch (e) { /* rien */ }
  };
  comps.addEventListener("click", remember);
  statuses.addEventListener("click", remember);

  apply();
  updateMissing();
  centerActive(daysNav, false);
  centerActive(comps, false);
  if (target) target.scrollIntoView({ block: "center" });
})();
