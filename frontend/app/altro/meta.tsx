import React, { useCallback, useState } from "react";
import { View, Text, StyleSheet, Pressable, TextInput } from "react-native";
import { useFocusEffect, useRouter } from "expo-router";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { Feather } from "@expo/vector-icons";
import * as Clipboard from "expo-clipboard";
import * as Haptics from "expo-haptics";
import { KeyboardAwareScrollView } from "react-native-keyboard-controller";
import { api } from "@/src/api";
import { useAuth } from "@/src/auth";
import { colors, spacing, radius, type, font } from "@/src/theme";
import { SubHeader } from "@/src/components/SubHeader";
import { Loading, GoldButton } from "@/src/components/ui";

const WEBHOOK_URL = `${process.env.EXPO_PUBLIC_BACKEND_URL}/api/integrations/meta/webhook`;

const STEPS = [
  "Crea un'app su developers.facebook.com → My Apps → Create App (tipo Business).",
  "In Impostazioni → Base copia App ID e App Secret e inviameli.",
  "Aggiungi il prodotto Webhooks, oggetto Page, e incolla l'URL e il Verify Token qui sotto.",
  "Iscriviti al campo leadgen e collega la Pagina Facebook che possiede i moduli lead.",
  "Genera un Page Access Token (Graph API Explorer → me/accounts) e inviamelo insieme al Page ID.",
  "Completa la verifica del Business e l'App Review per il permesso leads_retrieval.",
];

