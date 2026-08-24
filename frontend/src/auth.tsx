import React, { createContext, useContext, useEffect, useState } from "react";
import { storage } from "@/src/utils/storage";
import { TOKEN_KEY } from "@/src/api";

const BASE = process.env.EXPO_PUBLIC_BACKEND_URL;

export type User = {
  id: string;
  email: string;
  name: string;
  role: "admin" | "operator";
  avatar_color?: string;
};

type AuthState = {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
};

const AuthContext = createContext<AuthState>({} as AuthState);
export const useAuth = () => useContext(AuthContext);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      const token = await storage.secureGet<string>(TOKEN_KEY, "");
      if (token) {
        try {
          const res = await fetch(`${BASE}/api/auth/me`, {
            headers: { Authorization: `Bearer ${token}` },
          });
          if (res.ok) setUser(await res.json());
          else await storage.secureRemove(TOKEN_KEY);
        } catch {
          await storage.secureRemove(TOKEN_KEY);
        }
      }
      setLoading(false);
    })();
  }, []);

  const login = async (email: string, password: string) => {
    const res = await fetch(`${BASE}/api/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      throw new Error(body.detail || "Credenziali non valide");
    }
    const data = await res.json();
    await storage.secureSet(TOKEN_KEY, data.access_token);
    setUser(data.user);
  };

  const logout = async () => {
    await storage.secureRemove(TOKEN_KEY);
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}
