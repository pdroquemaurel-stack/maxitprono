// Saisie des pronostics :
// - une case = un chiffre (0 à 9) ; après le score domicile on passe à l'extérieur,
//   après l'extérieur on passe au match suivant ;
// - page Pronos : dès que les deux cases d'un match sont remplies, le prono est envoyé
//   au serveur (POST /matches/<id>/prediction), puis la carte affiche « Enregistré » ou l'erreur ;
// - accueil (data-mode="button") : rien ne part avant le bouton « Valider mes pronos »,
//   qui envoie tous les matchs remplis puis devient « Pronos enregistrés ».
(function () {
  var form = document.querySelector(".predictions-form");
  if (!form) return;
  var messages = form.dataset;
  var withButton = form.dataset.mode === "button";
  var submit = form.querySelector("[data-save-all]");
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

  // Renvoie une promesse : vrai si le prono est enregistré (null si la carte n'est pas remplie)
  function save(card) {
    var home = digitOf(card.querySelector('[data-score="home"]'));
    var away = digitOf(card.querySelector('[data-score="away"]'));
    if (home === null || away === null) return null;
    // Numéro d'envoi : on ignore la réponse d'un envoi dépassé par une saisie plus récente
    var sent = (card._sent || 0) + 1;
    card._sent = sent;
    card._failed = false;
    setStatus(card, messages.msgSaving);
    return fetch("/matches/" + card.dataset.matchId + "/prediction", {
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
      if (!data || card._sent !== sent) return false;
      if (data.saved) {
        setStatus(card, messages.msgSaved);
        showError(card, "");
        if (!("predicted" in card.dataset)) {
          card.dataset.predicted = "";
          decrementTodo();
        }
        return true;
      }
      setStatus(card, "");
      showError(card, data.error);
      return false;
    }).catch(function () {
      if (card._sent !== sent) return false;
      card._failed = true;
      setStatus(card, "");
      showError(card, messages.msgOffline);
      return false;
    });
  }

  // --- Bouton « Valider mes pronos » (accueil) ---

  function setSubmitDone(done) {
    if (!submit) return;
    submit.classList.toggle("done", done);
    submit.textContent = done ? submit.dataset.doneLabel : submit.dataset.label;
  }

  if (submit) {
    submit.addEventListener("click", function () {
      var sending = [];
      Array.prototype.forEach.call(form.querySelectorAll("[data-match-id]"), function (card) {
        var promise = save(card);
        if (promise) sending.push(promise);
      });
      if (!sending.length) return;
      submit.disabled = true;
      Promise.all(sending).then(function (results) {
        submit.disabled = false;
        setSubmitDone(results.every(Boolean));
      });
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
      if (withButton) setSubmitDone(false); // nouvelle saisie : à valider de nouveau
      else save(card);
    });
  });

  // Retour du réseau : on renvoie les pronos qui n'ont pas pu partir
  window.addEventListener("online", function () {
    Array.prototype.forEach.call(form.querySelectorAll("[data-match-id]"), function (card) {
      if (card._failed) save(card);
    });
  });
})();
