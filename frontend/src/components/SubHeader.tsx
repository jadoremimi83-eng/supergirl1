import React from "react";
import { View, Text, StyleSheet, Pressable } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { useRouter } from "expo-router";
import { Feather } from "@expo/vector-icons";
import { colors, spacing, type, font } from "@/src/theme";

export function SubHeader({ title, right }: { title: string; right?: React.ReactNode }) {
  const insets = useSafeAreaInsets();
  const router = useRouter();
  return (
    <View style={[styles.bar, { paddingTop: insets.top + spacing.sm }]}>
      <Pressable testID="sub-back" onPress={() => router.back()} hitSlop={10} style={styles.back}>
        <Feather name="chevron-left" size={26} color={colors.onSurface} />
      </Pressable>
      <Text style={styles.title} numberOfLines={1}>
        {title}
      </Text>
      <View style={styles.right}>{right}</View>
    </View>
  );
}

const styles = StyleSheet.create({
  bar: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.sm,
    paddingHorizontal: spacing.md,
    paddingBottom: spacing.md,
    backgroundColor: colors.surface,
    borderBottomWidth: 1,
    borderBottomColor: colors.divider,
  },
  back: { padding: 2 },
  title: { flex: 1, color: colors.onSurface, fontSize: type.xl, fontWeight: "700", fontFamily: font.display },
  right: { minWidth: 30, alignItems: "flex-end" },
});
