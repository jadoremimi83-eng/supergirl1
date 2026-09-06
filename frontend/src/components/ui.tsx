import React from "react";
import {
  View,
  Text,
  StyleSheet,
  Pressable,
  Modal,
  ScrollView,
  ActivityIndicator,
  KeyboardAvoidingView as RNKeyboardAvoidingView,
  Platform,
} from "react-native";
import { Image } from "expo-image";
import { Feather } from "@expo/vector-icons";
import { colors, spacing, radius, type, font, tempOf, stageOf } from "@/src/theme";

// ---------------------------------------------------------------- Avatar
export function Avatar({
  uri,
  name,
  size = 48,
  position,
}: {
  uri?: string | null;
  name?: string;
  size?: number;
  position?: "top" | "center" | "bottom";
}) {
  const initials = (name || "")
    .split(" ")
    .map((w) => w[0])
    .filter(Boolean)
    .slice(0, 2)
    .join("")
    .toUpperCase();
  if (uri) {
    return (
      <Image
        source={{ uri }}
        style={{ width: size, height: size, borderRadius: size / 2, backgroundColor: colors.surfaceTertiary }}
        contentFit="cover"
        contentPosition={position || "center"}
        transition={200}
      />
    );
  }
  return (
    <View
      style={[
        styles.avatarFallback,
        { width: size, height: size, borderRadius: size / 2 },
      ]}
    >
      {initials ? (
        <Text style={{ color: colors.onBrandTertiary, fontWeight: "700", fontSize: size * 0.34 }}>
          {initials}
        </Text>
      ) : (
        <Feather name="user" size={size * 0.5} color={colors.onSurfaceTertiary} />
      )}
    </View>
  );
}

// ---------------------------------------------------------------- Badges
export function TempBadge({ temp, small }: { temp?: string | null; small?: boolean }) {
  const t = tempOf(temp);
  return (
    <View style={[styles.pill, { backgroundColor: t.bg }, small && styles.pillSm]} testID={`temp-badge-${temp}`}>
      <View style={[styles.dot, { backgroundColor: t.fg }]} />
      <Text style={[styles.pillText, { color: t.fg }, small && { fontSize: 10 }]}>{t.label}</Text>
    </View>
  );
}

export function StageBadge({ stage }: { stage?: string | null }) {
  const s = stageOf(stage);
  return (
    <View style={[styles.stagePill, { borderColor: s.accent }]}>
      <View style={[styles.dot, { backgroundColor: s.accent }]} />
      <Text style={[styles.stageText, { color: s.accent }]}>{s.short}</Text>
    </View>
  );
}

export function AiBadge({ active }: { active: boolean }) {
  return (
    <View
      style={[
        styles.aiBadge,
        { backgroundColor: active ? colors.brandTertiary : colors.surfaceTertiary },
      ]}
    >
      <Feather
        name={active ? "cpu" : "user"}
        size={12}
        color={active ? colors.onBrandTertiary : colors.onSurfaceTertiary}
      />
      <Text
        style={[
          styles.aiBadgeText,
          { color: active ? colors.onBrandTertiary : colors.onSurfaceTertiary },
        ]}
      >
        {active ? "AI ATTIVA" : "OPERATORE"}
      </Text>
    </View>
  );
}

// ---------------------------------------------------------------- Button
export function GoldButton({
  title,
  onPress,
  icon,
  variant = "solid",
  testID,
  disabled,
  small,
}: {
  title: string;
  onPress: () => void;
  icon?: any;
  variant?: "solid" | "outline" | "ghost";
  testID?: string;
  disabled?: boolean;
  small?: boolean;
}) {
  const isSolid = variant === "solid";
  const isOutline = variant === "outline";
  return (
    <Pressable
      testID={testID}
      onPress={onPress}
      disabled={disabled}
      style={({ pressed }) => [
        styles.btn,
        small && styles.btnSm,
        isSolid && { backgroundColor: colors.brandPrimary },
        isOutline && { borderWidth: 1, borderColor: colors.borderStrong },
        variant === "ghost" && { backgroundColor: "transparent" },
        pressed && { opacity: 0.85 },
        disabled && { opacity: 0.4 },
      ]}
    >
      {icon && (
        <Feather
          name={icon}
          size={small ? 15 : 17}
          color={isSolid ? colors.onBrandPrimary : colors.brandPrimary}
        />
      )}
      <Text
        style={[
          styles.btnText,
          small && { fontSize: 13 },
          { color: isSolid ? colors.onBrandPrimary : colors.brandPrimary },
        ]}
      >
        {title}
      </Text>
    </Pressable>
  );
}

