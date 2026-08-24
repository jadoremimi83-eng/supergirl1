import React, { useCallback, useState } from "react";
import { View, Text, StyleSheet, ScrollView, Pressable, RefreshControl } from "react-native";
import { useFocusEffect } from "expo-router";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { Feather } from "@expo/vector-icons";
import { api } from "@/src/api";
import { colors, spacing, radius, type, font } from "@/src/theme";
import { Loading, Sheet, SectionTitle } from "@/src/components/ui";
import { AppHeader } from "@/src/components/AppHeader";
import { Chips } from "@/src/components/Chips";

const PERIODS = [
  { key: "oggi", label: "Oggi" },
  { key: "7d", label: "7 giorni" },
  { key: "30d", label: "30 giorni" },
];

type Dim = { sedi: string[]; servizi: string[]; campagne: string[]; inserzioni: string[]; piattaforme: string[] };

export default function Analytics() {
  const insets = useSafeAreaInsets();
  const [period, setPeriod] = useState("30d");
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [dims, setDims] = useState<Dim | null>(null);
  const [filterSheet, setFilterSheet] = useState(false);
  const [filters, setFilters] = useState<{ sede?: string; servizio?: string; campagna?: string; piattaforma?: string }>({});

  const load = useCallback(async () => {
    try {
      const qs = new URLSearchParams({ period });
      Object.entries(filters).forEach(([k, v]) => v && qs.append(k, v));
      const [a, f] = await Promise.all([api.get(`/analytics?${qs.toString()}`), dims ? Promise.resolve(dims) : api.get("/analytics/filters")]);
      setData(a);
      if (!dims) setDims(f);
    } catch {}
    setLoading(false);
    setRefreshing(false);
  }, [period, filters, dims]);

  useFocusEffect(
    useCallback(() => {
      load();
    }, [period, filters])
  );

  const activeFilters = Object.values(filters).filter(Boolean).length;
  const maxFunnel = data?.funnel?.[0]?.value || 1;

  return (
    <View style={{ flex: 1, backgroundColor: colors.surface }}>
      <AppHeader title="Analytics" subtitle="Risultati e conversioni" />
      <Chips items={PERIODS} value={period} onChange={setPeriod} />

      <View style={styles.filterBar}>
        <Pressable style={styles.filterBtn} onPress={() => setFilterSheet(true)} testID="open-filters-button">
          <Feather name="sliders" size={15} color={colors.brandPrimary} />
          <Text style={styles.filterBtnText}>Filtri{activeFilters ? ` (${activeFilters})` : ""}</Text>
        </Pressable>
        {activeFilters > 0 && (
          <Pressable onPress={() => setFilters({})} testID="clear-filters-button">
            <Text style={styles.clearText}>Azzera</Text>
          </Pressable>
        )}
      </View>

      {loading || !data ? (
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
          {/* Conversioni principali */}
          <View style={styles.convRow}>
            <ConvCard label="Lead → Interessata" value={`${data.pct_lead_interessata}%`} />
            <ConvCard label="Lead → Appuntamento" value={`${data.pct_lead_appuntamento}%`} gold />
          </View>

          {/* Funnel */}
          <View style={styles.section}>
            <SectionTitle>Funnel commerciale</SectionTitle>
            {data.funnel.map((f: any, i: number) => (
              <View key={f.label} style={styles.funnelRow}>
                <Text style={styles.funnelLabel}>{f.label}</Text>
                <View style={styles.funnelTrack}>
                  <View
                    style={[
                      styles.funnelFill,
                      { width: `${Math.max((f.value / maxFunnel) * 100, 4)}%`, opacity: 1 - i * 0.14 },
                    ]}
                  />
                </View>
                <Text style={styles.funnelValue}>{f.value}</Text>
              </View>
            ))}
          </View>

          {/* KPI grid */}
          <SectionTitle>Metriche</SectionTitle>
          <View style={styles.grid}>
            <Kpi icon="user-plus" label="Nuovi lead" value={data.nuovi_lead} />
            <Kpi icon="cpu" label="Conversazioni AI" value={data.conversazioni_ai} />
            <Kpi icon="message-square" label="Hanno risposto" value={data.risposte} />
            <Kpi icon="heart" label="Interessate" value={data.interessate} />
            <Kpi icon="star" label="Da fissare" value={data.da_fissare} gold />
            <Kpi icon="check-circle" label="Appuntamenti" value={data.appuntamenti} />
            <Kpi icon="x-circle" label="Non interessate" value={data.non_interessate} />
            <Kpi icon="slash" label="Lead persi" value={data.persi} />
          </View>

          {/* Per campagna */}
          <View style={[styles.section, { marginTop: spacing.lg }]}>
            <SectionTitle>Per campagna</SectionTitle>
            <View style={styles.campHead}>
              <Text style={[styles.campCell, { flex: 2 }]}>Campagna</Text>
              <Text style={styles.campCell}>Lead</Text>
              <Text style={styles.campCell}>Fissare</Text>
              <Text style={styles.campCell}>Appunt.</Text>
            </View>
            {data.by_campaign.map((c: any) => (
              <View key={c.campagna} style={styles.campRow}>
                <Text style={[styles.campVal, { flex: 2, textAlign: "left" }]} numberOfLines={1}>
                  {c.campagna}
                </Text>
                <Text style={styles.campVal}>{c.lead}</Text>
                <Text style={[styles.campVal, { color: colors.brandPrimary }]}>{c.da_fissare}</Text>
                <Text style={[styles.campVal, { color: colors.onSuccess }]}>{c.appuntamenti}</Text>
              </View>
            ))}
          </View>
        </ScrollView>
      )}

      <Sheet visible={filterSheet} onClose={() => setFilterSheet(false)} title="Filtri analitici">
        <FilterGroup
          title="Piattaforma"
          options={dims?.piattaforme || []}
          value={filters.piattaforma}
          onSelect={(v) => setFilters((f) => ({ ...f, piattaforma: f.piattaforma === v ? undefined : v }))}
        />
        <FilterGroup
          title="Sede"
          options={dims?.sedi || []}
          value={filters.sede}
          onSelect={(v) => setFilters((f) => ({ ...f, sede: f.sede === v ? undefined : v }))}
        />
        <FilterGroup
          title="Servizio"
          options={dims?.servizi || []}
          value={filters.servizio}
          onSelect={(v) => setFilters((f) => ({ ...f, servizio: f.servizio === v ? undefined : v }))}
        />
        <FilterGroup
          title="Campagna"
          options={dims?.campagne || []}
          value={filters.campagna}
          onSelect={(v) => setFilters((f) => ({ ...f, campagna: f.campagna === v ? undefined : v }))}
        />
        <View style={{ height: spacing.md }} />
        <Pressable style={styles.applyBtn} onPress={() => setFilterSheet(false)} testID="apply-filters-button">
          <Text style={styles.applyText}>Applica</Text>
        </Pressable>
      </Sheet>
    </View>
  );
}

