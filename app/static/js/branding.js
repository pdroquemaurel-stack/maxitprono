// Admin → Personnalisation : aperçu en direct pendant la saisie.
// Les teintes et le contraste reprennent exactement le calcul de app/services/branding.py
// (le serveur refait le contrôle à l'enregistrement : ce script n'est qu'un confort).
(function () {
  var form = document.querySelector("[data-branding-form]");
  if (!form) return;
  var preview = form.querySelector("[data-brand-preview]");
  var contrast = form.querySelector("[data-contrast]");
  var warning = form.querySelector("[data-contrast-warning]");
  var saveButton = form.querySelector("[data-branding-save]");
  var lang = document.documentElement.lang;
  var MIN_CONTRAST = 4.5;
  var WHITE = "#FFFFFF", BLACK = "#000000";

  function field(name) { return form.elements[name]; }

  // --- Couleurs ---
  function cleanColor(text) {
    var color = text.trim().toUpperCase();
    return /^#[0-9A-F]{6}$/.test(color) ? color : null;
  }

  function toRgb(color) {
    return [1, 3, 5].map(function (i) { return parseInt(color.slice(i, i + 2), 16); });
  }

  function toHex(rgb) {
    return "#" + rgb.map(function (v) { return v.toString(16).padStart(2, "0"); }).join("").toUpperCase();
  }

  // Python arrondit « au pair » (round(2.5) = 2) : même règle ici pour obtenir les mêmes teintes
  function roundHalfEven(value) {
    var floor = Math.floor(value), diff = value - floor;
    if (Math.abs(diff - 0.5) > 1e-9) return Math.round(value);
    return floor % 2 === 0 ? floor : floor + 1;
  }

  function mix(color, other, ratio) {
    var a = toRgb(color), b = toRgb(other);
    return toHex(a.map(function (v, i) { return roundHalfEven(v + (b[i] - v) * ratio); }));
  }

  function luminance(color) {
    var c = toRgb(color).map(function (v) {
      v /= 255;
      return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4);
    });
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2];
  }

  function contrastRatio(a, b) {
    var la = luminance(a), lb = luminance(b);
    return (Math.max(la, lb) + 0.05) / (Math.min(la, lb) + 0.05);
  }

  function textColorOn(background) {
    return contrastRatio(BLACK, background) >= contrastRatio(WHITE, background) ? BLACK : WHITE;
  }

  // Mêmes calculs que palette() dans app/services/branding.py
  function lightenUntilReadable(color, background, start) {
    var ratio = start;
    while (ratio < 1 && contrastRatio(mix(color, WHITE, ratio), background) < MIN_CONTRAST) ratio += 0.02;
    return mix(color, WHITE, Math.min(ratio, 1));
  }

  function transparent(color, opacity) {
    var rgb = toRgb(color);
    return "rgba(" + rgb.join(",") + "," + opacity + ")";
  }

  function palette(primary, dark) {
    var raised = mix(dark, WHITE, 0.065);
    return {
      "--color-primary": primary,
      "--color-primary-on-dark": lightenUntilReadable(primary, raised, 0.25),
      "--color-primary-tint": transparent(primary, 0.14),
      "--color-primary-deep": mix(primary, dark, 0.93),
      "--color-on-primary": textColorOn(primary),
      "--color-dark": dark,
      "--color-surface": mix(dark, WHITE, 0.045),
      "--color-raised": raised,
      "--color-line": mix(dark, WHITE, 0.11),
      "--color-line-strong": mix(dark, WHITE, 0.20)
    };
  }

  // --- Mise à jour de l'aperçu ---
  function splitTagline(text) {
    var match = text.match(/^(.+?[.!?])\s+(.+)$/);
    return match ? [match[1], match[2]] : [text, ""];
  }

  function updateTexts() {
    var logo = preview.querySelector(".p-logo");
    var pill = logo.querySelector(".p-logo-pill");
    logo.firstChild.textContent = field("logo_part1").value.trim() + " ";
    pill.textContent = field("logo_part2").value.trim();
    var parts = splitTagline(field(lang === "en" ? "tagline_en" : "tagline_fr").value.trim());
    preview.querySelector("[data-preview-tagline-start]").textContent = parts[0];
    preview.querySelector("[data-preview-tagline-end]").textContent = parts[1];
  }

  function showWarning(message) {
    warning.hidden = !message;
    warning.textContent = message || "";
    saveButton.disabled = !!message;
  }

  function updateColors() {
    var primary = cleanColor(field("color_primary").value);
    var dark = cleanColor(field("color_dark").value);
    if (!primary || !dark) return showWarning(warning.dataset.invalid);
    var colors = palette(primary, dark);
    Object.keys(colors).forEach(function (name) { preview.style.setProperty(name, colors[name]); });
    var onPrimary = colors["--color-on-primary"];
    var ratio = contrastRatio(primary, onPrimary);
    contrast.textContent = contrast.dataset.label
      .replace("{color}", onPrimary === BLACK ? contrast.dataset.black : contrast.dataset.white)
      .replace("{ratio}", ratio.toFixed(1));
    if (ratio < MIN_CONTRAST) return showWarning(warning.dataset.primary);
    if (contrastRatio(dark, WHITE) < MIN_CONTRAST) return showWarning(warning.dataset.dark);
    showWarning(null);
  }

  // Sélecteur de couleur <-> champ hexadécimal
  form.querySelectorAll("[data-color-picker]").forEach(function (picker) {
    var input = field(picker.dataset.colorPicker);
    picker.addEventListener("input", function () { input.value = picker.value.toUpperCase(); updateColors(); });
    input.addEventListener("input", function () {
      var color = cleanColor(input.value);
      if (color) picker.value = color.toLowerCase();
    });
  });

  form.querySelectorAll("[data-brand-field]").forEach(function (input) {
    input.addEventListener("input", function () { updateTexts(); updateColors(); });
  });

  // « Rétablir les valeurs par défaut » : confirmation avant d'envoyer
  var reset = document.querySelector("form[data-confirm]");
  if (reset) reset.addEventListener("submit", function (event) {
    if (!window.confirm(reset.dataset.confirm)) event.preventDefault();
  });

  updateTexts();
  updateColors();
})();
