import React, { useCallback, useState } from "react";
import { View, Text, StyleSheet, Pressable } from "react-native";
import { useFocusEffect } from "expo-router";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { Feather } from "@expo/vector-icons";
import * as Haptics from "expo-haptics";
import { KeyboardAwareScrollView } from "react-native-keyboard-controller";
import { api } from "@/src/api";
import { useAuth } from "@/src/auth";
import { colors, spacing, radius, type } from "@/src/theme";
import { SubHeader } from "@/src/components/SubHeader";
import { Loading } from "@/src/components/ui";
import { Field } from "./servizi";

const FIELDS: { key: string; label: string }[] = [
  { key: "azienda", label: "Informazioni azienda" },
  { key: "servizi", label: "Servizi" },
  { key: "prezzi", label: "Prezzi" },
  { key: "promozioni", label: "Promozioni" },
  { key: "sedi", label: "Sedi" },
  { key: "orari", label: "Orari" },
  { key: "faq", label: "FAQ" },
  { key: "obiezioni", label: "Risposte alle obiezioni" },
  { key: "pagamenti", label: "Modalità di pagamento" },
  { key: "tono_di_voce", label: "Tono di voce" },
  { key: "info_commerciali", label: "Informazioni commerciali" },
  { key: "istruzioni", label: "Istruzioni particolari" },
  { key: "non_comunicare", label: "Informazioni da NON comunicare" },
];

export default function ConoscenzaAI() {
  const insets = useSafeAreaInsets();
  const { user } = useAuth();
  const isAdmin = user?.role === "admin";
  const [kb, setKb] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [saved, setSaved] = useState(false);

  const load = useCallback(async () => {
    try { setKb(await api.get("/knowledge-base")); } catch {}
    setLoading(false);
  }, []);
  useFocusEffect(useCallback(() => { load(); }, [load]));

  const save = async () => {
    const payload: any = {};
    FIELDS.forEach((f) => (payload[f.key] = kb[f.key] || ""));
    await api.patch("/knowledge-base", payload);
    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
    setSaved(true);
    setTimeout(() => setSaved(false), 1800);
  };

  if (loading || !kb) {
    return <View style={{ flex: 1, backgroundColor: colors.surface }}><SubHeader title="Conoscenza AI" /><Loading /></View>;
  }

  return (
    <View style={{ flex: 1, backgroundColor: colors.surface }}>
      <SubHeader
        title="Conoscenza AI"
        right={isAdmin ? <Pressable onPress={save} testID="save-kb-button"><Feather name={saved ? "check" : "save"} size={22} color={colors.brandPrimary} /></Pressable> : null}
      />
      <KeyboardAwareScrollView
        contentContainerStyle={{ padding: spacing.lg, paddingBottom: insets.bottom + spacing["2xl"] }}
        bottomOffset={24}
        showsVerticalScrollIndicator={false}
      >
        <View style={styles.rule}>
          <Feather name="alert-circle" size={16} color={colors.onWarning} />
          <Text style={styles.ruleText}>
            Regola fondamentale: l'AI non deve inventare informazioni. Se non conosce una risposta,
            farà intervenire lo staff.
          </Text>
        </View>
        {FIELDS.map((f) => (
          <Field
            key={f.key}
            label={f.label}
            value={kb[f.key] || ""}
            onChange={(v) => isAdmin && setKb({ ...kb, [f.key]: v })}
            multi
          />
        ))}
        {!isAdmin && <Text style={styles.readonly}>Solo gli Admin possono modificare la Knowledge Base.</Text>}
      </KeyboardAwareScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  rule: { flexDirection: "row", gap: spacing.sm, backgroundColor: colors.warning, borderRadius: radius.sm, padding: spacing.md, marginBottom: spacing.lg },
  ruleText: { color: colors.onWarning, fontSize: 12.5, flex: 1, lineHeight: 18, fontWeight: "600" },
  readonly: { color: colors.onSurfaceTertiary, fontSize: 12, fontStyle: "italic", textAlign: "center" },
});