export default function MetaSetup() {
  const insets = useSafeAreaInsets();
  const router = useRouter();
  const { user } = useAuth();
  const isAdmin = user?.role === "admin";
  const [status, setStatus] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [copied, setCopied] = useState("");
  const [banner, setBanner] = useState<string | null>(null);
  const [services, setServices] = useState<any[]>([]);
  const [locations, setLocations] = useState<any[]>([]);
  const [campaigns, setCampaigns] = useState<any[]>([]);

  const [form, setForm] = useState({
    nome: "", cognome: "", telefono: "", email: "",
    servizio: "", sede: "", campagna: "", inserzione: "",
    piattaforma: "Instagram", ig_username: "",
  });

  const load = useCallback(async () => {
    try {
      const [s, sv, lo, ca] = await Promise.all([
        api.get("/integrations/meta/status"),
        api.get("/services"),
        api.get("/locations"),
        api.get("/campaigns"),
      ]);
      setStatus(s);
      setServices(sv);
      setLocations(lo);
      setCampaigns(ca);
    } catch {}
    setLoading(false);
  }, []);
  useFocusEffect(useCallback(() => { load(); }, [load]));

  const copy = async (label: string, value: string) => {
    await Clipboard.setStringAsync(value);
    setCopied(label);
    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
    setTimeout(() => setCopied(""), 1500);
  };

  const simulate = async () => {
    if (!form.nome.trim()) { setBanner("Inserisci almeno il nome del lead."); return; }
    const res = await api.post("/integrations/meta/simulate", form);
    Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
    setForm({ ...form, nome: "", cognome: "", telefono: "", email: "", ig_username: "" });
    if (res.conversation_id) {
      router.push(`/conversation/${res.conversation_id}`);
    } else {
      setBanner("Lead creato e inserito in NUOVO LEAD.");
    }
  };

  if (loading || !status) {
    return <View style={{ flex: 1, backgroundColor: colors.surface }}><SubHeader title="Meta Lead Ads" /><Loading /></View>;
  }

  return (
    <View style={{ flex: 1, backgroundColor: colors.surface }}>
      <SubHeader title="Meta Lead Ads" />
      <KeyboardAwareScrollView
        contentContainerStyle={{ padding: spacing.lg, paddingBottom: insets.bottom + spacing["2xl"] }}
        bottomOffset={24}
        showsVerticalScrollIndicator={false}
      >
        {/* Status */}
        <View style={styles.statusCard}>
          <View style={styles.statusHead}>
            <View style={styles.fbIcon}><Feather name="facebook" size={18} color={colors.brandSecondary} /></View>
            <View style={{ flex: 1 }}>
              <Text style={styles.statusTitle}>Stato integrazione</Text>
              <Text style={styles.statusSub}>{status.configured ? "Configurata" : "Non attiva · Fase 2"}</Text>
            </View>
            <View style={[styles.statusPill, status.configured && { backgroundColor: colors.success }]}>
              <Text style={[styles.statusPillText, status.configured && { color: colors.onSuccess }]}>
                {status.configured ? "ATTIVA" : "NON ATTIVA"}
              </Text>
            </View>
          </View>
          <View style={styles.checkGrid}>
            <Check ok={status.app_id_set} label="App ID" />
            <Check ok={status.app_secret_set} label="App Secret" />
            <Check ok={status.page_token_set} label="Page Token" />
            <Check ok={status.page_id_set} label="Page ID" />
          </View>
        </View>

        {/* Config values */}
        <Text style={styles.sectionTitle}>Configurazione webhook</Text>
        <CopyRow label="Callback URL" value={WEBHOOK_URL} copied={copied === "url"} onCopy={() => copy("url", WEBHOOK_URL)} />
        {isAdmin && status.verify_token ? (
          <CopyRow label="Verify Token" value={status.verify_token} copied={copied === "vt"} onCopy={() => copy("vt", status.verify_token)} />
        ) : null}
        <CopyRow label="Campo da iscrivere" value={status.subscribe_field} copied={copied === "f"} onCopy={() => copy("f", status.subscribe_field)} />

        {/* Guide */}
        <Text style={styles.sectionTitle}>Come collegare Meta (guida)</Text>
        <View style={styles.guide}>
          {STEPS.map((s, i) => (
            <View key={i} style={styles.step}>
              <View style={styles.stepNum}><Text style={styles.stepNumText}>{i + 1}</Text></View>
              <Text style={styles.stepText}>{s}</Text>
            </View>
          ))}
          <Text style={styles.note}>
            Quando avrai App ID, App Secret, Page Access Token e Page ID, inviameli: li inserisco lato server
            e attiviamo la ricezione automatica dei lead.
          </Text>
        </View>

        {/* Simulatore */}
        {isAdmin && (
          <>
            <Text style={styles.sectionTitle}>Simulatore Lead Meta</Text>
            <View style={styles.simCard}>
              <Text style={styles.simHint}>
                Simula un lead in arrivo dalle campagne per testare l&apos;intero flusso Ads → Lead → Chat → AI,
                senza le API reali.
              </Text>
              {banner ? <Text style={styles.banner}>{banner}</Text> : null}
              <Row2>
                <Inp label="Nome*" value={form.nome} onChange={(v) => setForm({ ...form, nome: v })} />
                <Inp label="Cognome" value={form.cognome} onChange={(v) => setForm({ ...form, cognome: v })} />
              </Row2>
              <Row2>
                <Inp label="Telefono" value={form.telefono} onChange={(v) => setForm({ ...form, telefono: v })} />
                <Inp label="Email" value={form.email} onChange={(v) => setForm({ ...form, email: v })} />
              </Row2>

              <Picker label="Servizio" options={services.map((s) => s.nome)} value={form.servizio} onSelect={(v) => setForm({ ...form, servizio: v })} />
              <Picker label="Sede" options={locations.map((l) => l.nome)} value={form.sede} onSelect={(v) => setForm({ ...form, sede: v })} />
              <Picker label="Campagna" options={campaigns.map((c) => c.nome)} value={form.campagna} onSelect={(v) => setForm({ ...form, campagna: v })} />

              <Inp label="Inserzione / Creatività" value={form.inserzione} onChange={(v) => setForm({ ...form, inserzione: v })} />

              <Text style={styles.inpLabel}>Piattaforma</Text>
              <View style={styles.platRow}>
                {["Instagram", "Facebook"].map((p) => (
                  <Pressable key={p} onPress={() => setForm({ ...form, piattaforma: p })} style={[styles.platOpt, form.piattaforma === p && { backgroundColor: colors.brandPrimary, borderColor: colors.brandPrimary }]} testID={`plat-${p}`}>
                    <Feather name={p === "Facebook" ? "facebook" : "instagram"} size={14} color={form.piattaforma === p ? colors.onBrandPrimary : colors.onSurfaceSecondary} />
                    <Text style={[styles.platText, form.piattaforma === p && { color: colors.onBrandPrimary }]}>{p}</Text>
                  </Pressable>
                ))}
              </View>
              <Inp label="Username social (opzionale)" value={form.ig_username} onChange={(v) => setForm({ ...form, ig_username: v })} />

              <View style={{ marginTop: spacing.md }}>
                <GoldButton title="Simula lead in arrivo" icon="download" onPress={simulate} testID="simulate-meta-lead-button" />
              </View>
            </View>
          </>
        )}
      </KeyboardAwareScrollView>
    </View>
  );
}

