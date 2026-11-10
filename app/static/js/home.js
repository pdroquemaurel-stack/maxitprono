// Accueil : « Partager » un score exact (partage natif du téléphone, sinon copie du texte).
document.querySelectorAll("[data-home-share]").forEach(function (button) {
  button.addEventListener("click", function () {
    var text = button.dataset.text, url = button.dataset.url;
    if (navigator.share) {
      navigator.share({ text: text, url: url }).catch(function () {});
    } else if (navigator.clipboard) {
      navigator.clipboard.writeText(text + " " + url).then(function () {
        button.querySelector("span").textContent = button.dataset.copied;
      });
    }
  });
});
