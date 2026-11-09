// Écrans Ligues : copier le code ou le lien, inviter par WhatsApp, compte à rebours,
// choix du match, aperçu en direct du formulaire de ligue.

function showStatus(message) {
  var status = document.querySelector(".lg-copy-status");
  if (!status) return;
  status.textContent = message;
  status.hidden = false;
}

// Copier : presse-papiers, sinon partage natif, sinon le texte affiché à copier à la main
document.querySelectorAll("[data-copy]").forEach(function (button) {
  button.addEventListener("click", function () {
    var text = button.dataset.copy;
    if (navigator.clipboard) {
      navigator.clipboard.writeText(text).then(function () {
        showStatus(button.dataset.copied);
      }, function () { showStatus(text); });
    } else if (navigator.share) {
      navigator.share({ text: text }).catch(function () {});
    } else {
      showStatus(text);
    }
  });
});

// WhatsApp : le lien wa.me ; si la web-view refuse de l'ouvrir, partage natif du téléphone
document.querySelectorAll("[data-whatsapp]").forEach(function (link) {
  link.addEventListener("click", function (event) {
    event.preventDefault();
    var opened = window.open(link.href, "_blank"); // sans "noopener", qui renvoie toujours null
    if (!opened && navigator.share) {
      navigator.share({ text: link.dataset.shareText }).catch(function () {});
    } else if (!opened) {
      window.location.href = link.href;
    }
  });
});

// « Ferme dans 2 h 14 » : mis à jour chaque minute (moins de 24 h avant la clôture)
document.querySelectorAll("[data-deadline]").forEach(function (pill) {
  var deadline = new Date(pill.dataset.deadline).getTime();
  var label = pill.querySelector("span:last-child");
  function tick() {
    var minutes = Math.ceil((deadline - Date.now()) / 60000);
    if (minutes <= 0) {
      label.textContent = pill.dataset.closed;
      return;
    }
    if (minutes >= 24 * 60) return; // texte du serveur (« Ferme demain », « Ferme samedi »)
    var hours = Math.floor(minutes / 60), rest = minutes % 60;
    label.textContent = hours
      ? pill.dataset.hours.replace("{hours}", hours).replace("{minutes}", rest < 10 ? "0" + rest : rest)
      : pill.dataset.minutes.replace("{minutes}", rest);
    setTimeout(tick, 60000 - (Date.now() % 60000));
  }
  tick();
});

document.querySelectorAll("select[data-autosubmit]").forEach(function (select) {
  select.addEventListener("change", function () { select.form.submit(); });
});

// Formulaire de ligue : aperçu (initiales, nom, couleur) et pastille « Toutes » exclusive
function leagueInitials(name) {
  var parts = name.split(/[\s_\-]+/).filter(Boolean);
  if (parts.length >= 2) return (parts[0][0] + parts[1][0]).toUpperCase();
  return name.slice(0, 2).toUpperCase() || "?";
}

document.querySelectorAll("[data-league-form]").forEach(function (form) {
  var icon = form.querySelector("[data-preview-icon]");
  var name = form.querySelector("[data-preview-name]");
  var input = form.querySelector("[data-preview-input]");
  input.addEventListener("input", function () {
    var value = input.value.trim();
    icon.textContent = leagueInitials(value);
    name.textContent = value || name.dataset.empty;
  });
  form.querySelectorAll("[data-preview-color]").forEach(function (radio) {
    radio.addEventListener("change", function () {
      icon.className = icon.className.replace(/lg-color-\w+/, "lg-color-" + radio.value);
    });
  });

  var all = form.querySelector("[data-chip-all]");
  var others = form.querySelectorAll("input[name=competitions]:not([data-chip-all])");
  all.addEventListener("change", function () {
    if (all.checked) others.forEach(function (box) { box.checked = false; });
  });
  others.forEach(function (box) {
    box.addEventListener("change", function () {
      var any = Array.prototype.some.call(others, function (b) { return b.checked; });
      all.checked = !any;
    });
  });
});
