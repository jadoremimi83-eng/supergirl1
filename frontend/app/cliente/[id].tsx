import React, { useCallback, useState } from "react";
import { View, Text, StyleSheet, Pressable, TextInput } from "react-native";
import { KeyboardAwareScrollView } from "react-native-keyboard-controller";
import { useLocalSearchParams, useRouter, useFocusEffect } from "expo-router";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { Feather } from "@expo/vector-icons";
import * as Haptics from "expo-haptics";
import { api } from "@/src/api";
import { colors, spacing, radius, type, font, STAGES, TEMP, tempOf, stageOf } from "@/src/theme";
import { Avatar, TempBadge, StageBadge, Loading, Sheet, GoldButton, SectionTitle } from "@/src/components/ui";

export default function Cliente() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const insets = useSafeAreaInsets();
  const router = useRouter();
  const [lead, setLead] = useState<any>(null);
  const [convId, setConvId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [notes, setNotes] = useState("");
  const [noteSaved, setNoteSaved] = useState(false);
  const [stageSheet, setStageSheet] = useState(false);
  const [tempSheet, setTempSheet] = useState(false);

  const load = useCallback(async () => {
    try {
      const res = await api.get(`/leads/${id}`);
      setLead(res.lead);
      setConvId(res.conversation_id);
      setNotes(res.lead.note_staff || "");
    } catch {}
    setLoading(false);
  }, [id]);

  useFocusEffect(
    useCallback(() => {
      load();
    }, [load])
  );

  const saveNotes = async () => {
    await api.patch(`/leads/${id}`, { note_staff: notes });
    setNoteSaved(true);
    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
    setTimeout(() => setNoteSaved(false), 1800);
  };

  const changeStage = async (stato: string) => {
    setStageSheet(false);
    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium);
    await api.post(`/leads/${id}/status`, { stato });
    load();
  };

  const changeTemp = async (temperature: string) => {
    setTempSheet(false);
    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium);
    await api.patch(`/leads/${id}`, { temperature });
    load();
  };

  const changeTipo = async (tipo: string) => {
    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
    setLead((prev: any) => ({ ...prev, tipo }));
    await api.patch(`/leads/${id}`, { tipo });
  };

  if (loading || !lead) {
    return (
      <View style={{ flex: 1, backgroundColor: colors.surface, paddingTop: insets.top }}>
        <Loading />
      </View>
    );
  }

  return (
    <View style={{ flex: 1, backgroundColor: colors.surface }}>
      <View style={[styles.topBar, { paddingTop: insets.top + spacing.sm }]}>
        <Pressable testID="cliente-back" onPress={() => router.back()} hitSlop={10}>
          <Feather name="chevron-left" size={26} color={colors.onSurface} />
        </Pressable>
        <Text style={styles.topTitle}>Scheda Cliente</Text>
        <View style={{ width: 26 }} />
      </View>

      <KeyboardAwareScrollView
        contentContainerStyle={{ padding: spacing.lg, paddingBottom: insets.bottom + spacing["2xl"] }}
        bottomOffset={20}
        showsVerticalScrollIndicator={false}
      >
        {/* Identità */}
        <View style={styles.identity}>
          <Avatar uri={lead.foto_profilo} name={`${lead.nome} ${lead.cognome}`} size={72} />
          <Text style={styles.name}>
            {lead.nome} {lead.cognome}
          </Text>
          {(lead.ig_username || lead.ig_display_name) && (
            <View style={styles.socialRow}>
              <Feather
                name={lead.piattaforma === "Facebook" ? "facebook" : "instagram"}
                size={13}
                color={colors.brandSecondary}
              />
              <Text style={styles.social}>
                {lead.ig_username || lead.ig_display_name}
                {lead.ig_display_name && lead.ig_username ? ` · ${lead.ig_display_name}` : ""}
              </Text>
            </View>
          )}
          <View style={styles.identityBadges}>
            <Pressable onPress={() => setStageSheet(true)} testID="open-stage-sheet">
              <StageBadge stage={lead.stato_pipeline} />
            </Pressable>
            <Pressable onPress={() => setTempSheet(true)} testID="open-temp-sheet">
              <TempBadge temp={lead.temperature} />
            </Pressable>
          </View>
        </View>

        {/* Tipo lead: Corso vs Trattamento */}
        <View style={styles.tipoBox}>
          <Text style={styles.tipoLbl}>TIPO LEAD</Text>
          <View style={styles.tipoRow}>
            {["trattamento", "corso"].map((t) => {
              const on = (lead.tipo || "trattamento") === t;
              return (
                <Pressable key={t} onPress={() => changeTipo(t)} testID={`lead-tipo-${t}`}
                  style={[styles.tipoChip, on && styles.tipoChipOn]}>
                  <Feather name={t === "corso" ? "award" : "star"} size={13} color={on ? colors.onBrandPrimary : colors.onSurfaceSecondary} />
                  <Text style={[styles.tipoChipTxt, on && styles.tipoChipTxtOn]}>
                    {t === "corso" ? "Corso" : "Trattamento"}
                  </Text>
                </Pressable>
              );
            })}
          </View>
          <Text style={styles.tipoHint}>
            {(lead.tipo || "trattamento") === "corso"
              ? "Andrea agisce come Academy Manager: qualifica e fissa la chiamata corso."
              : "Andrea gestisce la chat e passa il lead allo staff (Da richiamare)."}
          </Text>
        </View>

        {/* Azioni */}
        <View style={styles.actions}>
          <View style={{ flex: 1 }}>
            <GoldButton
              title="Conversazione"
              icon="message-circle"
              onPress={() => convId && router.push(`/conversation/${convId}`)}
              testID="open-conversation-button"
            />
          </View>
          <View style={{ flex: 1 }}>
            <GoldButton
              title="Cambia Stato"
              icon="git-branch"
              variant="outline"
              onPress={() => setStageSheet(true)}
              testID="change-stage-button"
            />
          </View>
        </View>

        {/* DATI */}
        <View style={styles.section}>
          <SectionTitle>Dati</SectionTitle>
          <Row label="Telefono" value={lead.telefono} icon="phone" />
          <Row label="Email" value={lead.email} icon="mail" />
          <Row label="Sede" value={lead.sede} icon="map-pin" />
          <Row label="Servizio" value={lead.servizio} icon="star" />
          <Row label="Piattaforma" value={lead.piattaforma} icon="share-2" />
          <Row label="Campagna" value={lead.campagna} icon="target" />
          <Row label="Inserzione" value={lead.inserzione} icon="image" />
          <Row label="Acquisizione" value={fmtDate(lead.data_acquisizione)} icon="calendar" />
          <Row label="Ultimo contatto" value={fmtDate(lead.ultimo_contatto)} icon="clock" last />
        </View>

        {/* RIASSUNTO AI */}
        <View style={styles.section}>
          <View style={styles.aiHead}>
            <SectionTitle>Riassunto AI</SectionTitle>
            <View style={styles.aiChip}>
              <Feather name="cpu" size={11} color={colors.brandPrimary} />
              <Text style={styles.aiChipText}>SUPER GIRL</Text>
            </View>
          </View>
          {lead.ai_summary ? (
            <View style={styles.summaryBox}>
              <Text style={styles.summaryText}>{lead.ai_summary}</Text>
            </View>
          ) : (
            <Text style={styles.placeholder}>
              Il riassunto verrà generato automaticamente quando la cliente sarà pronta per essere fissata.
            </Text>
          )}
        </View>

        {/* NOTE STAFF */}
        <View style={styles.section}>
          <SectionTitle>Note Staff</SectionTitle>
          <TextInput
            testID="staff-notes-input"
            value={notes}
            onChangeText={setNotes}
            placeholder="Aggiungi una nota interna…"
            placeholderTextColor={colors.onSurfaceTertiary}
            style={styles.notes}
            multiline
          />
          <GoldButton
            title={noteSaved ? "Salvato ✓" : "Salva nota"}
            icon={noteSaved ? "check" : "save"}
            variant="outline"
            small
            onPress={saveNotes}
            testID="save-notes-button"
          />
        </View>
      </KeyboardAwareScrollView>

      {/* Sheet cambia stato */}
      <Sheet visible={stageSheet} onClose={() => setStageSheet(false)} title="Cambia stato pipeline">
        {Object.keys(STAGES).map((k) => {
          const s = STAGES[k];
          const active = k === lead.stato_pipeline;
          return (
            <Pressable
              key={k}
              testID={`stage-option-${k}`}
              onPress={() => changeStage(k)}
              style={[styles.optionRow, active && { borderColor: s.accent, backgroundColor: colors.brandTertiary }]}
            >
              <View style={[styles.optDot, { backgroundColor: s.accent }]} />
              <Text style={[styles.optText, active && { color: colors.onSurface, fontWeight: "700" }]}>
                {s.label}
              </Text>
              {active && <Feather name="check" size={18} color={s.accent} />}
            </Pressable>
          );
        })}
      </Sheet>

      {/* Sheet temperatura */}
      <Sheet visible={tempSheet} onClose={() => setTempSheet(false)} title="Temperatura lead">
        {Object.keys(TEMP).map((k) => {
          const t = (TEMP as any)[k];
          const active = k === lead.temperature;
          return (
            <Pressable
              key={k}
              testID={`temp-option-${k}`}
              onPress={() => changeTemp(k)}
              style={[styles.optionRow, active && { borderColor: t.bg, backgroundColor: colors.surfaceTertiary }]}
            >
              <View style={[styles.optDot, { backgroundColor: t.fg }]} />
              <Text style={[styles.optText, active && { color: colors.onSurface, fontWeight: "700" }]}>{t.label}</Text>
              {active && <Feather name="check" size={18} color={t.fg} />}
            </Pressable>
          );
        })}
      </Sheet>
    </View>
  );
}

