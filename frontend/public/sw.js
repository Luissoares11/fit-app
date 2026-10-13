// Makes the app installable. Nothing is cached: every request goes to the network,
// so the data (and the login cookie) is always fresh.
self.addEventListener('install', () => self.skipWaiting())
self.addEventListener('activate', (event) => event.waitUntil(self.clients.claim()))
self.addEventListener('fetch', () => {})
