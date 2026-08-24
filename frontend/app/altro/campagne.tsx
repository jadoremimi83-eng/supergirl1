import React, { useCallback, useState } from "react";
import { View, Text, StyleSheet, ScrollView } from "react-native";
import { useFocusEffect } from "expo-router";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { Feather } from "@expo/vector-icons";
import { api } from "@/src/api";
import { colors, spacing, radius, type } from "@/src/theme";
import { SubHeader } from "@/src/components/SubHeader";
import { Loading } from "@/src/components/ui";

export default function Campagne() {
  const insets = useSafeAreaInsets();
  const [items, setItems] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    try { setItems(await api.get("/campaigns")); } catch {}
    setLoading(false);
  }, []);
  useFocusEffect(useCallback(() => { load(); }, [load]));

  return (
    <View style={{ flex: 1, backgroundColor: colors.surface }}>
      <SubHeader title="Campagne Meta" />
      {loading ? <Loading /> : (
        <ScrollView contentContainerStyle={{ padding: spacing.lg, paddingBottom: insets.bottom + spacing.xl }} showsVerticalScrollIndicator={false}>
          {items.map((c) => (
            <View key={c.id} style={styles.card} testID={`campaign-${c.id}`}>
              <View style={styles.head}>
                <View style={styles.iconBox}><Feather name="target" size={18} color={colors.brandPrimary} /></View>
                <View style={{ flex: 1 }}>
                  <Text style={styles.name}>{c.nome}</Text>
                  <Text style={styles.svc}>{c.servizio}</Text>
                </View>
                <View style={styles.leadBadge}>
                  <Text style={styles.leadNum}>{c.lead_count}</Text>
                  <Text style={styles.leadLbl}>lead</Text>
                </View>
              </View>
              <Text style={styles.insLabel}>INSERZIONI / CREATIVITÀ</Text>
              {c.inserzioni.map((i: string) => (
                <View key={i} style={styles.insRow}>
                  <Feather name="image" size={13} color={colors.onSurfaceTertiary} />
                  <Text style={styles.insText}>{i}</Text>
                </View>
              ))}
            </View>
          ))}
        </ScrollView>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  card: { backgroundColor: colors.surfaceSecondary, borderRadius: radius.md, borderWidth: 1, borderColor: colors.border, padding: spacing.lg, marginBottom: spacing.md },
  head: { flexDirection: "row", alignItems: "center", gap: spacing.md },
  iconBox: { width: 42, height: 42, borderRadius: radius.sm, backgroundColor: colors.brandTertiary, alignItems: "center", justifyContent: "center" },
  name: { color: colors.onSurface, fontSize: type.lg, fontWeight: "700" },
  svc: { color: colors.onSurfaceTertiary, fontSize: 12, marginTop: 1 },
  leadBadge: { alignItems: "center", backgroundColor: colors.brandTertiary, borderRadius: radius.sm, paddingHorizontal: spacing.md, paddingVertical: 6 },
  leadNum: { color: colors.brandPrimary, fontSize: 18, fontWeight: "800" },
  leadLbl: { color: colors.onBrandTertiary, fontSize: 10 },
  insLabel: { color: colors.onSurfaceTertiary, fontSize: 10, fontWeight: "800", letterSpacing: 1, marginTop: spacing.md, marginBottom: spacing.sm },
  insRow: { flexDirection: "row", alignItems: "center", gap: spacing.sm, paddingVertical: 4 },
  insText: { color: colors.onSurfaceSecondary, fontSize: 13 },
});