function Row({ label, value, icon, last }: { label: string; value?: string; icon: any; last?: boolean }) {
  return (
    <View style={[rowStyles.row, !last && rowStyles.border]}>
      <Feather name={icon} size={16} color={colors.onSurfaceTertiary} />
      <Text style={rowStyles.label}>{label}</Text>
      <Text style={rowStyles.value} numberOfLines={1}>
        {value || "—"}
      </Text>
    </View>
  );
}

function fmtDate(iso?: string) {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString("it-IT", { day: "2-digit", month: "short", year: "numeric" });
}

const rowStyles = StyleSheet.create({
  row: { flexDirection: "row", alignItems: "center", gap: spacing.sm, paddingVertical: spacing.md },
  border: { borderBottomWidth: 1, borderBottomColor: colors.divider },
  label: { color: colors.onSurfaceTertiary, fontSize: 13, width: 110 },
  value: { color: colors.onSurface, fontSize: 14, fontWeight: "600", flex: 1, textAlign: "right" },
});

const styles = StyleSheet.create({
  topBar: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingHorizontal: spacing.md,
    paddingBottom: spacing.md,
    borderBottomWidth: 1,
    borderBottomColor: colors.divider,
  },
  topTitle: { color: colors.onSurface, fontSize: type.lg, fontWeight: "700" },
  identity: { alignItems: "center", gap: spacing.sm, marginBottom: spacing.xl },
  name: { color: colors.onSurface, fontSize: type["2xl"], fontWeight: "700", fontFamily: font.display, marginTop: spacing.sm },
  socialRow: { flexDirection: "row", alignItems: "center", gap: 6 },
  social: { color: colors.brandSecondary, fontSize: 13, fontWeight: "600" },
  identityBadges: { flexDirection: "row", gap: spacing.sm, marginTop: spacing.sm, flexWrap: "wrap", justifyContent: "center" },
  actions: { flexDirection: "row", gap: spacing.md, marginBottom: spacing.xl },
  tipoBox: { backgroundColor: colors.surfaceSecondary, borderRadius: radius.md, borderWidth: 1, borderColor: colors.border, padding: spacing.lg, marginBottom: spacing.lg },
  tipoLbl: { color: colors.onSurfaceTertiary, fontSize: 10, fontWeight: "800", letterSpacing: 1, marginBottom: spacing.sm },
  tipoRow: { flexDirection: "row", gap: spacing.sm },
  tipoChip: { flexDirection: "row", alignItems: "center", gap: 6, flex: 1, justifyContent: "center", paddingVertical: 10, borderRadius: radius.sm, borderWidth: 1, borderColor: colors.border, backgroundColor: colors.surface },
  tipoChipOn: { backgroundColor: colors.brandPrimary, borderColor: colors.brandPrimary },
  tipoChipTxt: { color: colors.onSurfaceSecondary, fontSize: 13.5, fontWeight: "700" },
  tipoChipTxtOn: { color: colors.onBrandPrimary },
  tipoHint: { color: colors.onSurfaceTertiary, fontSize: 12, lineHeight: 17, marginTop: spacing.sm },
  section: {
    backgroundColor: colors.surfaceSecondary,
    borderRadius: radius.md,
    borderWidth: 1,
    borderColor: colors.border,
    padding: spacing.lg,
    marginBottom: spacing.lg,
  },
  aiHead: { flexDirection: "row", alignItems: "center", justifyContent: "space-between" },
  aiChip: {
    flexDirection: "row",
    alignItems: "center",
    gap: 4,
    backgroundColor: colors.brandTertiary,
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: radius.pill,
    marginBottom: spacing.sm,
  },
  aiChipText: { color: colors.brandPrimary, fontSize: 10, fontWeight: "800", letterSpacing: 0.5 },
  summaryBox: {
    backgroundColor: colors.brandTertiary,
    borderRadius: radius.sm,
    borderWidth: 1,
    borderColor: colors.borderStrong,
    padding: spacing.md,
  },
  summaryText: { color: colors.onBrandTertiary, fontSize: 13.5, lineHeight: 21 },
  placeholder: { color: colors.onSurfaceTertiary, fontSize: 13, lineHeight: 19, fontStyle: "italic" },
  notes: {
    color: colors.onSurface,
    fontSize: type.base,
    backgroundColor: colors.surface,
    borderRadius: radius.sm,
    borderWidth: 1,
    borderColor: colors.border,
    padding: spacing.md,
    minHeight: 90,
    textAlignVertical: "top",
    marginBottom: spacing.md,
  },
  optionRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.md,
    paddingVertical: spacing.md,
    paddingHorizontal: spacing.md,
    borderRadius: radius.md,
    borderWidth: 1,
    borderColor: colors.border,
    marginBottom: spacing.sm,
  },
  optDot: { width: 10, height: 10, borderRadius: 5 },
  optText: { color: colors.onSurfaceSecondary, fontSize: 14, flex: 1 },
});
