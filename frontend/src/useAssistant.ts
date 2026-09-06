import { useCallback, useState } from "react";
import { useFocusEffect } from "expo-router";
import { api } from "@/src/api";

const BACKEND = process.env.EXPO_PUBLIC_BACKEND_URL;

export type Assistant = { name: string; avatarUri: string | null };

// Cache leggera cross-schermata
let cache: Assistant | null = null;

export function useAssistant() {
  const [assistant, setAssistant] = useState<Assistant>(cache || { name: "Andrea", avatarUri: null });

  const refresh = useCallback(async () => {
    try {
      const a = await api.get("/assistant");
      const next = {
        name: a.name || "Andrea",
        avatarUri: a.avatar_url ? `${BACKEND}${a.avatar_url}` : null,
      };
      cache = next;
      setAssistant(next);
    } catch {}
  }, []);

  useFocusEffect(
    useCallback(() => {
      refresh();
    }, [refresh])
  );

  return { assistant, refresh };
}
