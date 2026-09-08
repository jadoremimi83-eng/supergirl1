import React, { useCallback, useState } from "react";
import { View, Text, StyleSheet, ScrollView, Pressable, RefreshControl } from "react-native";
import { useRouter, useFocusEffect } from "expo-router";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { Feather } from "@expo/vector-icons";
import * as Haptics from "expo-haptics";
import { api } from "@/src/api";
import { colors, spacing, radius, type, STAGES } from "@/src/theme";
import { Avatar, TempBadge, Loading, Sheet } from "@/src/components/ui";
import { AppHeader } from "@/src/components/AppHeader";
import { waitingSince } from "@/src/time";

export default function Pipeline() {
  const insets = useSafeAreaInsets();
  const router = useRouter();
  const [stages, setStages] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [expanded, setExpanded] = useState<Record<string, boolean>>({ attesa_chiamata: true, da_fissare: true, nuovo_lead: true });
  const [moveLead, setMoveLead] = useState<any>(null);

  const load = useCallback(async () => {
    try {
      const res = await api.get("/pipeline");
      setStages(res);
    } catch {}
    setLoading(false);
    setRefreshing(false);
  }, []);

  useFocusEffect(
    useCallback(() => {
      load();
    }, [load])
  );

  const toggle = (k: string) => setExpanded((e) => ({ ...e, [k]: !e[k] }));

  const changeStage = async (stato: string) => {
    const lead = moveLead;
    setMoveLead(null);
    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium);
    await api.post(`/leads/${lead.id}/status`, { stato });
    load();
  };

  return (
    <View style={{ flex: 1, backgroundColor: colors.surface }}>
      <AppHeader title="Pipeline" subtitle="Percorso commerciale" />
      {loading ? (
        <Loading />
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
          {stages.map((stage) => {
            const meta = STAGES[stage.key];
            const open = !!expanded[stage.key];
            const isFissare = stage.key === "da_fissare" || stage.key === "attesa_chiamata";
            return (
              <View
                key={stage.key}
                style={[styles.stage, isFissare && styles.stageFissare]}
                testID={`pipeline-stage-${stage.key}`}
              >
                <Pressable style={styles.stageHead} onPress={() => toggle(stage.key)}>
                  <View style={[styles.accent, { backgroundColor: meta.accent }]} />
                  <View style={{ flex: 1 }}>
                    <View style={styles.stageTitleRow}>
                      {isFissare && <Feather name="star" size={14} color={colors.brandPrimary} />}
                      <Text style={[styles.stageTitle, isFissare && { color: colors.brandPrimary }]} numberOfLines={1}>
                        {meta.label}
                      </Text>
                    </View>
                    <Text style={styles.stageDesc} numberOfLines={1}>
                      {stage.desc}
                    </Text>
                  </View>
                  <View style={[styles.countBadge, isFissare && { backgroundColor: colors.brandPrimary }]}>
                    <Text style={[styles.countText, isFissare && { color: colors.onBrandPrimary }]}>{stage.count}</Text>
                  </View>
                  <Feather name={open ? "chevron-up" : "chevron-down"} size={20} color={colors.onSurfaceTertiary} />
                </Pressable>

                {open && (
                  <View style={styles.leadList}>
                    {stage.leads.length === 0 ? (
                      <Text style={styles.emptyStage}>Nessun lead in questa fase</Text>
                    ) : (
                      stage.leads.map((l: any) => (
                        <View key={l.id} style={styles.leadCard}>
                          <Pressable style={styles.leadInfo} onPress={() => router.push(`/cliente/${l.id}`)}>
                            <Avatar uri={l.foto_profilo} name={`${l.nome} ${l.cognome}`} size={40} />
                            <View style={{ flex: 1 }}>
                              <Text style={styles.leadName} numberOfLines={1}>
                                {l.nome} {l.cognome}
                              </Text>
                              <Text style={styles.leadMeta} numberOfLines={1}>
                                {l.servizio} · {l.sede}
                              </Text>
                              <View style={styles.leadBadges}>
                                <TempBadge temp={l.temperature} small />
                                {isFissare && (
                                  <View style={styles.waitTag}>
                                    <Feather name="clock" size={10} color={colors.onBrandTertiary} />
                                    <Text style={styles.waitText}>{waitingSince(l.handoff_at || l.ultimo_contatto)}</Text>
                                  </View>
                                )}
                              </View>
                            </View>
                          </Pressable>
                          <Pressable
                            style={styles.moveBtn}
                            onPress={() => setMoveLead(l)}
                            testID={`change-stage-${l.id}`}
                          >
                            <Feather name="git-branch" size={14} color={colors.brandPrimary} />
                            <Text style={styles.moveText}>Cambia Stato</Text>
                          </Pressable>
                        </View>
                      ))
                    )}
                  </View>
                )}
              </View>
            );
          })}
        </ScrollView>
      )}

      <Sheet visible={!!moveLead} onClose={() => setMoveLead(null)} title="Sposta in…">
        {Object.keys(STAGES).map((k) => {
          const s = STAGES[k];
          const active = moveLead && k === moveLead.stato_pipeline;
          return (
            <Pressable
              key={k}
              testID={`move-option-${k}`}
              onPress={() => changeStage(k)}
              style={[styles.optionRow, active && { borderColor: s.accent, backgroundColor: colors.brandTertiary }]}
            >
              <View style={[styles.optDot, { backgroundColor: s.accent }]} />
              <Text style={[styles.optText, active && { color: colors.onSurface, fontWeight: "700" }]}>{s.label}</Text>
              {active && <Feather name="check" size={18} color={s.accent} />}
            </Pressable>
          );
        })}
      </Sheet>
    </View>
  );
}

