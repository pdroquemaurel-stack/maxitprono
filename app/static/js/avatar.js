// Réduit la photo choisie à 256 x 256 px (JPEG) avant l'envoi : page légère en 3G.
// Sans JavaScript, le fichier d'origine est envoyé tel quel (limite côté serveur).
document.querySelectorAll("input[type=file][data-avatar]").forEach(function (input) {
  input.addEventListener("change", function () {
    var file = input.files[0];
    if (!file) return;
    var img = new Image();
    img.onload = function () {
      var size = 256;
      var side = Math.min(img.width, img.height); // recadrage carré, centré
      var canvas = document.createElement("canvas");
      canvas.width = canvas.height = size;
      canvas.getContext("2d").drawImage(img, (img.width - side) / 2, (img.height - side) / 2,
                                        side, side, 0, 0, size, size);
      var dataUrl = canvas.toDataURL("image/jpeg", 0.8);
      input.form.querySelector("input[name=avatar_data]").value = dataUrl;
      var preview = document.getElementById("avatar_preview");
      preview.src = dataUrl;
      preview.hidden = false;
      input.value = ""; // le gros fichier d'origine n'est pas envoyé
      URL.revokeObjectURL(img.src);
    };
    img.src = URL.createObjectURL(file);
  });
});
