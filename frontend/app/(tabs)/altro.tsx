import React from "react";
import { View, Text, StyleSheet, ScrollView, Pressable } from "react-native";
import { useRouter } from "expo-router";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { Feather } from "@expo/vector-icons";
import { useAuth } from "@/src/auth";
import { colors, spacing, radius, type, font } from "@/src/theme";
import { AppHeader } from "@/src/components/AppHeader";
import { Avatar } from "@/src/components/ui";

const ITEMS = [
  { key: "servizi", label: "Servizi", desc: "Trattamenti, prezzi, promozioni, FAQ", icon: "star", route: "/altro/servizi" },
  { key: "sedi", label: "Sedi", desc: "Indirizzi, telefoni, orari", icon: "map-pin", route: "/altro/sedi" },
  { key: "campagne", label: "Campagne", desc: "Campagne Meta e lead collegati", icon: "target", route: "/altro/campagne" },
  { key: "chiamate-corsi", label: "Chiamate Corsi", desc: "Chiamate corso fissate da Andrea", icon: "phone-call", route: "/altro/chiamate-corsi" },
  { key: "prezzi-corsi", label: "Prezzi Corsi", desc: "Listino interno corsi (non comunicato in automatico)", icon: "tag", route: "/altro/prezzi-corsi", admin: true },
  { key: "team", label: "Team", desc: "Utenti e ruoli", icon: "users", route: "/altro/team" },
  { key: "kb", label: "Conoscenza AI", desc: "Knowledge Base dell'assistente", icon: "book-open", route: "/altro/conoscenza-ai", admin: true },
  { key: "test-andrea", label: "Test Andrea", desc: "Prova le risposte dell'AI sulla Knowledge Base", icon: "message-circle", route: "/altro/test-andrea", admin: true },
  { key: "integrazioni", label: "Integrazioni", desc: "Meta, WhatsApp, AI (Fase 2/3/4)", icon: "link", route: "/altro/integrazioni" },
  { key: "impostazioni", label: "Impostazioni", desc: "Account, follow-up, notifiche", icon: "settings", route: "/altro/impostazioni" },
];

export default function Altro() {
  const insets = useSafeAreaInsets();
  const router = useRouter();
  const { user, logout } = useAuth();

  const visible = ITEMS.filter((i) => !i.admin || user?.role === "admin");

  return (
    <View style={{ flex: 1, backgroundColor: colors.surface }}>
      <AppHeader title="Altro" subtitle="Configurazione" />
      <ScrollView
        contentContainerStyle={{ padding: spacing.lg, paddingBottom: insets.bottom + spacing["2xl"] }}
        showsVerticalScrollIndicator={false}
      >
        <View style={styles.userCard}>
          <Avatar name={user?.name} size={52} />
          <View style={{ flex: 1 }}>
            <Text style={styles.userName}>{user?.name}</Text>
            <Text style={styles.userEmail}>{user?.email}</Text>
          </View>
          <View style={styles.roleBadge}>
            <Text style={styles.roleText}>{user?.role === "admin" ? "ADMIN" : "OPERATORE"}</Text>
          </View>
        </View>

        {visible.map((it) => (
          <Pressable
            key={it.key}
            testID={`altro-${it.key}`}
            onPress={() => router.push(it.route as any)}
            style={({ pressed }) => [styles.row, pressed && { opacity: 0.85 }]}
          >
            <View style={styles.iconBox}>
              <Feather name={it.icon as any} size={19} color={colors.brandPrimary} />
            </View>
            <View style={{ flex: 1 }}>
              <Text style={styles.rowLabel}>{it.label}</Text>
              <Text style={styles.rowDesc}>{it.desc}</Text>
            </View>
            <Feather name="chevron-right" size={20} color={colors.onSurfaceTertiary} />
          </Pressable>
        ))}

        <Pressable testID="logout-button" onPress={logout} style={styles.logout}>
          <Feather name="log-out" size={18} color={colors.onError} />
          <Text style={styles.logoutText}>Esci</Text>
        </Pressable>

        <Text style={styles.version}>SUPER GIRL · Fase 1 Demo</Text>
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  userCard: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.md,
    backgroundColor: colors.surfaceSecondary,
    borderRadius: radius.md,
    borderWidth: 1,
    borderColor: colors.border,
    padding: spacing.lg,
    marginBottom: spacing.lg,
  },
  userName: { color: colors.onSurface, fontSize: type.lg, fontWeight: "700" },
  userEmail: { color: colors.onSurfaceTertiary, fontSize: 12, marginTop: 2 },
  roleBadge: { backgroundColor: colors.brandTertiary, paddingHorizontal: 10, paddingVertical: 5, borderRadius: radius.pill },
  roleText: { color: colors.brandPrimary, fontSize: 10, fontWeight: "800", letterSpacing: 0.5 },
  row: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.md,
    backgroundColor: colors.surfaceSecondary,
    borderRadius: radius.md,
    borderWidth: 1,
    borderColor: colors.border,
    padding: spacing.md,
    marginBottom: spacing.sm,
  },
  iconBox: {
    width: 40,
    height: 40,
    borderRadius: radius.sm,
    backgroundColor: colors.brandTertiary,
    alignItems: "center",
    justifyContent: "center",
  },
  rowLabel: { color: colors.onSurface, fontSize: type.lg, fontWeight: "700" },
  rowDesc: { color: colors.onSurfaceTertiary, fontSize: 12, marginTop: 1 },
  logout: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: spacing.sm,
    marginTop: spacing.lg,
    paddingVertical: 14,
    borderRadius: radius.md,
    borderWidth: 1,
    borderColor: colors.error,
  },
  logoutText: { color: colors.onError, fontSize: type.lg, fontWeight: "700" },
  version: { color: colors.onSurfaceTertiary, fontSize: 11, textAlign: "center", marginTop: spacing.xl, letterSpacing: 1 },
});
