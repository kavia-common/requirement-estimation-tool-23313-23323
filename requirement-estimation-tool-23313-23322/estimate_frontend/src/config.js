/**
 * PUBLIC_INTERFACE
 * getApiBaseUrl
 * Returns the configured API base URL for the frontend to call the backend service.
 * Reads from REACT_APP_API_BASE_URL environment variable (set in .env).
 */
export function getApiBaseUrl() {
  /** Returns the API base URL string. */
  const fallback = "http://localhost:3001";
  const url = process.env.REACT_APP_API_BASE_URL || fallback;
  return url.replace(/\/+$/, ""); // normalize by removing trailing slashes
}

/**
 * PUBLIC_INTERFACE
 * apiFetch
 * Thin wrapper around fetch that prefixes the API base URL.
 */
export async function apiFetch(path, options = {}) {
  /** Perform a fetch to the backend using the configured API base URL. */
  const base = getApiBaseUrl();
  const fullUrl = `${base}${path.startsWith("/") ? "" : "/"}${path}`;
  return fetch(fullUrl, options);
}
