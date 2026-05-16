const isBrowser = typeof window !== "undefined";

function apiBase(): string {
  if (isBrowser) {
    return "/api/proxy";
  }
  return process.env.BACKEND_URL ?? "http://localhost:8000";
}

function headers(): HeadersInit {
  if (isBrowser) {
    return { "Content-Type": "application/json" };
  }
  return {
    "Content-Type": "application/json",
    "X-API-Key": process.env.API_SECRET_KEY ?? "",
  };
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const base = apiBase();
  const url = isBrowser ? `${base}?path=${encodeURIComponent(path)}` : `${base}${path}`;
  const res = await fetch(url, { ...init, headers: { ...headers(), ...init?.headers } });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`API error ${res.status}: ${text}`);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body: unknown) =>
    request<T>(path, { method: "POST", body: JSON.stringify(body) }),
  patch: <T>(path: string, body: unknown) =>
    request<T>(path, { method: "PATCH", body: JSON.stringify(body) }),
  delete: (path: string) => request<void>(path, { method: "DELETE" }),
};
