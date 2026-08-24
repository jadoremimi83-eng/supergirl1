import React, { useCallback, useState } from "react";
import { View, Text, StyleSheet, ScrollView, Pressable } from "react-native";
import { useFocusEffect } from "expo-router";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { Feather } from "@expo/vector-icons";
import { api } from "@/src/api";
import { useAuth } from "@/src/auth";
import { colors, spacing, radius, type } from "@/src/theme";
import { SubHeader } from "@/src/components/SubHeader";
import { Loading, Sheet, GoldButton } from "@/src/components/ui";
import { Field } from "./servizi";

const EMPTY = { nome: "", indirizzo: "", telefono: "", orari: "", info: "" };

export default function Sedi() {
  const insets = useSafeAreaInsets();
  const { user } = useAuth();
  const isAdmin = user?.role === "admin";
  const [items, setItems] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [sheet, setSheet] = useState(false);
  const [form, setForm] = useState<any>(EMPTY);
  const [editId, setEditId] = useState<string | null>(null);

  const load = useCallback(async () => {
    try { setItems(await api.get("/locations")); } catch {}
    setLoading(false);
  }, []);
  useFocusEffect(useCallback(() => { load(); }, [load]));

  const save = async () => {
    if (!form.nome.trim()) return;
    const payload = { nome: form.nome, indirizzo: form.indirizzo, telefono: form.telefono, orari: form.orari, info: form.info };
    if (editId) await api.patch(`/locations/${editId}`, payload);
    else await api.post("/locations", payload);
    setSheet(false);
    load();
  };

  return (
    <View style={{ flex: 1, backgroundColor: colors.surface }}>
      <SubHeader title="Sedi" right={isAdmin ? <Pressable onPress={() => { setForm(EMPTY); setEditId(null); setSheet(true); }} testID="add-location-button"><Feather name="plus" size={22} color={colors.brandPrimary} /></Pressable> : null} />
      {loading ? <Loading /> : (
        <ScrollView contentContainerStyle={{ padding: spacing.lg, paddingBottom: insets.bottom + spacing.xl }} showsVerticalScrollIndicator={false}>
          {items.map((s) => (
            <Pressable key={s.id} onPress={() => isAdmin && (setForm(s), setEditId(s.id), setSheet(true))} style={styles.card} testID={`location-${s.id}`}>
              <View style={styles.head}>
                <Feather name="map-pin" size={16} color={colors.brandPrimary} />
                <Text style={styles.name}>{s.nome}</Text>
                {isAdmin && <Feather name="edit-2" size={15} color={colors.onSurfaceTertiary} />}
              </View>
              <Info icon="navigation" text={s.indirizzo} />
              <Info icon="phone" text={s.telefono} />
              <Info icon="clock" text={s.orari} />
              {!!s.info && <Info icon="info" text={s.info} />}
            </Pressable>
          ))}
        </ScrollView>
      )}
      <Sheet visible={sheet} onClose={() => setSheet(false)} title={editId ? "Modifica sede" : "Nuova sede"}>
        <Field label="Nome" value={form.nome} onChange={(v) => setForm({ ...form, nome: v })} />
        <Field label="Indirizzo" value={form.indirizzo} onChange={(v) => setForm({ ...form, indirizzo: v })} />
        <Field label="Telefono" value={form.telefono} onChange={(v) => setForm({ ...form, telefono: v })} />
        <Field label="Orari" value={form.orari} onChange={(v) => setForm({ ...form, orari: v })} />
        <Field label="Informazioni" value={form.info} onChange={(v) => setForm({ ...form, info: v })} multi />
        <GoldButton title="Salva" icon="save" onPress={save} testID="save-location-button" />
      </Sheet>
    </View>
  );
}

function Info({ icon, text }: { icon: any; text?: string }) {
  if (!text) return null;
  return (
    <View style={styles.info}>
      <Feather name={icon} size={13} color={colors.onSurfaceTertiary} />
      <Text style={styles.infoText}>{text}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  card: { backgroundColor: colors.surfaceSecondary, borderRadius: radius.md, borderWidth: 1, borderColor: colors.border, padding: spacing.lg, marginBottom: spacing.md, gap: spacing.sm },
  head: { flexDirection: "row", alignItems: "center", gap: spacing.sm },
  name: { color: colors.onSurface, fontSize: type.lg, fontWeight: "700", flex: 1 },
  info: { flexDirection: "row", alignItems: "center", gap: spacing.sm },
  infoText: { color: colors.onSurfaceSecondary, fontSize: 13, flex: 1 },
});
