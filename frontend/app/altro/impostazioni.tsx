import React, { useCallback, useState } from "react";
import { View, Text, StyleSheet, ScrollView, Switch, Pressable } from "react-native";
import { useFocusEffect } from "expo-router";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { Feather } from "@expo/vector-icons";
import * as ImagePicker from "expo-image-picker";
import { Image } from "expo-image";
import { api, uploadImage } from "@/src/api";
import { useAuth } from "@/src/auth";
import { useAssistant } from "@/src/useAssistant";
import { colors, spacing, radius, type } from "@/src/theme";
import { SubHeader } from "@/src/components/SubHeader";
import { Loading, SectionTitle, Avatar } from "@/src/components/ui";

export default function Impostazioni() {
  const insets = useSafeAreaInsets();
  const { user } = useAuth();
  const isAdmin = user?.role === "admin";
  const { assistant, refresh } = useAssistant();
  const [uploadingAvatar, setUploadingAvatar] = useState(false);
  const [settings, setSettings] = useState<any>(null);
  const [followups, setFollowups] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    try {
      const [s, f] = await Promise.all([api.get("/settings"), api.get("/followups")]);
      setSettings(s);
      setFollowups(f);
    } catch {}
    setLoading(false);
  }, []);
  useFocusEffect(useCallback(() => { load(); }, [load]));

  const toggleNotif = async (key: string, value: boolean) => {
    const next = { ...settings, notifiche: { ...settings.notifiche, [key]: value } };
    setSettings(next);
    if (isAdmin) await api.patch("/settings", { notifiche: next.notifiche });
  };

  const toggleFollowups = async (value: boolean) => {
    const next = { ...followups, enabled: value };
    setFollowups(next);
    if (isAdmin) await api.patch("/followups", { enabled: value, steps: followups.steps });
  };

  const changeAssistantPhoto = async () => {
    const perm = await ImagePicker.requestMediaLibraryPermissionsAsync();
    if (!perm.granted) return;
    const res = await ImagePicker.launchImageLibraryAsync({ mediaTypes: ["images"], quality: 0.8 });
    if (res.canceled || !res.assets?.length) return;
    setUploadingAvatar(true);
    try {
      const up = await uploadImage(res.assets[0].uri, "andrea.jpg");
      await api.patch("/assistant", { avatar_url: up.url });
      await refresh();
    } catch {}
    setUploadingAvatar(false);
  };

  if (loading || !settings || !followups) {
    return <View style={{ flex: 1, backgroundColor: colors.surface }}><SubHeader title="Impostazioni" /><Loading /></View>;
  }

  return (
    <View style={{ flex: 1, backgroundColor: colors.surface }}>
      <SubHeader title="Impostazioni" />
      <ScrollView contentContainerStyle={{ padding: spacing.lg, paddingBottom: insets.bottom + spacing["2xl"] }} showsVerticalScrollIndicator={false}>
        {/* Account */}
        <SectionTitle>Account</SectionTitle>
        <View style={styles.card}>
          <Line label="Nome" value={user?.name || "—"} />
          <Line label="Email" value={user?.email || "—"} />
          <Line label="Ruolo" value={user?.role === "admin" ? "Admin" : "Operatore"} last />
        </View>

        {/* Sicurezza */}
        <SectionTitle>Sicurezza</SectionTitle>
        <View style={styles.card}>
          <View style={styles.secRow}>
            <Feather name="shield" size={16} color={colors.onSuccess} />
            <Text style={styles.secText}>Autenticazione JWT attiva · Ruoli Admin/Operatore separati</Text>
          </View>
          <View style={[styles.secRow, { marginTop: spacing.sm }]}>
            <Feather name="lock" size={16} color={colors.onSuccess} />
            <Text style={styles.secText}>Le API key restano lato server (mai nel frontend)</Text>
          </View>
        </View>

        {/* AI */}
        <SectionTitle>Assistente AI</SectionTitle>
        <View style={styles.card}>
          {assistant.avatarUri ? (
            <Image
              source={{ uri: assistant.avatarUri }}
              style={styles.assistantBanner}
              contentFit="cover"
              transition={200}
              testID="assistant-banner"
            />
          ) : null}
          <View style={styles.assistantRow}>
            <Avatar uri={assistant.avatarUri} name={assistant.name} size={56} position="top" />
            <View style={{ flex: 1 }}>
              <Text style={styles.assistantName}>{assistant.name}</Text>
              <Text style={styles.assistantRole}>Assistente commerciale · GPT-5.4</Text>
            </View>
            {isAdmin && (
              <Pressable onPress={changeAssistantPhoto} style={styles.changePhoto} testID="change-assistant-photo">
                <Feather name={uploadingAvatar ? "loader" : "camera"} size={15} color={colors.brandPrimary} />
                <Text style={styles.changePhotoText}>{uploadingAvatar ? "..." : "Cambia foto"}</Text>
              </Pressable>
            )}
          </View>
          <View style={styles.lineBorderTop}>
            <Line label="Stato" value="Attiva (GPT-5.4)" />
            <Line label="Handoff su prenotazione" value="Attivo" last />
          </View>
        </View>

        {/* Follow-up */}
        <SectionTitle>Follow-up automatici</SectionTitle>
        <View style={styles.card}>
          <View style={styles.toggleRow}>
            <Text style={styles.toggleLabel}>Follow-up attivi</Text>
            <Switch
              value={followups.enabled}
              onValueChange={toggleFollowups}
              trackColor={{ true: colors.brandPrimary, false: colors.surfaceTertiary }}
              thumbColor={colors.onSurface}
              disabled={!isAdmin}
              testID="toggle-followups"
            />
          </View>
          {followups.steps?.map((s: any, i: number) => (
            <View key={i} style={styles.step}>
              <View style={styles.stepDot}><Text style={styles.stepNum}>{i + 1}</Text></View>
              <View style={{ flex: 1 }}>
                <Text style={styles.stepLabel}>{s.label} · dopo {s.delay}</Text>
                <Text style={styles.stepMsg}>{s.message}</Text>
              </View>
            </View>
          ))}
          <Text style={styles.note}>Se il cliente risponde, i follow-up programmati vengono annullati automaticamente.</Text>
        </View>

        {/* Notifiche */}
        <SectionTitle>Notifiche</SectionTitle>
        <View style={styles.card}>
          <NotifToggle label="Cliente pronta da fissare" value={settings.notifiche?.cliente_da_fissare} onChange={(v) => toggleNotif("cliente_da_fissare", v)} disabled={!isAdmin} k="cliente_da_fissare" />
          <NotifToggle label="AI richiede intervento" value={settings.notifiche?.ai_intervento} onChange={(v) => toggleNotif("ai_intervento", v)} disabled={!isAdmin} k="ai_intervento" />
          <NotifToggle label="Nuova chat assegnata" value={settings.notifiche?.nuova_chat} onChange={(v) => toggleNotif("nuova_chat", v)} disabled={!isAdmin} k="nuova_chat" />
          <NotifToggle label="Nuovo messaggio operatore" value={settings.notifiche?.nuovo_messaggio} onChange={(v) => toggleNotif("nuovo_messaggio", v)} disabled={!isAdmin} k="nuovo_messaggio" last />
        </View>
      </ScrollView>
    </View>
  );
}