const styles = StyleSheet.create({
  stage: {
    backgroundColor: colors.surfaceSecondary,
    borderRadius: radius.md,
    borderWidth: 1,
    borderColor: colors.border,
    marginBottom: spacing.md,
    overflow: "hidden",
  },
  stageFissare: { borderColor: colors.brandPrimary, backgroundColor: colors.brandTertiary },
  stageHead: { flexDirection: "row", alignItems: "center", gap: spacing.sm, padding: spacing.md },
  accent: { width: 4, alignSelf: "stretch", borderRadius: 2 },
  stageTitleRow: { flexDirection: "row", alignItems: "center", gap: 6 },
  stageTitle: { color: colors.onSurface, fontSize: 13.5, fontWeight: "800", letterSpacing: 0.4, flex: 1 },
  stageDesc: { color: colors.onSurfaceTertiary, fontSize: 11, marginTop: 2 },
  countBadge: {
    minWidth: 26,
    height: 26,
    borderRadius: 13,
    backgroundColor: colors.surfaceTertiary,
    paddingHorizontal: 6,
    alignItems: "center",
    justifyContent: "center",
  },
  countText: { color: colors.onSurface, fontSize: 13, fontWeight: "800" },
  leadList: { paddingHorizontal: spacing.md, paddingBottom: spacing.md, gap: spacing.sm },
  emptyStage: { color: colors.onSurfaceTertiary, fontSize: 12, fontStyle: "italic", paddingVertical: spacing.sm },
  leadCard: {
    backgroundColor: colors.surface,
    borderRadius: radius.sm,
    borderWidth: 1,
    borderColor: colors.border,
    padding: spacing.sm,
    gap: spacing.sm,
  },
  leadInfo: { flexDirection: "row", alignItems: "center", gap: spacing.sm },
  leadName: { color: colors.onSurface, fontSize: 14.5, fontWeight: "700" },
  leadMeta: { color: colors.onSurfaceTertiary, fontSize: 11.5, marginTop: 1 },
  leadBadges: { flexDirection: "row", alignItems: "center", gap: spacing.sm, marginTop: spacing.xs },
  waitTag: { flexDirection: "row", alignItems: "center", gap: 3, backgroundColor: "rgba(0,0,0,0.3)", paddingHorizontal: 7, paddingVertical: 2, borderRadius: radius.pill },
  waitText: { color: colors.onBrandTertiary, fontSize: 10, fontWeight: "700" },
  moveBtn: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 6,
    paddingVertical: 8,
    borderRadius: radius.sm,
    borderWidth: 1,
    borderColor: colors.borderStrong,
  },
  moveText: { color: colors.brandPrimary, fontSize: 12.5, fontWeight: "700" },
  optionRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.md,
    paddingVertical: spacing.md,
    paddingHorizontal: spacing.md,
    borderRadius: radius.md,
    borderWidth: 1,
    borderColor: colors.border,
    marginBottom: spacing.sm,
  },
  optDot: { width: 10, height: 10, borderRadius: 5 },
  optText: { color: colors.onSurfaceSecondary, fontSize: 14, flex: 1 },
});
