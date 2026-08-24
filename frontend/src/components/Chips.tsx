import React from "react";
import { ScrollView, Pressable, Text, StyleSheet, View } from "react-native";
import { colors, spacing, radius } from "@/src/theme";

export type ChipItem = { key: string; label: string; count?: number };

export function Chips({
  items,
  value,
  onChange,
}: {
  items: ChipItem[];
  value: string;
  onChange: (key: string) => void;
}) {
  return (
    <View style={styles.wrap}>
      <ScrollView
        horizontal
        showsHorizontalScrollIndicator={false}
        contentContainerStyle={styles.content}
      >
        {items.map((it) => {
          const active = it.key === value;
          return (
            <Pressable
              key={it.key}
              testID={`chip-${it.key}`}
              onPress={() => onChange(it.key)}
              style={[styles.chip, active ? styles.chipActive : styles.chipIdle]}
            >
              <Text style={[styles.chipText, active ? styles.chipTextActive : styles.chipTextIdle]}>
                {it.label}
                {typeof it.count === "number" ? ` ${it.count}` : ""}
              </Text>
            </Pressable>
          );
        })}
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: { height: 56, justifyContent: "center", backgroundColor: colors.surface },
  content: { paddingHorizontal: spacing.lg, gap: spacing.sm, alignItems: "center" },
  chip: {
    height: 36,
    paddingHorizontal: spacing.lg,
    borderRadius: radius.pill,
    alignItems: "center",
    justifyContent: "center",
    borderWidth: 1,
    flexShrink: 0,
  },
  chipActive: { backgroundColor: colors.brandPrimary, borderColor: colors.brandPrimary },
  chipIdle: { backgroundColor: colors.surfaceSecondary, borderColor: colors.border },
  chipText: { fontSize: 13, fontWeight: "700", letterSpacing: 0.2 },
  chipTextActive: { color: colors.onBrandPrimary },
  chipTextIdle: { color: colors.onSurfaceSecondary },
});
