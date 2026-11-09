// Page Profil : partage des stats (partage natif, sinon copie du lien) et choix de la compétition.
document.querySelectorAll("[data-share-stats]").forEach(function (button) {
  var status = document.querySelector(".p-share-status");
  function show(message) {
    status.textContent = message;
    status.hidden = false;
  }
  button.addEventListener("click", function () {
    var text = button.dataset.text, url = button.dataset.url;
    if (navigator.share) {
      navigator.share({ text: text, url: url }).catch(function () {});
    } else if (navigator.clipboard) {
      navigator.clipboard.writeText(text + " " + url).then(function () {
        show(button.dataset.copied);
      }, function () { show(url); });
    } else {
      show(url); // dernier recours : le lien affiché, à copier à la main
    }
  });
});

document.querySelectorAll("select[data-autosubmit]").forEach(function (select) {
  select.addEventListener("change", function () { select.form.submit(); });
});
