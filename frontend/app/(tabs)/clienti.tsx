import React, { useCallback, useState } from "react";
import { View, Text, StyleSheet, FlatList, Pressable, TextInput } from "react-native";
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

  const load = useCallback(async (q: string) => {
    try {
      const res = await api.get(`/leads${q ? `?search=${encodeURIComponent(q)}` : ""}`);
      setLeads(res);
    } catch {}
    setLoading(false);
  }, []);

  useFocusEffect(
    useCallback(() => {
      load(search);
    }, [])
  );

  const onSearch = (q: string) => {
    setSearch(q);
    load(q);
  };

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
      </View>
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
  searchWrap: { paddingHorizontal: spacing.lg, paddingVertical: spacing.md },
  searchBox: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.sm,
    backgroundColor: colors.surfaceSecondary,
    borderRadius: radius.md,
    borderWidth: 1,
    borderColor: colors.border,
    paddingHorizontal: spacing.lg,
  },
  searchInput: { flex: 1, color: colors.onSurface, fontSize: type.lg, paddingVertical: 12 },
  row: { flexDirection: "row", alignItems: "center", gap: spacing.md, paddingHorizontal: spacing.lg, paddingVertical: spacing.md },
  name: { color: colors.onSurface, fontSize: type.lg, fontWeight: "700" },
  meta: { color: colors.onSurfaceTertiary, fontSize: 12, marginTop: 1 },
  service: { color: colors.onSurfaceSecondary, fontSize: 12.5, marginTop: 2 },
  badges: { flexDirection: "row", alignItems: "center", gap: spacing.sm, marginTop: spacing.sm, flexWrap: "wrap" },
  sep: { height: 1, backgroundColor: colors.divider, marginLeft: 76 },
});
