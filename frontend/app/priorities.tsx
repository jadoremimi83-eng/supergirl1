import React, { useCallback, useState } from "react";
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  Pressable,
  RefreshControl,
} from "react-native";
import { useRouter, useFocusEffect } from "expo-router";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { LinearGradient } from "expo-linear-gradient";
import { Feather } from "@expo/vector-icons";
import { api } from "@/src/api";
import { useAuth } from "@/src/auth";
import { colors, spacing, radius, type, font, tempOf } from "@/src/theme";
import { Avatar, TempBadge, Loading, EmptyState } from "@/src/components/ui";
import { useAssistant } from "@/src/useAssistant";
import { waitingSince } from "@/src/time";

type Priority = {
  id: string;
  nome: string;
  cognome: string;
  telefono: string;
  servizio?: string;
  sede?: string;
  temperature?: string;
  waiting_since?: string;
  foto_profilo?: string | null;
  ig_username?: string | null;
  piattaforma?: string | null;
  campagna?: string | null;
  conversation_id?: string | null;
};

export default function Priorities() {
  const insets = useSafeAreaInsets();
  const router = useRouter();
  const { user } = useAuth();
  const { assistant } = useAssistant();
  const [data, setData] = useState<{ da_fissare: Priority[]; total_leads: number; count: number } | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const load = useCallback(async () => {
    try {
      const res = await api.get("/home/priorities");
      setData(res);
    } catch {}
    setLoading(false);
    setRefreshing(false);
  }, []);

  useFocusEffect(
    useCallback(() => {
      load();
    }, [load])
  );

  return (
    <View style={{ flex: 1, backgroundColor: colors.surface }}>
      <LinearGradient
        colors={["#1F1A10", "#141210", "#0A0A0A"]}
        style={[styles.hero, { paddingTop: insets.top + spacing.lg }]}
      >
        <View style={styles.heroTop}>
          <View style={styles.brandBlock}>
            <Avatar uri={assistant.avatarUri} name={assistant.name} size={46} position="top" />
            <View>
              <Text style={styles.brand}>SUPER GIRL</Text>
              <Text style={styles.hello}>Ciao, {user?.name?.split(" ")[0] || "benvenuta"}</Text>
            </View>
          </View>
          <Pressable
            testID="go-dashboard-button"
            onPress={() => router.replace("/(tabs)/chat")}
            style={styles.enterBtn}
          >
            <Feather name="grid" size={18} color={colors.onBrandPrimary} />
          </Pressable>
        </View>
        <View style={styles.statsRow}>
          <Stat label="Lead totali" value={data?.total_leads ?? "—"} />
          <View style={styles.statDivider} />
          <Stat label="Da fissare adesso" value={data?.count ?? "—"} gold />
        </View>
      </LinearGradient>

      {loading ? (
        <Loading label="Carico le priorità…" />
      ) : (
        <ScrollView
          contentContainerStyle={{ padding: spacing.lg, paddingBottom: insets.bottom + spacing["2xl"] }}
          showsVerticalScrollIndicator={false}
          refreshControl={
            <RefreshControl
              refreshing={refreshing}
              onRefresh={() => {
                setRefreshing(true);
                load();
              }}
              tintColor={colors.brandPrimary}
            />
          }
        >
          <View style={styles.sectionHead}>
            <View style={styles.sectionDot} />
            <Text style={styles.sectionTitle}>DA FISSARE ADESSO</Text>
          </View>
          <Text style={styles.sectionSub}>
            Chi contattare subito — ordinato per priorità e attesa
          </Text>

          {!data?.da_fissare?.length ? (
            <View style={{ marginTop: spacing["2xl"] }}>
              <EmptyState
                icon="check-circle"
                title="Tutto sotto controllo"
                subtitle="Nessuna cliente in attesa di essere fissata."
              />
            </View>
          ) : (
            data.da_fissare.map((p, i) => (
              <Pressable
                key={p.id}
                testID={`priority-card-${p.id}`}
                onPress={() =>
                  p.conversation_id
                    ? router.push(`/conversation/${p.conversation_id}`)
                    : router.push(`/cliente/${p.id}`)
                }
                style={({ pressed }) => [styles.card, pressed && { opacity: 0.9 }]}
              >
                <View style={styles.rankWrap}>
                  <Text style={styles.rank}>{i + 1}</Text>
                </View>
                <Avatar uri={p.foto_profilo} name={`${p.nome} ${p.cognome}`} size={52} />
                <View style={{ flex: 1 }}>
                  <View style={styles.cardTopRow}>
                    <Text style={styles.name} numberOfLines={1}>
                      {p.nome} {p.cognome}
                    </Text>
                    <View style={styles.waitPill}>
                      <Feather name="clock" size={11} color={colors.onBrandTertiary} />
                      <Text style={styles.waitText}>{waitingSince(p.waiting_since)}</Text>
                    </View>
                  </View>
                  <Text style={styles.service} numberOfLines={1}>
                    {p.servizio} · {p.sede}
                  </Text>
                  <View style={styles.metaRow}>
                    <TempBadge temp={p.temperature} small />
                    <View style={styles.provRow}>
                      <Feather
                        name={p.piattaforma === "Facebook" ? "facebook" : "instagram"}
                        size={11}
                        color={colors.onSurfaceTertiary}
                      />
                      <Text style={styles.prov} numberOfLines={1}>
                        {p.ig_username || p.campagna || p.piattaforma}
                      </Text>
                    </View>
                  </View>
                </View>
                <Feather name="message-circle" size={20} color={colors.brandPrimary} />
              </Pressable>
            ))
          )}
        </ScrollView>
      )}
    </View>
  );
}

