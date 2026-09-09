/**
 * Обёртка над fetch: JSON, ошибки с полем detail, учёт HTTP Basic из браузера.
 */
export async function apiFetch(url, options = {}) {
  const headers = new Headers(options.headers || {});
  if (options.body && !(options.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  const res = await fetch(url, {
    credentials: "same-origin",
    ...options,
    headers,
  });
  const ct = res.headers.get("content-type") || "";
  let payload = null;
  if (ct.includes("application/json")) {
    payload = await res.json().catch(() => null);
  }
  if (!res.ok) {
    const detail = payload && payload.detail !== undefined ? payload.detail : res.statusText;
    const err = new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
    err.status = res.status;
    throw err;
  }
  return payload;
}
