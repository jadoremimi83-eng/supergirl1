import React, { useCallback, useState } from "react";
import { View, Text, StyleSheet, ScrollView, Pressable } from "react-native";
import { useFocusEffect } from "expo-router";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { Feather } from "@expo/vector-icons";
import { api } from "@/src/api";
import { useAuth } from "@/src/auth";
import { colors, spacing, radius, type } from "@/src/theme";
import { SubHeader } from "@/src/components/SubHeader";
import { Loading, Sheet, GoldButton, Avatar } from "@/src/components/ui";
import { Field } from "./servizi";

export default function Team() {
  const insets = useSafeAreaInsets();
  const { user } = useAuth();
  const isAdmin = user?.role === "admin";
  const [items, setItems] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [sheet, setSheet] = useState(false);
  const [form, setForm] = useState({ name: "", email: "", role: "operator", password: "Operatore123!" });
  const [err, setErr] = useState("");

  const load = useCallback(async () => {
    try { setItems(await api.get("/team")); } catch {}
    setLoading(false);
  }, []);
  useFocusEffect(useCallback(() => { load(); }, [load]));

  const save = async () => {
    setErr("");
    if (!form.name.trim() || !form.email.trim()) { setErr("Nome ed email obbligatori"); return; }
    try {
      await api.post("/team", form);
      setSheet(false);
      setForm({ name: "", email: "", role: "operator", password: "Operatore123!" });
      load();
    } catch (e: any) { setErr(e.message); }
  };

  return (
    <View style={{ flex: 1, backgroundColor: colors.surface }}>
      <SubHeader title="Team" right={isAdmin ? <Pressable onPress={() => setSheet(true)} testID="add-team-button"><Feather name="user-plus" size={22} color={colors.brandPrimary} /></Pressable> : null} />
      {loading ? <Loading /> : (
        <ScrollView contentContainerStyle={{ padding: spacing.lg, paddingBottom: insets.bottom + spacing.xl }} showsVerticalScrollIndicator={false}>
          {items.map((u) => (
            <View key={u.id} style={styles.card} testID={`team-${u.id}`}>
              <Avatar name={u.name} size={44} />
              <View style={{ flex: 1 }}>
                <Text style={styles.name}>{u.name}</Text>
                <Text style={styles.email}>{u.email}</Text>
              </View>
              <View style={[styles.roleBadge, u.role === "admin" && { backgroundColor: colors.brandPrimary }]}>
                <Text style={[styles.roleText, u.role === "admin" && { color: colors.onBrandPrimary }]}>
                  {u.role === "admin" ? "ADMIN" : "OPERATORE"}
                </Text>
              </View>
            </View>
          ))}
        </ScrollView>
      )}
      <Sheet visible={sheet} onClose={() => setSheet(false)} title="Nuovo membro del team">
        <Field label="Nome" value={form.name} onChange={(v) => setForm({ ...form, name: v })} />
        <Field label="Email" value={form.email} onChange={(v) => setForm({ ...form, email: v })} />
        <Text style={styles.roleLabel}>Ruolo</Text>
        <View style={styles.roleRow}>
          {["operator", "admin"].map((r) => (
            <Pressable key={r} onPress={() => setForm({ ...form, role: r })} style={[styles.roleOpt, form.role === r && { backgroundColor: colors.brandPrimary, borderColor: colors.brandPrimary }]} testID={`role-${r}`}>
              <Text style={[styles.roleOptText, form.role === r && { color: colors.onBrandPrimary }]}>{r === "admin" ? "Admin" : "Operatore"}</Text>
            </Pressable>
          ))}
        </View>
        <Field label="Password" value={form.password} onChange={(v) => setForm({ ...form, password: v })} />
        {!!err && <Text style={styles.err}>{err}</Text>}
        <GoldButton title="Crea utente" icon="user-plus" onPress={save} testID="save-team-button" />
      </Sheet>
    </View>
  );
}

const styles = StyleSheet.create({
  card: { flexDirection: "row", alignItems: "center", gap: spacing.md, backgroundColor: colors.surfaceSecondary, borderRadius: radius.md, borderWidth: 1, borderColor: colors.border, padding: spacing.md, marginBottom: spacing.sm },
  name: { color: colors.onSurface, fontSize: type.lg, fontWeight: "700" },
  email: { color: colors.onSurfaceTertiary, fontSize: 12, marginTop: 1 },
  roleBadge: { backgroundColor: colors.surfaceTertiary, paddingHorizontal: 10, paddingVertical: 5, borderRadius: radius.pill },
  roleText: { color: colors.onSurfaceSecondary, fontSize: 10, fontWeight: "800", letterSpacing: 0.5 },
  roleLabel: { color: colors.onSurfaceSecondary, fontSize: 12, fontWeight: "700", marginBottom: 6 },
  roleRow: { flexDirection: "row", gap: spacing.sm, marginBottom: spacing.md },
  roleOpt: { flex: 1, alignItems: "center", paddingVertical: 12, borderRadius: radius.sm, borderWidth: 1, borderColor: colors.border, backgroundColor: colors.surface },
  roleOptText: { color: colors.onSurfaceSecondary, fontSize: 14, fontWeight: "700" },
  err: { color: colors.onError, fontSize: 13, marginBottom: spacing.sm },
});
