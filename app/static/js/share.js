// Bouton d'invitation : ouvre le partage natif du téléphone (WhatsApp, SMS…)
// quand il existe ; sinon le lien wa.me du bouton est suivi normalement.
document.querySelectorAll("[data-share-text]").forEach(function (button) {
  if (!navigator.share) return;
  button.addEventListener("click", function (event) {
    event.preventDefault();
    navigator.share({ text: button.dataset.shareText }).catch(function () {});
  });
});
