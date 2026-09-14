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
      const d = body.detail;
      if (typeof d === "string") detail = d;
      else if (d?.meta_error?.error?.error_user_msg) detail = d.meta_error.error.error_user_msg;
      else if (d?.meta_error?.error?.message) detail = d.meta_error.error.message;
      else if (d) detail = JSON.stringify(d);
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

// Upload immagine (multipart) — gestisce sia web che native
export async function uploadImage(uri: string, name = "photo.jpg", type = "image/jpeg") {
  const { Platform } = require("react-native");
  const token = await storage.secureGet<string>(TOKEN_KEY, "");
  const form = new FormData();
  if (Platform.OS === "web") {
    const blob = await (await fetch(uri)).blob();
    form.append("file", blob, name);
  } else {
    form.append("file", { uri, name, type } as any);
  }
  const res = await fetch(`${BASE}/api/upload`, {
    method: "POST",
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    body: form,
  });
  if (!res.ok) throw new Error("Upload non riuscito");
  return res.json();
}

// Upload generico (foto benvenuto WhatsApp) → { url }
export async function uploadWelcomePhoto(uri: string, name: string, type: string) {
  const { Platform } = require("react-native");
  const token = await storage.secureGet<string>(TOKEN_KEY, "");
  const form = new FormData();
  if (Platform.OS === "web") {
    const blob = await (await fetch(uri)).blob();
    form.append("file", blob, name);
  } else {
    form.append("file", { uri, name, type } as any);
  }
  const res = await fetch(`${BASE}/api/meta/upload-welcome-photo`, {
    method: "POST",
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    body: form,
  });
  if (!res.ok) throw new Error("Upload foto non riuscito");
  return res.json();
}

// Upload asset Meta (foto O video) → ritorna { type, image_hash|video_id, thumb_url }
export async function uploadMetaAsset(uri: string, name: string, type: string) {
  const { Platform } = require("react-native");
  const token = await storage.secureGet<string>(TOKEN_KEY, "");
  const form = new FormData();
  if (Platform.OS === "web") {
    const blob = await (await fetch(uri)).blob();
    form.append("file", blob, name);
  } else {
    form.append("file", { uri, name, type } as any);
  }
  const res = await fetch(`${BASE}/api/meta/upload-asset`, {
    method: "POST",
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    body: form,
  });
  if (!res.ok) {
    let d = "Upload non riuscito";
    try { const b = await res.json(); d = b.detail?.meta_error?.error?.error_user_msg || b.detail || d; } catch {}
    throw new Error(typeof d === "string" ? d : "Upload non riuscito");
  }
  return res.json();
}
