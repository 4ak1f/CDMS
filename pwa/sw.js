const CACHE = 'cdms-v1'
const ASSETS = [
  '/mobile/index.html',
  '/mobile/styles.css',
  '/mobile/app.js',
]

self.addEventListener('install', e => {
  e.waitUntil(
    caches.open(CACHE).then(cache => cache.addAll(ASSETS))
  )
})

self.addEventListener('fetch', e => {
  e.respondWith(
    caches.match(e.request).then(cached => cached || fetch(e.request))
  )
})