function Check({ ok, label }: { ok: boolean; label: string }) {
  return (
    <View style={styles.check}>
      <Feather name={ok ? "check-circle" : "circle"} size={15} color={ok ? colors.onSuccess : colors.onSurfaceTertiary} />
      <Text style={[styles.checkLabel, ok && { color: colors.onSurface }]}>{label}</Text>
    </View>
  );
}

function CopyRow({ label, value, copied, onCopy }: any) {
  return (
    <View style={styles.copyRow}>
      <View style={{ flex: 1 }}>
        <Text style={styles.copyLabel}>{label}</Text>
        <Text style={styles.copyValue} numberOfLines={1}>{value}</Text>
      </View>
      <Pressable onPress={onCopy} style={styles.copyBtn} hitSlop={6} testID={`copy-${label}`}>
        <Feather name={copied ? "check" : "copy"} size={16} color={colors.brandPrimary} />
      </Pressable>
    </View>
  );
}

function Row2({ children }: { children: React.ReactNode }) {
  return <View style={{ flexDirection: "row", gap: spacing.sm }}>{children}</View>;
}

function Inp({ label, value, onChange }: { label: string; value: string; onChange: (v: string) => void }) {
  return (
    <View style={{ flex: 1, marginBottom: spacing.md }}>
      <Text style={styles.inpLabel}>{label}</Text>
      <TextInput value={value} onChangeText={onChange} style={styles.inp} placeholderTextColor={colors.onSurfaceTertiary} autoCapitalize="none" />
    </View>
  );
}

