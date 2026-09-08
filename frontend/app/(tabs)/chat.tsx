import React, { useCallback, useState } from "react";
import { View, Text, StyleSheet, FlatList, Pressable, RefreshControl } from "react-native";
import { useRouter, useFocusEffect } from "expo-router";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { Feather } from "@expo/vector-icons";
import { api } from "@/src/api";
import { colors, spacing, radius, type } from "@/src/theme";
import { Avatar, TempBadge, AiBadge, Loading, EmptyState } from "@/src/components/ui";
import { AppHeader } from "@/src/components/AppHeader";
import { Chips } from "@/src/components/Chips";
import { chatTime } from "@/src/time";

const FILTERS = [
  { key: "tutte", label: "Tutte" },
  { key: "ai", label: "AI" },
  { key: "operatore", label: "Operatore" },
  { key: "da_fissare", label: "Da fissare" },
  { key: "non_lette", label: "Non lette" },
];

type Conv = {
  id: string;
  lead_nome: string;
  last_message: string;
  last_message_at: string;
  unread: number;
  ai_attiva: boolean;
  stato: string;
  temperature?: string;
  foto_profilo?: string | null;
};

export default function Chat() {
  const insets = useSafeAreaInsets();
  const router = useRouter();
  const [filter, setFilter] = useState("tutte");
  const [convs, setConvs] = useState<Conv[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const load = useCallback(
    async (f: string) => {
      try {
        const res = await api.get(`/conversations?filter=${f}`);
        setConvs(res);
      } catch {}
      setLoading(false);
      setRefreshing(false);
    },
    []
  );

  useFocusEffect(
    useCallback(() => {
      load(filter);
    }, [filter, load])
  );

  const renderRow = ({ item }: { item: Conv }) => (
    <Pressable
      testID={`conversation-row-${item.id}`}
      onPress={() => router.push(`/conversation/${item.id}`)}
      style={({ pressed }) => [styles.row, pressed && { backgroundColor: colors.surfaceSecondary }]}
    >
      <View>
        <Avatar uri={item.foto_profilo} name={item.lead_nome} size={52} />
        {(item.stato === "da_fissare" || item.stato === "attesa_chiamata") && (
          <View style={styles.fissareDot}>
            <Feather name="star" size={9} color={colors.onBrandPrimary} />
          </View>
        )}
      </View>
      <View style={{ flex: 1 }}>
        <View style={styles.rowTop}>
          <Text style={styles.name} numberOfLines={1}>
            {item.lead_nome}
          </Text>
          <Text style={styles.time}>{chatTime(item.last_message_at)}</Text>
        </View>
        <View style={styles.rowMid}>
          <Text
            style={[styles.last, item.unread > 0 && { color: colors.onSurface, fontWeight: "600" }]}
            numberOfLines={1}
          >
            {item.last_message}
          </Text>
          {item.unread > 0 && (
            <View style={styles.unread}>
              <Text style={styles.unreadText}>{item.unread}</Text>
            </View>
          )}
        </View>
        <View style={styles.rowBottom}>
          <AiBadge active={item.ai_attiva} />
          <TempBadge temp={item.temperature} small />
        </View>
      </View>
    </Pressable>
  );

  return (
    <View style={{ flex: 1, backgroundColor: colors.surface }}>
      <AppHeader title="Chat" subtitle="Conversazioni WhatsApp" />
      <Chips items={FILTERS} value={filter} onChange={setFilter} />
      {loading ? (
        <Loading />
      ) : convs.length === 0 ? (
        <EmptyState icon="message-circle" title="Nessuna conversazione" subtitle="Non ci sono chat per questo filtro." />
      ) : (
        <FlatList
          data={convs}
          keyExtractor={(c) => c.id}
          renderItem={renderRow}
          contentContainerStyle={{ paddingBottom: insets.bottom + spacing.xl }}
          ItemSeparatorComponent={() => <View style={styles.sep} />}
          refreshControl={
            <RefreshControl
              refreshing={refreshing}
              onRefresh={() => {
                setRefreshing(true);
                load(filter);
              }}
              tintColor={colors.brandPrimary}
            />
          }
        />
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  row: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.md,
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.md,
  },
  fissareDot: {
    position: "absolute",
    bottom: -2,
    right: -2,
    width: 20,
    height: 20,
    borderRadius: 10,
    backgroundColor: colors.brandPrimary,
    alignItems: "center",
    justifyContent: "center",
    borderWidth: 2,
    borderColor: colors.surface,
  },
  rowTop: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", gap: spacing.sm },
  name: { color: colors.onSurface, fontSize: type.lg, fontWeight: "700", flex: 1 },
  time: { color: colors.onSurfaceTertiary, fontSize: 11 },
  rowMid: { flexDirection: "row", alignItems: "center", gap: spacing.sm, marginTop: 3 },
  last: { color: colors.onSurfaceTertiary, fontSize: 13, flex: 1 },
  unread: {
    minWidth: 20,
    height: 20,
    borderRadius: 10,
    backgroundColor: colors.brandPrimary,
    paddingHorizontal: 5,
    alignItems: "center",
    justifyContent: "center",
  },
  unreadText: { color: colors.onBrandPrimary, fontSize: 11, fontWeight: "800" },
  rowBottom: { flexDirection: "row", alignItems: "center", gap: spacing.sm, marginTop: spacing.sm },
  sep: { height: 1, backgroundColor: colors.divider, marginLeft: 80 },
});
