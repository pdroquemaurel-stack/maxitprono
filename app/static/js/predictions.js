// Saisie des pronostics, sans bouton :
// - une case = un chiffre (0 à 9) ; après le score domicile on passe à l'extérieur,
//   après l'extérieur on passe au match suivant ;
// - dès que les deux cases d'un match sont remplies, le prono est envoyé au serveur
//   (POST /matches/<id>/prediction), puis la carte affiche « Enregistré » ou l'erreur.
(function () {
  var form = document.querySelector(".predictions-form");
  if (!form) return;
  var messages = form.dataset;
  var homeInputs = Array.prototype.slice.call(form.querySelectorAll('[data-match-id] [data-score="home"]'));

  function digitOf(input) {
    var value = input.value.trim();
    return /^[0-9]$/.test(value) ? value : null;
  }

  function nextHomeInput(card) {
    for (var i = 0; i < homeInputs.length; i++) {
      var other = homeInputs[i].closest(".match-card");
      if (other !== card && (card.compareDocumentPosition(other) & Node.DOCUMENT_POSITION_FOLLOWING)) {
        return homeInputs[i];
      }
    }
    return null;
  }

  function moveFocus(input, card) {
    var target = input.dataset.score === "home"
      ? card.querySelector('[data-score="away"]')
      : nextHomeInput(card);
    if (target) target.focus();
    else input.blur(); // dernier match : on ferme le clavier
  }

  // --- Affichage de l'état sur la carte ---

  function setStatus(card, text) {
    var status = card.querySelector("[data-save-status]");
    if (!status) return;
    status.textContent = text;
    status.classList.remove("closing");
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

  // --- Envoi ---

  function save(card) {
    var home = digitOf(card.querySelector('[data-score="home"]'));
    var away = digitOf(card.querySelector('[data-score="away"]'));
    if (home === null || away === null) return;
    // Numéro d'envoi : on ignore la réponse d'un envoi dépassé par une saisie plus récente
    var sent = (card._sent || 0) + 1;
    card._sent = sent;
    card._failed = false;
    setStatus(card, messages.msgSaving);
    fetch("/matches/" + card.dataset.matchId + "/prediction", {
      method: "POST",
      credentials: "same-origin",
      headers: { Accept: "application/json" },
      body: new URLSearchParams({ home: home, away: away })
    }).then(function (response) {
      if (response.redirected) { // session expirée : page de connexion
        window.location.href = response.url;
        return null;
      }
      return response.json();
    }).then(function (data) {
      if (!data || card._sent !== sent) return;
      if (data.saved) {
        setStatus(card, messages.msgSaved);
        showError(card, "");
        if (!("predicted" in card.dataset)) {
          card.dataset.predicted = "";
          decrementTodo();
        }
      } else {
        setStatus(card, "");
        showError(card, data.error);
      }
    }).catch(function () {
      if (card._sent !== sent) return;
      card._failed = true;
      setStatus(card, "");
      showError(card, messages.msgOffline);
    });
  }

  // --- Saisie ---

  Array.prototype.forEach.call(form.querySelectorAll("[data-match-id]"), function (card) {
    card.addEventListener("focusin", function (event) {
      // Chiffre déjà présent : sélectionné, il est remplacé par le prochain chiffre tapé
      var input = event.target;
      if (input.dataset.score) setTimeout(function () { input.select(); }, 0); // délai : mobiles
    });
    card.addEventListener("input", function (event) {
      var input = event.target;
      if (!input.dataset.score) return;
      input.value = input.value.replace(/[^0-9]/g, "").slice(-1);
      if (input.value === "") return;
      moveFocus(input, card);
      save(card);
    });
  });

  // Retour du réseau : on renvoie les pronos qui n'ont pas pu partir
  window.addEventListener("online", function () {
    Array.prototype.forEach.call(form.querySelectorAll("[data-match-id]"), function (card) {
      if (card._failed) save(card);
    });
  });
})();
