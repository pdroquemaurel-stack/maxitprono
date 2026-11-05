// Service worker : affiche notre page « Pas de connexion » quand le réseau ne répond pas.
// Il ne garde que cette page et ce qu'il faut pour l'afficher : les données restent toujours à jour.
const CACHE = "maxitprono-offline-v1";
const OFFLINE_URL = "/offline";
const ASSETS = [OFFLINE_URL, "/static/css/style.css", "/static/fonts/dm-sans.woff2",
                "/static/fonts/outfit.woff2"];

self.addEventListener("install", function (event) {
  event.waitUntil(caches.open(CACHE).then(function (cache) { return cache.addAll(ASSETS); })
    .then(function () { return self.skipWaiting(); }));
});

self.addEventListener("activate", function (event) {
  // Supprime les anciennes versions du cache
  event.waitUntil(caches.keys().then(function (keys) {
    return Promise.all(keys.filter(function (key) { return key !== CACHE; })
      .map(function (key) { return caches.delete(key); }));
  }).then(function () { return self.clients.claim(); }));
});

self.addEventListener("fetch", function (event) {
  const request = event.request;
  if (request.method !== "GET") return;
  if (request.mode === "navigate") {
    // Une page : le réseau d'abord, notre page hors connexion s'il ne répond pas
    event.respondWith(fetch(request).catch(function () { return caches.match(OFFLINE_URL); }));
    return;
  }
  const path = new URL(request.url).pathname;
  if (ASSETS.indexOf(path) !== -1) {
    // Feuille de style et polices de la page hors connexion (le numéro de version est ignoré)
    event.respondWith(fetch(request).catch(function () {
      return caches.match(path, { ignoreSearch: true });
    }));
  }
});