function ConvCard({ label, value, gold }: { label: string; value: string; gold?: boolean }) {
  return (
    <View style={[styles.convCard, gold && { borderColor: colors.brandPrimary, backgroundColor: colors.brandTertiary }]}>
      <Text style={[styles.convValue, gold && { color: colors.brandPrimary }]}>{value}</Text>
      <Text style={styles.convLabel}>{label}</Text>
    </View>
  );
}

function Kpi({ icon, label, value, gold }: { icon: any; label: string; value: number; gold?: boolean }) {
  return (
    <View style={[styles.kpi, gold && { borderColor: colors.borderStrong }]}>
      <Feather name={icon} size={16} color={gold ? colors.brandPrimary : colors.onSurfaceTertiary} />
      <Text style={[styles.kpiValue, gold && { color: colors.brandPrimary }]}>{value}</Text>
      <Text style={styles.kpiLabel} numberOfLines={1}>
        {label}
      </Text>
    </View>
  );
}

function FilterGroup({ title, options, value, onSelect }: { title: string; options: string[]; value?: string; onSelect: (v: string) => void }) {
  return (
    <View style={{ marginBottom: spacing.md }}>
      <Text style={styles.fgTitle}>{title}</Text>
      <View style={styles.fgWrap}>
        {options.map((o) => {
          const active = o === value;
          return (
            <Pressable
              key={o}
              onPress={() => onSelect(o)}
              style={[styles.fgChip, active && { backgroundColor: colors.brandPrimary, borderColor: colors.brandPrimary }]}
              testID={`filter-${o}`}
            >
              <Text style={[styles.fgChipText, active && { color: colors.onBrandPrimary }]}>{o}</Text>
            </Pressable>
          );
        })}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  filterBar: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", paddingHorizontal: spacing.lg, paddingBottom: spacing.sm },
  filterBtn: { flexDirection: "row", alignItems: "center", gap: 6, borderWidth: 1, borderColor: colors.borderStrong, borderRadius: radius.pill, paddingHorizontal: spacing.md, paddingVertical: 7 },
  filterBtnText: { color: colors.brandPrimary, fontSize: 13, fontWeight: "700" },
  clearText: { color: colors.onSurfaceTertiary, fontSize: 13, fontWeight: "600" },
  convRow: { flexDirection: "row", gap: spacing.md, marginBottom: spacing.lg },
  convCard: { flex: 1, backgroundColor: colors.surfaceSecondary, borderRadius: radius.md, borderWidth: 1, borderColor: colors.border, padding: spacing.lg },
  convValue: { color: colors.onSurface, fontSize: 28, fontWeight: "800", fontFamily: font.display },
  convLabel: { color: colors.onSurfaceTertiary, fontSize: 12, marginTop: 2 },
  section: { backgroundColor: colors.surfaceSecondary, borderRadius: radius.md, borderWidth: 1, borderColor: colors.border, padding: spacing.lg, marginBottom: spacing.lg },
  funnelRow: { flexDirection: "row", alignItems: "center", gap: spacing.sm, marginBottom: spacing.sm },
  funnelLabel: { color: colors.onSurfaceSecondary, fontSize: 12, width: 96 },
  funnelTrack: { flex: 1, height: 22, backgroundColor: colors.surface, borderRadius: radius.sm, overflow: "hidden" },
  funnelFill: { height: "100%", backgroundColor: colors.brandPrimary, borderRadius: radius.sm },
  funnelValue: { color: colors.onSurface, fontSize: 14, fontWeight: "800", width: 28, textAlign: "right" },
  grid: { flexDirection: "row", flexWrap: "wrap", gap: spacing.md },
  kpi: {
    width: "47%",
    flexGrow: 1,
    backgroundColor: colors.surfaceSecondary,
    borderRadius: radius.md,
    borderWidth: 1,
    borderColor: colors.border,
    padding: spacing.lg,
    gap: 6,
  },
  kpiValue: { color: colors.onSurface, fontSize: 24, fontWeight: "800", fontFamily: font.display },
  kpiLabel: { color: colors.onSurfaceTertiary, fontSize: 12 },
  campHead: { flexDirection: "row", paddingBottom: spacing.sm, borderBottomWidth: 1, borderBottomColor: colors.border },
  campCell: { flex: 1, color: colors.onSurfaceTertiary, fontSize: 11, fontWeight: "700", textAlign: "center" },
  campRow: { flexDirection: "row", alignItems: "center", paddingVertical: spacing.sm, borderBottomWidth: 1, borderBottomColor: colors.divider },
  campVal: { flex: 1, color: colors.onSurface, fontSize: 13, fontWeight: "600", textAlign: "center" },
  fgTitle: { color: colors.onSurfaceSecondary, fontSize: 13, fontWeight: "700", marginBottom: spacing.sm },
  fgWrap: { flexDirection: "row", flexWrap: "wrap", gap: spacing.sm },
  fgChip: { paddingHorizontal: spacing.md, paddingVertical: 8, borderRadius: radius.pill, borderWidth: 1, borderColor: colors.border, backgroundColor: colors.surface },
  fgChipText: { color: colors.onSurfaceSecondary, fontSize: 12.5, fontWeight: "600" },
  applyBtn: { backgroundColor: colors.brandPrimary, borderRadius: radius.md, paddingVertical: 14, alignItems: "center" },
  applyText: { color: colors.onBrandPrimary, fontSize: type.lg, fontWeight: "800", letterSpacing: 0.5 },
});
