import React, { useCallback, useState } from "react";
import { View, Text, StyleSheet, Pressable } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { useRouter } from "expo-router";
import { useFocusEffect } from "expo-router";
import { Feather } from "@expo/vector-icons";
import { colors, spacing, type, font } from "@/src/theme";
import { api } from "@/src/api";

export function AppHeader({ title, subtitle }: { title: string; subtitle?: string }) {
  const insets = useSafeAreaInsets();
  const router = useRouter();
  const [unread, setUnread] = useState(0);
  const [daFissare, setDaFissare] = useState(0);

  useFocusEffect(
    useCallback(() => {
      let active = true;
      (async () => {
        try {
          const [n, h] = await Promise.all([
            api.get("/notifications"),
            api.get("/home/priorities"),
          ]);
          if (active) {
            setUnread(n.unread || 0);
            setDaFissare(h.count || 0);
          }
        } catch {}
      })();
      return () => {
        active = false;
      };
    }, [])
  );

  return (
    <View style={[styles.wrap, { paddingTop: insets.top + spacing.sm }]}>
      <View style={styles.row}>
        <View style={{ flex: 1 }}>
          <Text style={styles.title}>{title}</Text>
          {subtitle ? <Text style={styles.subtitle}>{subtitle}</Text> : null}
        </View>
        <Pressable
          testID="header-priorities-button"
          onPress={() => router.push("/priorities")}
          style={styles.iconBtn}
          hitSlop={8}
        >
          <Feather name="target" size={20} color={colors.brandPrimary} />
          {daFissare > 0 && (
            <View style={[styles.badge, { backgroundColor: colors.brandPrimary }]}>
              <Text style={styles.badgeText}>{daFissare}</Text>
            </View>
          )}
        </Pressable>
        <Pressable
          testID="header-notifications-button"
          onPress={() => router.push("/notifiche")}
          style={styles.iconBtn}
          hitSlop={8}
        >
          <Feather name="bell" size={20} color={colors.onSurface} />
          {unread > 0 && (
            <View style={[styles.badge, { backgroundColor: colors.onError }]}>
              <Text style={[styles.badgeText, { color: colors.surface }]}>{unread}</Text>
            </View>
          )}
        </Pressable>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: {
    backgroundColor: colors.surface,
    paddingHorizontal: spacing.lg,
    paddingBottom: spacing.md,
    borderBottomWidth: 1,
    borderBottomColor: colors.divider,
  },
  row: { flexDirection: "row", alignItems: "center", gap: spacing.md },
  title: {
    color: colors.onSurface,
    fontSize: type["2xl"],
    fontWeight: "700",
    fontFamily: font.display,
    letterSpacing: 0.5,
  },
  subtitle: { color: colors.onSurfaceTertiary, fontSize: 12, marginTop: 2 },
  iconBtn: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: colors.surfaceSecondary,
    borderWidth: 1,
    borderColor: colors.border,
    alignItems: "center",
    justifyContent: "center",
  },
  badge: {
    position: "absolute",
    top: -3,
    right: -3,
    minWidth: 18,
    height: 18,
    borderRadius: 9,
    paddingHorizontal: 4,
    alignItems: "center",
    justifyContent: "center",
  },
  badgeText: { color: colors.onBrandPrimary, fontSize: 10, fontWeight: "800" },
});
