import React, { useCallback, useState } from "react";
import { View, Text, StyleSheet, ScrollView, Pressable, RefreshControl } from "react-native";
import { useFocusEffect, useRouter } from "expo-router";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { Feather } from "@expo/vector-icons";
import { api } from "@/src/api";
import { colors, spacing, radius, type } from "@/src/theme";
import { SubHeader } from "@/src/components/SubHeader";
import { Loading } from "@/src/components/ui";

const ROME_FMT = new Intl.DateTimeFormat("it-IT", {
  timeZone: "Europe/Rome", weekday: "long", day: "2-digit", month: "2-digit",
  hour: "2-digit", minute: "2-digit",
});
const ROME_TIME = new Intl.DateTimeFormat("it-IT", {
  timeZone: "Europe/Rome", hour: "2-digit", minute: "2-digit",
});

function fmtSlot(iso: string) {
  // Sempre orario italiano (Europe/Rome), indipendente dal browser
  return ROME_FMT.format(new Date(iso)).replace(",", " ·");
}

export default function ChiamateCorsi() {
  const insets = useSafeAreaInsets();
  const router = useRouter();
  const [items, setItems] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    try { setItems(await api.get("/call-slots")); } catch {}
    setLoading(false);
  }, []);
  useFocusEffect(useCallback(() => { load(); }, [load]));

  const setStatus = async (id: string, status: string) => {
    await api.patch(`/call-slots/${id}`, { status });
    load();
  };

  const imminent = items.filter((s) => s.imminent);

  return (
    <View style={{ flex: 1, backgroundColor: colors.surface }}>
      <SubHeader title="Chiamate Corsi fissate" />
      {loading ? <Loading /> : (
        <ScrollView
          contentContainerStyle={{ padding: spacing.lg, paddingBottom: insets.bottom + spacing.xl }}
          showsVerticalScrollIndicator={false}
          refreshControl={<RefreshControl refreshing={false} onRefresh={load} tintColor={colors.brandPrimary} />}
        >
          {imminent.length > 0 && (
            <View style={styles.alertBox}>
              <Feather name="bell" size={16} color={colors.onBrandPrimary} />
              <Text style={styles.alertText}>
                {imminent.length === 1
                  ? `Tra poco: chiamata con ${imminent[0].nome} ${imminent[0].cognome || ""} alle ${ROME_TIME.format(new Date(imminent[0].start))}`
                  : `${imminent.length} chiamate nella prossima ora`}
              </Text>
            </View>
          )}

          {items.length === 0 && (
            <Text style={styles.empty}>Nessuna chiamata corso fissata. Quando Andrea (Academy Manager) fissa una chiamata, comparirà qui.</Text>
          )}

          {items.map((s) => (
            <View key={s.id} style={[styles.card, s.imminent && styles.cardImminent]} testID={`slot-${s.id}`}>
              <View style={styles.timeBox}>
                <Feather name="phone-call" size={16} color={s.imminent ? colors.onBrandPrimary : colors.brandPrimary} />
              </View>
              <View style={{ flex: 1 }}>
                <Text style={styles.name}>{s.nome} {s.cognome}</Text>
                <Text style={styles.slot}>{fmtSlot(s.start)}</Text>
                {!!s.servizio && <Text style={styles.svc}>{s.servizio}{s.sede ? ` · ${s.sede}` : ""}</Text>}
                {s.starts_in_minutes >= 0 && s.starts_in_minutes <= 240 && (
                  <Text style={styles.inMin}>tra {s.starts_in_minutes} min</Text>
                )}
              </View>
              <View style={{ gap: spacing.sm }}>
                {s.conversation_id && (
                  <Pressable onPress={() => router.push(`/conversation/${s.conversation_id}`)} style={styles.iconBtn}>
                    <Feather name="message-circle" size={16} color={colors.brandPrimary} />
                  </Pressable>
                )}
                <Pressable onPress={() => setStatus(s.id, "completata")} style={styles.iconBtn}>
                  <Feather name="check" size={16} color={colors.onSuccess} />
                </Pressable>
                <Pressable onPress={() => setStatus(s.id, "annullata")} style={styles.iconBtn}>
                  <Feather name="x" size={16} color={colors.onSurfaceTertiary} />
                </Pressable>
              </View>
            </View>
          ))}
        </ScrollView>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  alertBox: { flexDirection: "row", alignItems: "center", gap: spacing.sm, backgroundColor: colors.brandPrimary, borderRadius: radius.md, padding: spacing.md, marginBottom: spacing.lg },
  alertText: { flex: 1, color: colors.onBrandPrimary, fontSize: 13.5, fontWeight: "700" },
  empty: { color: colors.onSurfaceTertiary, fontSize: 14, lineHeight: 20, textAlign: "center", marginTop: spacing["2xl"] },
  card: { flexDirection: "row", alignItems: "center", gap: spacing.md, backgroundColor: colors.surfaceSecondary, borderRadius: radius.md, borderWidth: 1, borderColor: colors.border, padding: spacing.lg, marginBottom: spacing.md },
  cardImminent: { borderColor: colors.brandPrimary, borderWidth: 2 },
  timeBox: { width: 42, height: 42, borderRadius: radius.sm, backgroundColor: colors.brandTertiary, alignItems: "center", justifyContent: "center" },
  name: { color: colors.onSurface, fontSize: type.lg, fontWeight: "700" },
  slot: { color: colors.brandPrimary, fontSize: 14, fontWeight: "700", marginTop: 2 },
  svc: { color: colors.onSurfaceTertiary, fontSize: 12.5, marginTop: 2 },
  inMin: { color: colors.brandSecondary, fontSize: 11.5, fontWeight: "700", marginTop: 3 },
  iconBtn: { width: 34, height: 34, borderRadius: radius.sm, borderWidth: 1, borderColor: colors.border, alignItems: "center", justifyContent: "center", backgroundColor: colors.surface },
});
