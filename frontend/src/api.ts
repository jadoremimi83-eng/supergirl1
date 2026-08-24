import { storage } from "@/src/utils/storage";

const BASE = process.env.EXPO_PUBLIC_BACKEND_URL;
export const TOKEN_KEY = "supergirl_token";

async function authHeaders(): Promise<Record<string, string>> {
  const token = await storage.secureGet<string>(TOKEN_KEY, "");
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function request(path: string, options: RequestInit = {}) {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(await authHeaders()),
    ...((options.headers as Record<string, string>) || {}),
  };
  const res = await fetch(`${BASE}/api${path}`, { ...options, headers });
  if (!res.ok) {
    let detail = "Errore di rete";
    try {
      const body = await res.json();
      detail = body.detail || detail;
    } catch {}
    throw new Error(detail);
  }
  if (res.status === 204) return null;
  return res.json();
}

export const api = {
  get: (p: string) => request(p),
  post: (p: string, body?: any) =>
    request(p, { method: "POST", body: body ? JSON.stringify(body) : undefined }),
  patch: (p: string, body?: any) =>
    request(p, { method: "PATCH", body: body ? JSON.stringify(body) : undefined }),
  del: (p: string) => request(p, { method: "DELETE" }),
};