function Line({ label, value, last }: { label: string; value: string; last?: boolean }) {
  return (
    <View style={[styles.line, !last && styles.lineBorder]}>
      <Text style={styles.lineLabel}>{label}</Text>
      <Text style={styles.lineValue}>{value}</Text>
    </View>
  );
}

function NotifToggle({ label, value, onChange, disabled, k, last }: any) {
  return (
    <View style={[styles.toggleRow, !last && styles.lineBorder]}>
      <Text style={styles.toggleLabel}>{label}</Text>
      <Switch
        value={!!value}
        onValueChange={onChange}
        trackColor={{ true: colors.brandPrimary, false: colors.surfaceTertiary }}
        thumbColor={colors.onSurface}
        disabled={disabled}
        testID={`toggle-${k}`}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  card: { backgroundColor: colors.surfaceSecondary, borderRadius: radius.md, borderWidth: 1, borderColor: colors.border, paddingHorizontal: spacing.lg, marginBottom: spacing.lg },
  assistantRow: { flexDirection: "row", alignItems: "center", gap: spacing.md, paddingVertical: spacing.md },
  assistantBanner: { width: "100%", aspectRatio: 1, borderRadius: radius.sm, marginTop: spacing.md, backgroundColor: colors.surfaceTertiary },
  assistantName: { color: colors.onSurface, fontSize: type.lg, fontWeight: "700" },
  assistantRole: { color: colors.onSurfaceTertiary, fontSize: 12, marginTop: 2 },
  changePhoto: { flexDirection: "row", alignItems: "center", gap: 5, borderWidth: 1, borderColor: colors.borderStrong, borderRadius: radius.pill, paddingHorizontal: spacing.md, paddingVertical: 7 },
  changePhotoText: { color: colors.brandPrimary, fontSize: 12, fontWeight: "700" },
  lineBorderTop: { borderTopWidth: 1, borderTopColor: colors.divider },
  line: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", paddingVertical: spacing.md },
  lineBorder: { borderBottomWidth: 1, borderBottomColor: colors.divider },
  lineLabel: { color: colors.onSurfaceTertiary, fontSize: 13 },
  lineValue: { color: colors.onSurface, fontSize: 14, fontWeight: "600" },
  secRow: { flexDirection: "row", alignItems: "center", gap: spacing.sm, paddingVertical: spacing.md },
  secText: { color: colors.onSurfaceSecondary, fontSize: 12.5, flex: 1 },
  toggleRow: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", paddingVertical: spacing.md },
  toggleLabel: { color: colors.onSurface, fontSize: 14, fontWeight: "600", flex: 1 },
  step: { flexDirection: "row", gap: spacing.sm, paddingVertical: spacing.sm, borderTopWidth: 1, borderTopColor: colors.divider },
  stepDot: { width: 22, height: 22, borderRadius: 11, backgroundColor: colors.brandTertiary, alignItems: "center", justifyContent: "center" },
  stepNum: { color: colors.brandPrimary, fontSize: 11, fontWeight: "800" },
  stepLabel: { color: colors.onSurface, fontSize: 13, fontWeight: "700" },
  stepMsg: { color: colors.onSurfaceTertiary, fontSize: 12, marginTop: 2, lineHeight: 17 },
  note: { color: colors.onSurfaceTertiary, fontSize: 11.5, fontStyle: "italic", paddingVertical: spacing.md, lineHeight: 16 },
});
