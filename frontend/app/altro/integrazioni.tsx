import React, { useCallback, useState } from "react";
import { View, Text, StyleSheet, ScrollView, Pressable } from "react-native";
import { useFocusEffect, useRouter } from "expo-router";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { Feather } from "@expo/vector-icons";
import { api } from "@/src/api";
import { colors, spacing, radius, type } from "@/src/theme";
import { SubHeader } from "@/src/components/SubHeader";
import { Loading } from "@/src/components/ui";

const META = {
  meta: { icon: "facebook", desc: "Ricezione automatica dei lead dai moduli Meta Lead Ads.", route: "/altro/meta" },
  whatsapp: { icon: "message-circle", desc: "Numero, credenziali e template. Sostituibile dalle impostazioni.", route: "/altro/whatsapp" },
  ai: { icon: "cpu", desc: "AI commerciale reale (GPT-5.4) attiva sulle conversazioni." },
};

export default function Integrazioni() {
  const insets = useSafeAreaInsets();
  const router = useRouter();
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    try { setData(await api.get("/integrations")); } catch {}
    setLoading(false);
  }, []);
  useFocusEffect(useCallback(() => { load(); }, [load]));

  if (loading || !data) return <View style={{ flex: 1, backgroundColor: colors.surface }}><SubHeader title="Integrazioni" /><Loading /></View>;

  return (
    <View style={{ flex: 1, backgroundColor: colors.surface }}>
      <SubHeader title="Integrazioni" />
      <ScrollView contentContainerStyle={{ padding: spacing.lg, paddingBottom: insets.bottom + spacing.xl }} showsVerticalScrollIndicator={false}>
        <View style={styles.notice}>
          <Feather name="info" size={16} color={colors.onInfo} />
          <Text style={styles.noticeText}>
            Meta Lead Ads è predisposta (Fase 2): puoi già testare il flusso con il Simulatore.
            WhatsApp e AI reale arrivano nelle Fasi 3 e 4.
          </Text>
        </View>
        {["meta", "whatsapp", "ai"].map((k) => {
          const it = data[k];
          const m = (META as any)[k];
          const configured = it.configured;
          const tappable = !!m.route;
          const Wrapper: any = tappable ? Pressable : View;
          return (
            <Wrapper
              key={k}
              style={[styles.card, k === "meta" && styles.cardMeta]}
              testID={`integration-${k}`}
              onPress={tappable ? () => router.push(m.route) : undefined}
            >
              <View style={styles.iconBox}><Feather name={m.icon} size={20} color={colors.brandSecondary} /></View>
              <View style={{ flex: 1 }}>
                <Text style={styles.name}>{it.name}</Text>
                <Text style={styles.desc}>{m.desc}</Text>
              </View>
              <View style={styles.statusCol}>
                <View style={[styles.statusPill, configured && { backgroundColor: colors.success }]}>
                  <Text style={[styles.statusText, configured && { color: colors.onSuccess }]}>
                    {configured ? "ATTIVA" : "NON ATTIVO"}
                  </Text>
                </View>
                {tappable ? <Text style={styles.manage}>Configura ›</Text> : <Text style={styles.phase}>{it.phase}</Text>}
              </View>
            </Wrapper>
          );
        })}
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  notice: { flexDirection: "row", gap: spacing.sm, backgroundColor: colors.info, borderRadius: radius.sm, padding: spacing.md, marginBottom: spacing.lg },
  noticeText: { color: colors.onInfo, fontSize: 12.5, flex: 1, lineHeight: 18 },
  card: { flexDirection: "row", alignItems: "center", gap: spacing.md, backgroundColor: colors.surfaceSecondary, borderRadius: radius.md, borderWidth: 1, borderColor: colors.border, padding: spacing.lg, marginBottom: spacing.md },
  cardMeta: { borderColor: colors.borderStrong },
  iconBox: { width: 44, height: 44, borderRadius: radius.sm, backgroundColor: colors.surfaceTertiary, alignItems: "center", justifyContent: "center" },
  name: { color: colors.onSurface, fontSize: 15, fontWeight: "700" },
  desc: { color: colors.onSurfaceTertiary, fontSize: 12, marginTop: 2, lineHeight: 17 },
  statusCol: { alignItems: "flex-end", gap: 4 },
  statusPill: { backgroundColor: colors.surfaceTertiary, paddingHorizontal: 8, paddingVertical: 4, borderRadius: radius.pill },
  statusText: { color: colors.onSurfaceTertiary, fontSize: 9, fontWeight: "800", letterSpacing: 0.5 },
  phase: { color: colors.brandSecondary, fontSize: 10, fontWeight: "700" },
  manage: { color: colors.brandPrimary, fontSize: 11, fontWeight: "700" },
});
