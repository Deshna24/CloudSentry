// Backend URL comes from the build-time environment variable VITE_API_URL.
// If it is empty the app talks to the same origin that served it (e.g. behind a reverse proxy).
export const API_URL = (import.meta.env.VITE_API_URL || window.location.origin).replace(/\/$/, '');