function Picker({ label, options, value, onSelect }: { label: string; options: string[]; value: string; onSelect: (v: string) => void }) {
  return (
    <View style={{ marginBottom: spacing.md }}>
      <Text style={styles.inpLabel}>{label}</Text>
      <View style={styles.pickWrap}>
        {options.map((o) => {
          const active = o === value;
          return (
            <Pressable key={o} onPress={() => onSelect(active ? "" : o)} style={[styles.pickChip, active && { backgroundColor: colors.brandPrimary, borderColor: colors.brandPrimary }]} testID={`pick-${o}`}>
              <Text style={[styles.pickText, active && { color: colors.onBrandPrimary }]} numberOfLines={1}>{o}</Text>
            </Pressable>
          );
        })}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  statusCard: { backgroundColor: colors.surfaceSecondary, borderRadius: radius.md, borderWidth: 1, borderColor: colors.border, padding: spacing.lg, marginBottom: spacing.lg },
  statusHead: { flexDirection: "row", alignItems: "center", gap: spacing.md },
  fbIcon: { width: 42, height: 42, borderRadius: radius.sm, backgroundColor: colors.surfaceTertiary, alignItems: "center", justifyContent: "center" },
  statusTitle: { color: colors.onSurface, fontSize: 15, fontWeight: "700" },
  statusSub: { color: colors.onSurfaceTertiary, fontSize: 12, marginTop: 2 },
  statusPill: { backgroundColor: colors.surfaceTertiary, paddingHorizontal: 10, paddingVertical: 5, borderRadius: radius.pill },
  statusPillText: { color: colors.onSurfaceTertiary, fontSize: 9, fontWeight: "800", letterSpacing: 0.5 },
  checkGrid: { flexDirection: "row", flexWrap: "wrap", gap: spacing.sm, marginTop: spacing.md },
  check: { flexDirection: "row", alignItems: "center", gap: 6, width: "47%" },
  checkLabel: { color: colors.onSurfaceTertiary, fontSize: 12.5, fontWeight: "600" },
  sectionTitle: { color: colors.onSurfaceTertiary, fontSize: 12, fontWeight: "700", letterSpacing: 1, textTransform: "uppercase", marginBottom: spacing.sm, marginTop: spacing.sm },
  copyRow: { flexDirection: "row", alignItems: "center", gap: spacing.sm, backgroundColor: colors.surfaceSecondary, borderRadius: radius.sm, borderWidth: 1, borderColor: colors.border, padding: spacing.md, marginBottom: spacing.sm },
  copyLabel: { color: colors.onSurfaceTertiary, fontSize: 11, fontWeight: "700" },
  copyValue: { color: colors.onSurface, fontSize: 12.5, marginTop: 2, fontFamily: font.display },
  copyBtn: { width: 36, height: 36, borderRadius: radius.sm, backgroundColor: colors.brandTertiary, alignItems: "center", justifyContent: "center" },
  guide: { backgroundColor: colors.surfaceSecondary, borderRadius: radius.md, borderWidth: 1, borderColor: colors.border, padding: spacing.lg, marginBottom: spacing.lg, gap: spacing.md },
  step: { flexDirection: "row", gap: spacing.sm },
  stepNum: { width: 22, height: 22, borderRadius: 11, backgroundColor: colors.brandTertiary, alignItems: "center", justifyContent: "center" },
  stepNumText: { color: colors.brandPrimary, fontSize: 11, fontWeight: "800" },
  stepText: { color: colors.onSurfaceSecondary, fontSize: 13, flex: 1, lineHeight: 19 },
  note: { color: colors.onSurfaceTertiary, fontSize: 12, fontStyle: "italic", lineHeight: 18, borderTopWidth: 1, borderTopColor: colors.divider, paddingTop: spacing.md },
  simCard: { backgroundColor: colors.surfaceSecondary, borderRadius: radius.md, borderWidth: 1, borderColor: colors.borderStrong, padding: spacing.lg },
  simHint: { color: colors.onSurfaceTertiary, fontSize: 12.5, lineHeight: 18, marginBottom: spacing.md },
  banner: { color: colors.onWarning, backgroundColor: colors.warning, fontSize: 12.5, padding: spacing.sm, borderRadius: radius.sm, marginBottom: spacing.md },
  inpLabel: { color: colors.onSurfaceSecondary, fontSize: 12, fontWeight: "700", marginBottom: 6 },
  inp: { color: colors.onSurface, fontSize: type.base, backgroundColor: colors.surface, borderRadius: radius.sm, borderWidth: 1, borderColor: colors.border, paddingHorizontal: spacing.md, paddingVertical: 10 },
  platRow: { flexDirection: "row", gap: spacing.sm, marginBottom: spacing.md },
  platOpt: { flex: 1, flexDirection: "row", alignItems: "center", justifyContent: "center", gap: 6, paddingVertical: 11, borderRadius: radius.sm, borderWidth: 1, borderColor: colors.border, backgroundColor: colors.surface },
  platText: { color: colors.onSurfaceSecondary, fontSize: 13, fontWeight: "700" },
  pickWrap: { flexDirection: "row", flexWrap: "wrap", gap: spacing.sm },
  pickChip: { paddingHorizontal: spacing.md, paddingVertical: 8, borderRadius: radius.pill, borderWidth: 1, borderColor: colors.border, backgroundColor: colors.surface, maxWidth: "100%" },
  pickText: { color: colors.onSurfaceSecondary, fontSize: 12.5, fontWeight: "600" },
});