// ---------------------------------------------------------------- Sheet
export function Sheet({
  visible,
  onClose,
  title,
  children,
}: {
  visible: boolean;
  onClose: () => void;
  title?: string;
  children: React.ReactNode;
}) {
  return (
    <Modal visible={visible} transparent animationType="slide" onRequestClose={onClose}>
      <RNKeyboardAvoidingView
        behavior={Platform.OS === "ios" ? "padding" : undefined}
        style={styles.sheetRoot}
      >
        <Pressable style={styles.backdropAbs} onPress={onClose} testID="sheet-backdrop" />
        <View style={styles.sheet}>
          <View style={styles.sheetHandle} />
          {title ? (
            <View style={styles.sheetHeader}>
              <Text style={styles.sheetTitle}>{title}</Text>
              <Pressable onPress={onClose} hitSlop={10} testID="sheet-close">
                <Feather name="x" size={22} color={colors.onSurfaceSecondary} />
              </Pressable>
            </View>
          ) : null}
          <ScrollView showsVerticalScrollIndicator={false} keyboardShouldPersistTaps="handled">
            {children}
          </ScrollView>
        </View>
      </RNKeyboardAvoidingView>
    </Modal>
  );
}

// ---------------------------------------------------------------- States
export function Loading({ label }: { label?: string }) {
  return (
    <View style={styles.center}>
      <ActivityIndicator color={colors.brandPrimary} size="large" />
      {label ? <Text style={styles.stateText}>{label}</Text> : null}
    </View>
  );
}

export function EmptyState({ icon = "inbox", title, subtitle }: { icon?: any; title: string; subtitle?: string }) {
  return (
    <View style={styles.center}>
      <View style={styles.emptyIcon}>
        <Feather name={icon} size={30} color={colors.onSurfaceTertiary} />
      </View>
      <Text style={styles.emptyTitle}>{title}</Text>
      {subtitle ? <Text style={styles.stateText}>{subtitle}</Text> : null}
    </View>
  );
}

export function SectionTitle({ children }: { children: React.ReactNode }) {
  return <Text style={styles.sectionTitle}>{children}</Text>;
}

export function Card({ children, style }: { children: React.ReactNode; style?: any }) {
  return <View style={[styles.card, style]}>{children}</View>;
}

const styles = StyleSheet.create({
  avatarFallback: {
    backgroundColor: colors.brandTertiary,
    alignItems: "center",
    justifyContent: "center",
  },
  pill: {
    flexDirection: "row",
    alignItems: "center",
    gap: 5,
    paddingHorizontal: 9,
    paddingVertical: 4,
    borderRadius: radius.pill,
    alignSelf: "flex-start",
  },
  pillSm: { paddingHorizontal: 7, paddingVertical: 3 },
  pillText: { fontSize: 11, fontWeight: "700", letterSpacing: 0.3 },
  dot: { width: 6, height: 6, borderRadius: 3 },
  stagePill: {
    flexDirection: "row",
    alignItems: "center",
    gap: 5,
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: radius.pill,
    borderWidth: 1,
    alignSelf: "flex-start",
  },
  stageText: { fontSize: 10.5, fontWeight: "700", letterSpacing: 0.2 },
  aiBadge: {
    flexDirection: "row",
    alignItems: "center",
    gap: 5,
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: radius.pill,
  },
  aiBadgeText: { fontSize: 10.5, fontWeight: "800", letterSpacing: 0.4 },
  btn: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 8,
    paddingVertical: 14,
    paddingHorizontal: 18,
    borderRadius: radius.md,
  },
  btnSm: { paddingVertical: 9, paddingHorizontal: 12 },
  btnText: { fontSize: 15, fontWeight: "700", letterSpacing: 0.3 },
  backdrop: { flex: 1, backgroundColor: "rgba(0,0,0,0.65)" },
  sheetRoot: { flex: 1, justifyContent: "flex-end" },
  backdropAbs: { ...StyleSheet.absoluteFillObject, backgroundColor: "rgba(0,0,0,0.65)" },
  sheet: {
    backgroundColor: colors.surfaceSecondary,
    borderTopLeftRadius: radius.lg,
    borderTopRightRadius: radius.lg,
    paddingHorizontal: spacing.lg,
    paddingBottom: spacing["2xl"],
    paddingTop: spacing.sm,
    maxHeight: "85%",
    borderTopWidth: 1,
    borderColor: colors.border,
  },
  sheetHandle: {
    width: 40,
    height: 4,
    borderRadius: 2,
    backgroundColor: colors.border,
    alignSelf: "center",
    marginBottom: spacing.md,
  },
  sheetHeader: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    marginBottom: spacing.md,
  },
  sheetTitle: { color: colors.onSurface, fontSize: type.lg, fontWeight: "700" },
  center: { flex: 1, alignItems: "center", justifyContent: "center", padding: spacing.xl, gap: spacing.sm },
  stateText: { color: colors.onSurfaceTertiary, fontSize: type.base, textAlign: "center" },
  emptyIcon: {
    width: 64,
    height: 64,
    borderRadius: 32,
    backgroundColor: colors.surfaceTertiary,
    alignItems: "center",
    justifyContent: "center",
    marginBottom: spacing.sm,
  },
  emptyTitle: { color: colors.onSurface, fontSize: type.lg, fontWeight: "700", fontFamily: font.display },
  sectionTitle: {
    color: colors.onSurfaceTertiary,
    fontSize: 12,
    fontWeight: "700",
    letterSpacing: 1,
    textTransform: "uppercase",
    marginBottom: spacing.sm,
  },
  card: {
    backgroundColor: colors.surfaceSecondary,
    borderRadius: radius.md,
    borderWidth: 1,
    borderColor: colors.border,
    padding: spacing.lg,
  },
});
