// Filtres de la page Pronos (compétition × statut), sans recharger la page :
// - les matchs sont tous dans la page, un filtre ne fait que les masquer (les scores saisis restent) ;
// - les compteurs des compétitions suivent le statut choisi ;
// - le choix est gardé dans l'adresse (?comp=l1&status=todo), même tri que app/services/match_filters.py ;
// - « N matchs sans prono » suit la saisie.
(function () {
  var comps = document.querySelector("[data-filter-comps]");
  var statuses = document.querySelector("[data-filter-status]");
  if (!comps || !statuses) return;
  var cards = Array.prototype.slice.call(document.querySelectorAll(".match-card[data-comp]"));
  var days = Array.prototype.slice.call(document.querySelectorAll("[data-day]"));
  var empty = document.querySelector("[data-empty]");
  var missing = document.querySelector("[data-missing]");
  var params = new URLSearchParams(window.location.search);
  var current = {
    comp: comps.querySelector(".active").dataset.compKey,
    status: statuses.querySelector(".active").dataset.statusKey
  };

  function has(card, name) { return name in card.dataset; }

  function matchesStatus(card, status) {
    var predicted = has(card, "predicted");
    if (status === "todo") return has(card, "open") && !predicted;
    if (status === "mine") return predicted && !has(card, "ended");
    return true;
  }

  function plural(element, count) {
    var fmt = count === 1 ? element.dataset.fmtOne : element.dataset.fmt;
    return fmt.replace("{count}", count);
  }

  function setActive(container, attribute, key) {
    Array.prototype.forEach.call(container.querySelectorAll("a"), function (link) {
      var active = link.dataset[attribute] === key;
      link.classList.toggle("active", active);
      if (active) link.setAttribute("aria-current", "true");
      else link.removeAttribute("aria-current");
      link.href = "?comp=" + (attribute === "compKey" ? link.dataset.compKey : current.comp) +
        "&status=" + (attribute === "statusKey" ? link.dataset.statusKey : current.status);
    });
  }

  function updateCounts() {
    var counts = { all: 0 };
    cards.forEach(function (card) {
      if (!matchesStatus(card, current.status)) return;
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
      var visible = matchesStatus(card, current.status) &&
        (current.comp === "all" || card.dataset.comp === current.comp);
      card.hidden = !visible;
      if (visible) shown += 1;
    });
    days.forEach(function (day) {
      var count = day.querySelectorAll(".match-card:not([hidden])").length;
      day.hidden = count === 0;
      var label = day.querySelector("[data-day-count]");
      label.textContent = plural(label, count);
    });
    empty.hidden = shown > 0;
    setActive(comps, "compKey", current.comp);
    setActive(statuses, "statusKey", current.status);
    updateCounts();
    params.set("comp", current.comp);
    params.set("status", current.status);
    history.replaceState(null, "", "?" + params.toString() + window.location.hash);
  }

  function scrollActiveIntoView() {
    var active = comps.querySelector(".active");
    var left = active.offsetLeft - (comps.clientWidth - active.offsetWidth) / 2;
    comps.scrollTo({ left: Math.max(0, left), behavior: "smooth" });
  }

  comps.addEventListener("click", function (event) {
    var link = event.target.closest("[data-comp-key]");
    if (!link) return;
    event.preventDefault();
    current.comp = link.dataset.compKey;
    apply();
    scrollActiveIntoView();
  });

  statuses.addEventListener("click", function (event) {
    var link = event.target.closest("[data-status-key]");
    if (!link) return;
    event.preventDefault();
    current.status = link.dataset.statusKey;
    apply();
  });

  // « N matchs sans prono » : matchs ouverts dont les deux cases ne sont pas remplies
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

  // Sans paramètre dans l'adresse : on reprend le dernier choix (localStorage)
  try {
    if (!params.has("comp") && !params.has("status")) {
      var saved = JSON.parse(localStorage.getItem("pronos-filters") || "null");
      if (saved && comps.querySelector('[data-comp-key="' + saved.comp + '"]')) current.comp = saved.comp;
      if (saved && statuses.querySelector('[data-status-key="' + saved.status + '"]')) current.status = saved.status;
    }
  } catch (e) { /* stockage indisponible : on garde les valeurs par défaut */ }

  // Lien vers un match précis (#m12, depuis l'accueil) masqué par les filtres : on montre tout
  var target = window.location.hash && document.getElementById(window.location.hash.slice(1));
  if (target && cards.indexOf(target) >= 0 && !matchesStatus(target, current.status)) {
    current = { comp: "all", status: "all" };
  }

  var remember = function () {
    try { localStorage.setItem("pronos-filters", JSON.stringify(current)); } catch (e) { /* rien */ }
  };
  comps.addEventListener("click", remember);
  statuses.addEventListener("click", remember);

  apply();
  updateMissing();
  var active = comps.querySelector(".active");
  comps.scrollLeft = Math.max(0, active.offsetLeft - (comps.clientWidth - active.offsetWidth) / 2);
  if (target) target.scrollIntoView({ block: "center" });
})();
