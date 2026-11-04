// Envoie au serveur le fuseau horaire du téléphone (cookie "tz") pour afficher
// les heures des matchs en heure locale. Recharge la page une seule fois si besoin.
(function () {
  var tz;
  try { tz = Intl.DateTimeFormat().resolvedOptions().timeZone; } catch (e) { return; }
  if (!tz) return;
  var current = (document.cookie.match(/(?:^|; )tz=([^;]*)/) || [])[1];
  if (current && decodeURIComponent(current) === tz) return;
  document.cookie = "tz=" + encodeURIComponent(tz) + "; path=/; max-age=31536000; samesite=lax";
  // Ne recharge que si le cookie a bien été accepté (évite une boucle)
  if (document.cookie.indexOf("tz=") !== -1) location.reload();
})();