function Stat({ label, value, gold }: { label: string; value: any; gold?: boolean }) {
  return (
    <View style={{ flex: 1 }}>
      <Text style={[styles.statValue, gold && { color: colors.brandPrimary }]}>{value}</Text>
      <Text style={styles.statLabel}>{label}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  hero: {
    paddingHorizontal: spacing.lg,
    paddingBottom: spacing.xl,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
  },
  heroTop: { flexDirection: "row", alignItems: "center", justifyContent: "space-between" },
  brandBlock: { flexDirection: "row", alignItems: "center", gap: spacing.md },
  brand: {
    fontFamily: font.display,
    fontSize: 26,
    letterSpacing: 3,
    color: colors.onSurface,
    fontWeight: "700",
  },
  hello: { color: colors.brandSecondary, fontSize: 13, marginTop: 2 },
  enterBtn: {
    width: 44,
    height: 44,
    borderRadius: 22,
    backgroundColor: colors.brandPrimary,
    alignItems: "center",
    justifyContent: "center",
  },
  statsRow: {
    flexDirection: "row",
    alignItems: "center",
    marginTop: spacing.xl,
    backgroundColor: "rgba(255,255,255,0.03)",
    borderRadius: radius.md,
    borderWidth: 1,
    borderColor: colors.border,
    padding: spacing.lg,
  },
  statDivider: { width: 1, height: 36, backgroundColor: colors.border, marginHorizontal: spacing.md },
  statValue: { color: colors.onSurface, fontSize: 28, fontWeight: "800", fontFamily: font.display },
  statLabel: { color: colors.onSurfaceTertiary, fontSize: 11, marginTop: 2, letterSpacing: 0.3 },
  sectionHead: { flexDirection: "row", alignItems: "center", gap: spacing.sm },
  sectionDot: { width: 8, height: 8, borderRadius: 4, backgroundColor: colors.brandPrimary },
  sectionTitle: { color: colors.onSurface, fontSize: type.lg, fontWeight: "800", letterSpacing: 1 },
  sectionSub: { color: colors.onSurfaceTertiary, fontSize: 12, marginTop: 2, marginBottom: spacing.lg },
  card: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.md,
    backgroundColor: colors.brandTertiary,
    borderRadius: radius.md,
    borderWidth: 1,
    borderColor: colors.borderStrong,
    padding: spacing.md,
    marginBottom: spacing.md,
  },
  rankWrap: {
    width: 22,
    height: 22,
    borderRadius: 11,
    backgroundColor: colors.brandPrimary,
    alignItems: "center",
    justifyContent: "center",
  },
  rank: { color: colors.onBrandPrimary, fontSize: 12, fontWeight: "800" },
  cardTopRow: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", gap: spacing.sm },
  name: { color: colors.onSurface, fontSize: type.lg, fontWeight: "700", flex: 1 },
  waitPill: {
    flexDirection: "row",
    alignItems: "center",
    gap: 3,
    backgroundColor: "rgba(0,0,0,0.35)",
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: radius.pill,
  },
  waitText: { color: colors.onBrandTertiary, fontSize: 11, fontWeight: "700" },
  service: { color: colors.onSurfaceSecondary, fontSize: 13, marginTop: 2 },
  metaRow: { flexDirection: "row", alignItems: "center", gap: spacing.sm, marginTop: spacing.sm },
  provRow: { flexDirection: "row", alignItems: "center", gap: 4, flex: 1 },
  prov: { color: colors.onSurfaceTertiary, fontSize: 11, flex: 1 },
});
