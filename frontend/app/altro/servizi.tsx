import React, { useCallback, useState } from "react";
import { View, Text, StyleSheet, ScrollView, Pressable, TextInput } from "react-native";
import { useFocusEffect } from "expo-router";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { Feather } from "@expo/vector-icons";
import { api } from "@/src/api";
import { useAuth } from "@/src/auth";
import { colors, spacing, radius, type } from "@/src/theme";
import { SubHeader } from "@/src/components/SubHeader";
import { Loading, Sheet, GoldButton } from "@/src/components/ui";

const EMPTY = { nome: "", descrizione: "", prezzo: "", promozione: "", info: "", faq: "" };

export default function Servizi() {
  const insets = useSafeAreaInsets();
  const { user } = useAuth();
  const isAdmin = user?.role === "admin";
  const [items, setItems] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [sheet, setSheet] = useState(false);
  const [form, setForm] = useState<any>(EMPTY);
  const [editId, setEditId] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setItems(await api.get("/services"));
    } catch {}
    setLoading(false);
  }, []);

  useFocusEffect(useCallback(() => { load(); }, [load]));

  const openNew = () => { setForm(EMPTY); setEditId(null); setSheet(true); };
  const openEdit = (s: any) => { setForm(s); setEditId(s.id); setSheet(true); };

  const save = async () => {
    if (!form.nome.trim()) return;
    const payload = { nome: form.nome, descrizione: form.descrizione, prezzo: form.prezzo, promozione: form.promozione, info: form.info, faq: form.faq };
    if (editId) await api.patch(`/services/${editId}`, payload);
    else await api.post("/services", payload);
    setSheet(false);
    load();
  };

  return (
    <View style={{ flex: 1, backgroundColor: colors.surface }}>
      <SubHeader
        title="Servizi"
        right={isAdmin ? <Pressable onPress={openNew} testID="add-service-button"><Feather name="plus" size={22} color={colors.brandPrimary} /></Pressable> : null}
      />
      {loading ? <Loading /> : (
        <ScrollView contentContainerStyle={{ padding: spacing.lg, paddingBottom: insets.bottom + spacing.xl }} showsVerticalScrollIndicator={false}>
          {items.map((s) => (
            <Pressable key={s.id} onPress={() => isAdmin && openEdit(s)} style={styles.card} testID={`service-${s.id}`}>
              <View style={styles.cardHead}>
                <Text style={styles.name}>{s.nome}</Text>
                {isAdmin && <Feather name="edit-2" size={15} color={colors.onSurfaceTertiary} />}
              </View>
              {!!s.descrizione && <Text style={styles.desc}>{s.descrizione}</Text>}
              {!!s.prezzo && <View style={styles.chipRow}><Feather name="tag" size={12} color={colors.brandPrimary} /><Text style={styles.price}>{s.prezzo}</Text></View>}
              {!!s.promozione && <View style={styles.promo}><Text style={styles.promoText}>{s.promozione}</Text></View>}
              {!!s.faq && <Text style={styles.faq}>FAQ: {s.faq}</Text>}
            </Pressable>
          ))}
        </ScrollView>
      )}

      <Sheet visible={sheet} onClose={() => setSheet(false)} title={editId ? "Modifica servizio" : "Nuovo servizio"}>
        <Field label="Nome" value={form.nome} onChange={(v) => setForm({ ...form, nome: v })} />
        <Field label="Descrizione" value={form.descrizione} onChange={(v) => setForm({ ...form, descrizione: v })} multi />
        <Field label="Prezzo" value={form.prezzo} onChange={(v) => setForm({ ...form, prezzo: v })} />
        <Field label="Promozione" value={form.promozione} onChange={(v) => setForm({ ...form, promozione: v })} />
        <Field label="Informazioni" value={form.info} onChange={(v) => setForm({ ...form, info: v })} multi />
        <Field label="FAQ" value={form.faq} onChange={(v) => setForm({ ...form, faq: v })} multi />
        <GoldButton title="Salva" icon="save" onPress={save} testID="save-service-button" />
      </Sheet>
    </View>
  );
}

export function Field({ label, value, onChange, multi }: { label: string; value: string; onChange: (v: string) => void; multi?: boolean }) {
  return (
    <View style={{ marginBottom: spacing.md }}>
      <Text style={styles.label}>{label}</Text>
      <TextInput
        value={value}
        onChangeText={onChange}
        style={[styles.input, multi && { minHeight: 70, textAlignVertical: "top" }]}
        multiline={multi}
        placeholderTextColor={colors.onSurfaceTertiary}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  card: { backgroundColor: colors.surfaceSecondary, borderRadius: radius.md, borderWidth: 1, borderColor: colors.border, padding: spacing.lg, marginBottom: spacing.md, gap: 6 },
  cardHead: { flexDirection: "row", alignItems: "center", justifyContent: "space-between" },
  name: { color: colors.onSurface, fontSize: type.lg, fontWeight: "700" },
  desc: { color: colors.onSurfaceSecondary, fontSize: 13, lineHeight: 19 },
  chipRow: { flexDirection: "row", alignItems: "center", gap: 6 },
  price: { color: colors.brandPrimary, fontSize: 13, fontWeight: "700" },
  promo: { backgroundColor: colors.brandTertiary, alignSelf: "flex-start", paddingHorizontal: 10, paddingVertical: 4, borderRadius: radius.pill },
  promoText: { color: colors.onBrandTertiary, fontSize: 12, fontWeight: "700" },
  faq: { color: colors.onSurfaceTertiary, fontSize: 12, fontStyle: "italic" },
  label: { color: colors.onSurfaceSecondary, fontSize: 12, fontWeight: "700", marginBottom: 6 },
  input: { color: colors.onSurface, fontSize: type.base, backgroundColor: colors.surface, borderRadius: radius.sm, borderWidth: 1, borderColor: colors.border, padding: spacing.md },
});
