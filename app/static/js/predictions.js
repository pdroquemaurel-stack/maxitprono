// Saisie des pronostics (page Pronos et accueil) :
// - une case = un chiffre (0 à 9) ; après le score domicile on passe à l'extérieur,
//   après l'extérieur on passe au match suivant visible ;
// - rien ne part avant le bouton « Valider », qui envoie en une fois tous les matchs modifiés
//   (y compris ceux masqués par un filtre), puis devient « Enregistré » ;
// - un match fermé entre-temps est refusé par le serveur : le message s'affiche sur sa ligne ;
// - quitter la page avec des pronos remplis mais pas envoyés demande confirmation.
(function () {
  var form = document.querySelector(".predictions-form");
  if (!form) return;
  var messages = form.dataset;
  var submit = form.querySelector("[data-save-all]");
  var cards = Array.prototype.slice.call(form.querySelectorAll("[data-match-id]"));

  function digitOf(input) {
    var value = input.value.trim();
    return /^[0-9]$/.test(value) ? value : null;
  }

  function isFilled(card) {
    return digitOf(card.querySelector('[data-score="home"]')) !== null &&
      digitOf(card.querySelector('[data-score="away"]')) !== null;
  }

  function isVisible(element) {
    return element.offsetParent !== null; // faux si la carte ou son jour est masqué
  }

  function moveFocus(input, card) {
    var target = null;
    if (input.dataset.score === "home") {
      target = card.querySelector('[data-score="away"]');
    } else {
      var next = cards.slice(cards.indexOf(card) + 1).filter(isVisible)[0];
      if (next) target = next.querySelector('[data-score="home"]');
    }
    if (target) target.focus();
    else input.blur(); // dernier match : on ferme le clavier
  }

  // --- Affichage sur la ligne du match ---

  function showSaved(card) {
    var pill = card.querySelector("[data-state-pill]");
    if (pill) {
      pill.className = "mc-pill saved";
      pill.textContent = messages.msgSaved;
    }
  }

  function showError(card, text) {
    var error = card.querySelector("[data-save-error]");
    error.textContent = text;
    error.hidden = !text;
    card.classList.toggle("has-error", !!text);
  }

  function decrementTodo() {
    var badge = document.querySelector("[data-todo-count]");
    if (!badge) return;
    var count = parseInt(badge.dataset.todoCount, 10) - 1;
    badge.dataset.todoCount = count;
    if (count > 0) badge.textContent = messages.msgTodo.replace("{count}", count);
    else badge.hidden = true;
  }

  // --- Envoi d'un match : promesse vraie si enregistré ---

  function save(card) {
    var home = digitOf(card.querySelector('[data-score="home"]'));
    var away = digitOf(card.querySelector('[data-score="away"]'));
    card._failed = false;
    return fetch("/matches/" + card.dataset.matchId + "/prediction", {
      method: "POST",
      credentials: "same-origin",
      headers: { Accept: "application/json" },
      body: new URLSearchParams({ home: home, away: away })
    }).then(function (response) {
      if (response.status === 401) { // session expirée : page de connexion, retour ici ensuite
        card._dirty = false;
        window.location.href = "/login?next=" + encodeURIComponent(location.pathname + location.search);
        return null;
      }
      if (response.redirected) {
        card._dirty = false;
        window.location.href = response.url;
        return null;
      }
      return response.json();
    }).then(function (data) {
      if (!data) return false;
      card._dirty = false; // enregistré, ou refusé pour de bon (match fermé entre-temps)
      if (data.saved) {
        showSaved(card);
        showError(card, "");
        if (!("predicted" in card.dataset)) {
          card.dataset.predicted = "";
          decrementTodo();
        }
        card.dispatchEvent(new CustomEvent("prediction-saved", { bubbles: true }));
        return true;
      }
      showError(card, data.error);
      return false;
    }).catch(function () {
      card._failed = true; // reste à envoyer : renvoyé au retour du réseau
      showError(card, messages.msgOffline);
      return false;
    });
  }

  function pendingCards() {
    return cards.filter(function (card) { return card._dirty && isFilled(card); });
  }

  // --- Bouton « Valider » ---

  function setSubmit(state) { // "idle", "saving" ou "done"
    if (!submit) return;
    submit.classList.toggle("saving", state === "saving");
    submit.classList.toggle("done", state === "done");
    submit.disabled = state === "saving";
    submit.setAttribute("aria-busy", state === "saving" ? "true" : "false");
    submit.textContent = state === "done" ? submit.dataset.doneLabel
      : state === "saving" ? messages.msgSaving : submit.dataset.label;
  }

  function saveAll() {
    var sending = pendingCards().map(save);
    if (!sending.length) {
      setSubmit("done");
      return;
    }
    setSubmit("saving");
    Promise.all(sending).then(function (results) {
      setSubmit(results.every(Boolean) ? "done" : "idle");
    });
  }

  if (submit) submit.addEventListener("click", saveAll);

  // --- Saisie ---

  cards.forEach(function (card) {
    card.addEventListener("focusin", function (event) {
      // Chiffre déjà présent : sélectionné, il est remplacé par le prochain chiffre tapé
      var input = event.target;
      if (input.dataset.score) setTimeout(function () { input.select(); }, 0); // délai : mobiles
    });
    card.addEventListener("input", function (event) {
      var input = event.target;
      if (!input.dataset.score) return;
      input.value = input.value.replace(/[^0-9]/g, "").slice(-1);
      input.classList.toggle("filled", input.value !== "");
      card._dirty = true;
      showError(card, "");
      setSubmit("idle"); // nouvelle saisie : à valider de nouveau
      if (input.value !== "") moveFocus(input, card);
    });
  });

  // Pronos remplis mais pas envoyés : le navigateur demande confirmation avant de quitter
  window.addEventListener("beforeunload", function (event) {
    if (!pendingCards().length) return;
    event.preventDefault();
    event.returnValue = messages.msgLeave || "";
  });

  // Retour du réseau : on renvoie les pronos qui n'ont pas pu partir
  window.addEventListener("online", function () {
    cards.forEach(function (card) { if (card._failed && isFilled(card)) save(card); });
  });
})();
