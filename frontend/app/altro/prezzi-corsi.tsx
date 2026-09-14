import React, { useCallback, useState } from "react";
import { View, Text, StyleSheet, TextInput } from "react-native";
import { KeyboardAwareScrollView } from "react-native-keyboard-controller";
import { useFocusEffect } from "expo-router";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { Feather } from "@expo/vector-icons";
import * as Haptics from "expo-haptics";
import { api } from "@/src/api";
import { colors, spacing, radius, type } from "@/src/theme";
import { SubHeader } from "@/src/components/SubHeader";
import { Loading, GoldButton } from "@/src/components/ui";

export default function PrezziCorsi() {
  const insets = useSafeAreaInsets();
  const [prezzi, setPrezzi] = useState("");
  const [loading, setLoading] = useState(true);
  const [saved, setSaved] = useState(false);

  const load = useCallback(async () => {
    try { const r = await api.get("/course-prices"); setPrezzi(r.prezzi || ""); } catch {}
    setLoading(false);
  }, []);
  useFocusEffect(useCallback(() => { load(); }, [load]));

  const save = async () => {
    await api.patch("/course-prices", { prezzi });
    setSaved(true);
    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
    setTimeout(() => setSaved(false), 1800);
  };

  if (loading) return <View style={{ flex: 1, backgroundColor: colors.surface }}><SubHeader title="Prezzi Corsi" /><Loading /></View>;

  return (
    <View style={{ flex: 1, backgroundColor: colors.surface }}>
      <SubHeader title="Prezzi Corsi" />
      <KeyboardAwareScrollView
        contentContainerStyle={{ padding: spacing.lg, paddingBottom: insets.bottom + spacing["2xl"] }}
        bottomOffset={20}
        showsVerticalScrollIndicator={false}
      >
        <View style={styles.infoBox}>
          <Feather name="info" size={15} color={colors.brandPrimary} />
          <Text style={styles.infoText}>
            Listino interno dei corsi. Andrea NON lo comunica al primo messaggio: lo usa solo se la cliente
            chiede esplicitamente il prezzo, riportando comunque il discorso al fissare la chiamata.
          </Text>
        </View>

        <Text style={styles.label}>PREZZI CORSI (uso interno)</Text>
        <TextInput
          testID="course-prices-input"
          value={prezzi}
          onChangeText={setPrezzi}
          placeholder={"Es.\nCorso Base Massaggio: 890€\nCorso Avanzato Estetica: 1490€ (rateizzabile)"}
          placeholderTextColor={colors.onSurfaceTertiary}
          style={styles.input}
          multiline
        />
        <GoldButton
          title={saved ? "Salvato ✓" : "Salva prezzi"}
          icon={saved ? "check" : "save"}
          onPress={save}
          testID="save-course-prices"
        />
      </KeyboardAwareScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  infoBox: { flexDirection: "row", gap: spacing.sm, backgroundColor: colors.brandTertiary, borderRadius: radius.md, borderWidth: 1, borderColor: colors.borderStrong, padding: spacing.md, marginBottom: spacing.lg },
  infoText: { flex: 1, color: colors.onBrandTertiary, fontSize: 12.5, lineHeight: 18 },
  label: { color: colors.onSurfaceTertiary, fontSize: 11, fontWeight: "800", letterSpacing: 1, marginBottom: spacing.sm },
  input: { color: colors.onSurface, fontSize: type.base, backgroundColor: colors.surfaceSecondary, borderRadius: radius.sm, borderWidth: 1, borderColor: colors.border, padding: spacing.md, minHeight: 160, textAlignVertical: "top", marginBottom: spacing.lg },
});
