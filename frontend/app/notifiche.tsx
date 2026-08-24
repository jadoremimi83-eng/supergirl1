import React, { useCallback, useState } from "react";
import { View, Text, StyleSheet, FlatList, Pressable } from "react-native";
import { useRouter, useFocusEffect } from "expo-router";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { Feather } from "@expo/vector-icons";
import { api } from "@/src/api";
import { colors, spacing, radius, type, font } from "@/src/theme";
import { Loading, EmptyState } from "@/src/components/ui";
import { timeAgo } from "@/src/time";

const TYPES: Record<string, { icon: any; color: string; title: string }> = {
  cliente_da_fissare: { icon: "star", color: colors.brandPrimary, title: "Cliente pronta da fissare" },
  ai_intervento: { icon: "alert-triangle", color: colors.onWarning, title: "AI richiede intervento" },
  nuova_chat: { icon: "message-circle", color: colors.onSuccess, title: "Nuova chat assegnata" },
  nuovo_messaggio: { icon: "mail", color: colors.onInfo, title: "Nuovo messaggio" },
};

export default function Notifiche() {
  const insets = useSafeAreaInsets();
  const router = useRouter();
  const [items, setItems] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    try {
      const res = await api.get("/notifications");
      setItems(res.notifications);
    } catch {}
    setLoading(false);
  }, []);
  useFocusEffect(useCallback(() => { load(); }, [load]));

  const markAll = async () => {
    await api.post("/notifications/read-all");
    load();
  };

  const openNotif = async (n: any) => {
    await api.post(`/notifications/${n.id}/read`);
    if (n.lead_id) router.push(`/cliente/${n.lead_id}`);
  };

  return (
    <View style={{ flex: 1, backgroundColor: colors.surface }}>
      <View style={[styles.header, { paddingTop: insets.top + spacing.sm }]}>
        <Pressable onPress={() => router.back()} hitSlop={10} testID="notif-close">
          <Feather name="chevron-down" size={26} color={colors.onSurface} />
        </Pressable>
        <Text style={styles.title}>Notifiche</Text>
        <Pressable onPress={markAll} hitSlop={10} testID="mark-all-read">
          <Text style={styles.markAll}>Segna lette</Text>
        </Pressable>
      </View>
      {loading ? (
        <Loading />
      ) : items.length === 0 ? (
        <EmptyState icon="bell" title="Nessuna notifica" subtitle="Sei aggiornata su tutto." />
      ) : (
        <FlatList
          data={items}
          keyExtractor={(n) => n.id}
          contentContainerStyle={{ padding: spacing.lg, paddingBottom: insets.bottom + spacing.xl }}
          renderItem={({ item }) => {
            const t = TYPES[item.tipo] || TYPES.nuovo_messaggio;
            return (
              <Pressable onPress={() => openNotif(item)} style={[styles.card, !item.read && styles.unread]} testID={`notif-${item.id}`}>
                <View style={[styles.iconBox, { backgroundColor: colors.surfaceTertiary }]}>
                  <Feather name={t.icon} size={18} color={t.color} />
                </View>
                <View style={{ flex: 1 }}>
                  <Text style={styles.cardTitle}>{t.title}</Text>
                  <Text style={styles.cardName}>{item.lead_nome}</Text>
                  {!!item.text && <Text style={styles.cardText} numberOfLines={2}>{item.text}</Text>}
                  <Text style={styles.time}>{timeAgo(item.created_at)}</Text>
                </View>
                {!item.read && <View style={styles.dot} />}
              </Pressable>
            );
          }}
        />
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  header: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", paddingHorizontal: spacing.lg, paddingBottom: spacing.md, borderBottomWidth: 1, borderBottomColor: colors.divider },
  title: { color: colors.onSurface, fontSize: type.xl, fontWeight: "700", fontFamily: font.display },
  markAll: { color: colors.brandPrimary, fontSize: 13, fontWeight: "700" },
  card: { flexDirection: "row", alignItems: "flex-start", gap: spacing.md, backgroundColor: colors.surfaceSecondary, borderRadius: radius.md, borderWidth: 1, borderColor: colors.border, padding: spacing.md, marginBottom: spacing.sm },
  unread: { borderColor: colors.borderStrong, backgroundColor: colors.brandTertiary },
  iconBox: { width: 40, height: 40, borderRadius: radius.sm, alignItems: "center", justifyContent: "center" },
  cardTitle: { color: colors.onSurface, fontSize: 14, fontWeight: "700" },
  cardName: { color: colors.brandSecondary, fontSize: 13, fontWeight: "600", marginTop: 1 },
  cardText: { color: colors.onSurfaceTertiary, fontSize: 12.5, marginTop: 3, lineHeight: 17 },
  time: { color: colors.onSurfaceTertiary, fontSize: 11, marginTop: 4 },
  dot: { width: 9, height: 9, borderRadius: 4.5, backgroundColor: colors.brandPrimary, marginTop: 4 },
});
