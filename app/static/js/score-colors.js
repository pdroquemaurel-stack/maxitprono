// Colore les deux cases de score d'un match pendant la saisie :
// gagnant en vert, perdant en rouge, les deux en bleu si nul.
// Même règle que app/services/score_colors.py (côté serveur).
(function () {
  var COLORS = ["win", "lose", "draw"];

  function scoreClasses(home, away) {
    if (home === null || away === null) return ["", ""];
    if (home > away) return ["win", "lose"];
    if (home < away) return ["lose", "win"];
    return ["draw", "draw"];
  }

  function readScore(input) {
    var value = input.value.trim();
    return /^[0-9]{1,2}$/.test(value) ? parseInt(value, 10) : null;
  }

  function paint(input, color) {
    COLORS.forEach(function (name) { input.classList.remove(name); });
    if (color) input.classList.add(color);
  }

  function refresh(card) {
    var home = card.querySelector('[data-score="home"]');
    var away = card.querySelector('[data-score="away"]');
    if (!home || !away) return;
    var classes = scoreClasses(readScore(home), readScore(away));
    paint(home, classes[0]);
    paint(away, classes[1]);
  }

  var cards = document.querySelectorAll(".match-card");
  Array.prototype.forEach.call(cards, function (card) {
    refresh(card);
    card.addEventListener("input", function () { refresh(card); });
  });
})();
