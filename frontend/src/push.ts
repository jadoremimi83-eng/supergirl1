import { Platform } from "react-native";
import * as Notifications from "expo-notifications";

const BASE = process.env.EXPO_PUBLIC_BACKEND_URL;

/**
 * Registra il dispositivo per le notifiche push (Emergent managed relay).
 * Chiamare al login e a ogni apertura app. Non blocca mai il flusso in caso di rifiuto.
 */
export async function registerForPush(userId: string) {
  if (Platform.OS === "web" || !userId) return;
  try {
    const { status } = await Notifications.requestPermissionsAsync();
    if (status !== "granted") return;
    const tokenResp = await Notifications.getDevicePushTokenAsync();
    await fetch(`${BASE}/api/register-push`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        user_id: userId,
        platform: Platform.OS,
        device_token: tokenResp.data,
      }),
    });
  } catch (e) {
    // non-blocking
    console.log("registerForPush skipped:", e);
  }
}
