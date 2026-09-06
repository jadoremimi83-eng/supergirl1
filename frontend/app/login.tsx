import React, { useEffect, useState } from "react";
import {
  View,
  Text,
  TextInput,
  StyleSheet,
  Pressable,
  ActivityIndicator,
} from "react-native";
import { useRouter } from "expo-router";
import { LinearGradient } from "expo-linear-gradient";
import { Image } from "expo-image";
import { Feather } from "@expo/vector-icons";
import { KeyboardAwareScrollView } from "react-native-keyboard-controller";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { useAuth } from "@/src/auth";
import { colors, spacing, radius, type, font } from "@/src/theme";
import { GoldButton } from "@/src/components/ui";

export default function Login() {
  const { login } = useAuth();
  const router = useRouter();
  const insets = useSafeAreaInsets();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [heroUri, setHeroUri] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      try {
        const r = await fetch(`${process.env.EXPO_PUBLIC_BACKEND_URL}/api/assistant/public`);
        if (r.ok) {
          const d = await r.json();
          if (d.avatar_url) setHeroUri(`${process.env.EXPO_PUBLIC_BACKEND_URL}${d.avatar_url}`);
        }
      } catch {}
    })();
  }, []);

  const submit = async () => {
    if (!email || !password) {
      setError("Inserisci email e password");
      return;
    }
    setBusy(true);
    setError("");
    try {
      await login(email.trim(), password);
      router.replace("/priorities");
    } catch (e: any) {
      setError(e.message || "Accesso non riuscito");
    } finally {
      setBusy(false);
    }
  };

  const quickFill = (role: "admin" | "operator") => {
    if (role === "admin") {
      setEmail("admin@supergirl.app");
      setPassword("Admin123!");
    } else {
      setEmail("operatore@supergirl.app");
      setPassword("Operatore123!");
    }
    setError("");
  };

  return (
    <LinearGradient colors={["#0A0A0A", "#141210", "#1F1A10"]} style={{ flex: 1 }}>
      <KeyboardAwareScrollView
        contentContainerStyle={[
          styles.content,
          { paddingTop: insets.top + spacing["3xl"], paddingBottom: insets.bottom + spacing.xl },
        ]}
        bottomOffset={24}
        showsVerticalScrollIndicator={false}
      >
        <View style={styles.brandBlock}>
          {heroUri ? (
            <Image source={{ uri: heroUri }} style={styles.hero} contentFit="cover" transition={250} testID="login-hero" />
          ) : (
            <View style={styles.logoRing}>
              <Text style={styles.logoInitials}>SG</Text>
            </View>
          )}
          {!heroUri ? <Text style={styles.brand}>SUPER GIRL</Text> : null}
          <Text style={styles.tagline}>CRM CONVERSAZIONALE · AI</Text>
        </View>

        <View style={styles.form}>
          <Text style={styles.label}>Email</Text>
          <View style={styles.inputWrap}>
            <Feather name="mail" size={18} color={colors.onSurfaceTertiary} />
            <TextInput
              testID="login-email-input"
              value={email}
              onChangeText={setEmail}
              placeholder="nome@supergirl.app"
              placeholderTextColor={colors.onSurfaceTertiary}
              autoCapitalize="none"
              keyboardType="email-address"
              style={styles.input}
            />
          </View>

          <Text style={styles.label}>Password</Text>
          <View style={styles.inputWrap}>
            <Feather name="lock" size={18} color={colors.onSurfaceTertiary} />
            <TextInput
              testID="login-password-input"
              value={password}
              onChangeText={setPassword}
              placeholder="••••••••"
              placeholderTextColor={colors.onSurfaceTertiary}
              secureTextEntry
              style={styles.input}
            />
          </View>

          {error ? (
            <Text style={styles.error} testID="login-error">
              {error}
            </Text>
          ) : null}

          <Pressable
            testID="login-submit-button"
            onPress={submit}
            disabled={busy}
            style={({ pressed }) => [styles.submit, pressed && { opacity: 0.9 }]}
          >
            {busy ? (
              <ActivityIndicator color={colors.onBrandPrimary} />
            ) : (
              <Text style={styles.submitText}>ACCEDI</Text>
            )}
          </Pressable>

          <Text style={styles.demoLabel}>Accesso rapido demo</Text>
          <View style={styles.demoRow}>
            <View style={{ flex: 1 }}>
              <GoldButton
                title="Admin"
                icon="shield"
                variant="outline"
                small
                testID="quick-admin"
                onPress={() => quickFill("admin")}
              />
            </View>
            <View style={{ flex: 1 }}>
              <GoldButton
                title="Operatore"
                icon="user"
                variant="outline"
                small
                testID="quick-operator"
                onPress={() => quickFill("operator")}
              />
            </View>
          </View>
        </View>
      </KeyboardAwareScrollView>
    </LinearGradient>
  );
}

const styles = StyleSheet.create({
  content: { paddingHorizontal: spacing.xl, flexGrow: 1 },
  brandBlock: { alignItems: "center", marginBottom: spacing["2xl"] },
  hero: { width: "78%", aspectRatio: 1, borderRadius: radius.lg, marginBottom: spacing.lg, backgroundColor: colors.surfaceSecondary, borderWidth: 1, borderColor: colors.borderStrong },
  logoRing: {
    width: 84,
    height: 84,
    borderRadius: 42,
    borderWidth: 1.5,
    borderColor: colors.brandPrimary,
    alignItems: "center",
    justifyContent: "center",
    marginBottom: spacing.lg,
    backgroundColor: colors.brandTertiary,
  },
  logoInitials: {
    fontFamily: font.display,
    fontSize: 34,
    color: colors.brandPrimary,
    fontWeight: "700",
  },
  brand: {
    fontFamily: font.display,
    fontSize: 34,
    letterSpacing: 4,
    color: colors.onSurface,
    fontWeight: "700",
  },
  tagline: {
    color: colors.brandSecondary,
    fontSize: 11,
    letterSpacing: 3,
    marginTop: spacing.xs,
    fontWeight: "600",
  },
  form: { gap: spacing.sm },
  label: {
    color: colors.onSurfaceSecondary,
    fontSize: 12,
    fontWeight: "700",
    letterSpacing: 0.5,
    marginTop: spacing.md,
  },
  inputWrap: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.sm,
    backgroundColor: colors.surfaceSecondary,
    borderRadius: radius.md,
    borderWidth: 1,
    borderColor: colors.border,
    paddingHorizontal: spacing.lg,
  },
  input: {
    flex: 1,
    color: colors.onSurface,
    fontSize: type.lg,
    paddingVertical: 14,
  },
  error: { color: colors.onError, fontSize: type.base, marginTop: spacing.sm },
  submit: {
    backgroundColor: colors.brandPrimary,
    borderRadius: radius.md,
    paddingVertical: 16,
    alignItems: "center",
    marginTop: spacing.xl,
  },
  submitText: {
    color: colors.onBrandPrimary,
    fontSize: type.lg,
    fontWeight: "800",
    letterSpacing: 1.5,
  },
  demoLabel: {
    color: colors.onSurfaceTertiary,
    fontSize: 11,
    textAlign: "center",
    marginTop: spacing.xl,
    marginBottom: spacing.sm,
    letterSpacing: 1,
    textTransform: "uppercase",
  },
  demoRow: { flexDirection: "row", gap: spacing.md },
});
