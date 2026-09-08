import React, { useCallback, useState } from "react";
import { View, Text, StyleSheet, FlatList, Pressable, TextInput, ScrollView } from "react-native";
import { useRouter, useFocusEffect } from "expo-router";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { Feather } from "@expo/vector-icons";
import { api } from "@/src/api";
import { colors, spacing, radius, type } from "@/src/theme";
import { Avatar, TempBadge, StageBadge, Loading, EmptyState } from "@/src/components/ui";
import { AppHeader } from "@/src/components/AppHeader";

export default function Clienti() {
  const insets = useSafeAreaInsets();
  const router = useRouter();
  const [search, setSearch] = useState("");
  const [leads, setLeads] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [segments, setSegments] = useState<any>(null);
  const [filters, setFilters] = useState<any>({});
  const [showFilters, setShowFilters] = useState(false);

  const load = useCallback(async (q: string, f: any) => {
    try {
      const p = new URLSearchParams();
      if (q) p.append("search", q);
      if (f.sede) p.append("sede", f.sede);
      if (f.servizio) p.append("servizio", f.servizio);
      if (f.stato_pipeline) p.append("stato", f.stato_pipeline);
      if (f.temperature) p.append("temperature", f.temperature);
      const qs = p.toString();
      const res = await api.get(`/leads${qs ? `?${qs}` : ""}`);
      setLeads(res);
    } catch {}
    setLoading(false);
  }, []);

  useFocusEffect(
    useCallback(() => {
      load(search, filters);
      api.get("/segments").then(setSegments).catch(() => {});
    }, [])
  );

  const onSearch = (q: string) => {
    setSearch(q);
    load(q, filters);
  };

  const toggleFilter = (cat: string, val: string) => {
    setFilters((prev: any) => {
      const next = { ...prev, [cat]: prev[cat] === val ? undefined : val };
      load(search, next);
      return next;
    });
  };

  const clearFilters = () => {
    setFilters({});
    load(search, {});
  };

  const activeCount = Object.values(filters).filter(Boolean).length;
  const nice = (s: string) => (s || "").replace(/_/g, " ");

  const renderRow = ({ item }: { item: any }) => (
    <Pressable
      testID={`client-row-${item.id}`}
      onPress={() => router.push(`/cliente/${item.id}`)}
      style={({ pressed }) => [styles.row, pressed && { backgroundColor: colors.surfaceSecondary }]}
    >
      <Avatar uri={item.foto_profilo} name={`${item.nome} ${item.cognome}`} size={48} />
      <View style={{ flex: 1 }}>
        <Text style={styles.name} numberOfLines={1}>
          {item.nome} {item.cognome}
        </Text>
        <Text style={styles.meta} numberOfLines={1}>
          {item.telefono}
        </Text>
        <Text style={styles.service} numberOfLines={1}>
          {item.servizio} · {item.sede}
        </Text>
        <View style={styles.badges}>
          <StageBadge stage={item.stato_pipeline} />
          <TempBadge temp={item.temperature} small />
        </View>
      </View>
      <Feather name="chevron-right" size={20} color={colors.onSurfaceTertiary} />
    </Pressable>
  );

  return (
    <View style={{ flex: 1, backgroundColor: colors.surface }}>
      <AppHeader title="Clienti" subtitle="Database lead" />
      <View style={styles.searchWrap}>
        <View style={styles.searchBox}>
          <Feather name="search" size={18} color={colors.onSurfaceTertiary} />
          <TextInput
            testID="client-search-input"
            value={search}
            onChangeText={onSearch}
            placeholder="Cerca per nome o telefono…"
            placeholderTextColor={colors.onSurfaceTertiary}
            style={styles.searchInput}
            autoCapitalize="none"
          />
          {search ? (
            <Pressable onPress={() => onSearch("")} hitSlop={8}>
              <Feather name="x" size={18} color={colors.onSurfaceTertiary} />
            </Pressable>
          ) : null}
        </View>
        <Pressable
          testID="toggle-filters"
          onPress={() => setShowFilters((v) => !v)}
          style={[styles.filterBtn, activeCount > 0 && styles.filterBtnActive]}
        >
          <Feather name="sliders" size={18} color={activeCount > 0 ? colors.onPrimary : colors.onSurfaceSecondary} />
          {activeCount > 0 ? <Text style={styles.filterBadge}>{activeCount}</Text> : null}
        </Pressable>
      </View>

      {showFilters && segments ? (
        <View style={styles.filterPanel}>
          {[
            { key: "sede", label: "Sede", data: segments.sede },
            { key: "servizio", label: "Trattamento", data: segments.servizio },
            { key: "stato_pipeline", label: "Stato", data: segments.stato_pipeline },
            { key: "temperature", label: "Interesse", data: segments.temperature },
          ].map((cat) =>
            cat.data && cat.data.length ? (
              <View key={cat.key} style={{ marginBottom: spacing.sm }}>
                <Text style={styles.filterCat}>{cat.label}</Text>
                <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={{ gap: spacing.sm, paddingRight: spacing.lg }}>
                  {cat.data.map((opt: any) => {
                    const active = filters[cat.key] === opt.value;
                    return (
                      <Pressable
                        key={opt.value}
                        testID={`chip-${cat.key}-${opt.value}`}
                        onPress={() => toggleFilter(cat.key, opt.value)}
                        style={[styles.chip, active && styles.chipActive]}
                      >
                        <Text style={[styles.chipText, active && styles.chipTextActive]}>
                          {nice(opt.value)} · {opt.count}
                        </Text>
                      </Pressable>
                    );
                  })}
                </ScrollView>
              </View>
            ) : null
          )}
          {activeCount > 0 ? (
            <Pressable onPress={clearFilters} style={styles.clearBtn} testID="clear-filters">
              <Feather name="x-circle" size={14} color={colors.onSurfaceSecondary} />
              <Text style={styles.clearText}>Pulisci filtri</Text>
            </Pressable>
          ) : null}
        </View>
      ) : null}
      {loading ? (
        <Loading />
      ) : leads.length === 0 ? (
        <EmptyState icon="users" title="Nessun cliente trovato" subtitle="Prova con un altro nome o numero." />
      ) : (
        <FlatList
          data={leads}
          keyExtractor={(l) => l.id}
          renderItem={renderRow}
          contentContainerStyle={{ paddingBottom: insets.bottom + spacing.xl }}
          ItemSeparatorComponent={() => <View style={styles.sep} />}
          keyboardShouldPersistTaps="handled"
        />
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  searchWrap: { flexDirection: "row", alignItems: "center", gap: spacing.sm, paddingHorizontal: spacing.lg, paddingVertical: spacing.md },
  searchBox: {
    flex: 1,
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.sm,
    backgroundColor: colors.surfaceSecondary,
    borderRadius: radius.md,
    borderWidth: 1,
    borderColor: colors.border,
    paddingHorizontal: spacing.lg,
  },
  filterBtn: {
    flexDirection: "row", alignItems: "center", gap: 4,
    height: 44, paddingHorizontal: spacing.md,
    borderRadius: radius.md, borderWidth: 1, borderColor: colors.border,
    backgroundColor: colors.surfaceSecondary,
  },
  filterBtnActive: { backgroundColor: colors.brandPrimary, borderColor: colors.brandPrimary },
  filterBadge: { color: colors.onBrandPrimary, fontSize: 12, fontWeight: "800" },
  filterPanel: { paddingHorizontal: spacing.lg, paddingBottom: spacing.md },
  filterCat: { color: colors.onSurfaceTertiary, fontSize: 11, fontWeight: "700", marginBottom: 6, textTransform: "uppercase", letterSpacing: 0.4 },
  chip: {
    paddingHorizontal: spacing.md, paddingVertical: 7,
    borderRadius: 999, borderWidth: 1, borderColor: colors.border,
    backgroundColor: colors.surfaceSecondary,
  },
  chipActive: { backgroundColor: colors.brandPrimary, borderColor: colors.brandPrimary },
  chipText: { color: colors.onSurfaceSecondary, fontSize: 12.5, fontWeight: "600", textTransform: "capitalize" },
  chipTextActive: { color: colors.onBrandPrimary, fontWeight: "800" },
  clearBtn: { flexDirection: "row", alignItems: "center", gap: 5, marginTop: 4, alignSelf: "flex-start" },
  clearText: { color: colors.onSurfaceSecondary, fontSize: 12.5, fontWeight: "600" },
  searchInput: { flex: 1, color: colors.onSurface, fontSize: type.lg, paddingVertical: 12 },
  row: { flexDirection: "row", alignItems: "center", gap: spacing.md, paddingHorizontal: spacing.lg, paddingVertical: spacing.md },
  name: { color: colors.onSurface, fontSize: type.lg, fontWeight: "700" },
  meta: { color: colors.onSurfaceTertiary, fontSize: 12, marginTop: 1 },
  service: { color: colors.onSurfaceSecondary, fontSize: 12.5, marginTop: 2 },
  badges: { flexDirection: "row", alignItems: "center", gap: spacing.sm, marginTop: spacing.sm, flexWrap: "wrap" },
  sep: { height: 1, backgroundColor: colors.divider, marginLeft: 76 },
});
