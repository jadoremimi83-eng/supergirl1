import React, { useCallback, useState } from "react";
import { View, Text, StyleSheet, Pressable, TextInput } from "react-native";
import { useFocusEffect } from "expo-router";
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

const WEBHOOK_URL = `${process.env.EXPO_PUBLIC_BACKEND_URL}/api/integrations/whatsapp/webhook`;

export default function WhatsAppSettings() {
  const insets = useSafeAreaInsets();
  const { user } = useAuth();
  const isAdmin = user?.role === "admin";
  const [cfg, setCfg] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [form, setForm] = useState<any>({});
  const [saved, setSaved] = useState(false);
  const [copied, setCopied] = useState("");

  const load = useCallback(async () => {
    try {
      const c = await api.get("/integrations/whatsapp/config");
      setCfg(c);
      setForm({
        numero: c.numero || "", phone_number_id: c.phone_number_id || "",
        waba_id: c.waba_id || "", template_name: c.template_name || "",
        template_language: c.template_language || "it", token: "", app_secret: "",
        verify_token: c.verify_token || "",
      });
    } catch {
      // Fallback (es. Operatore senza permessi): la schermata resta usabile
      setCfg({
        configured: false, numero: "", phone_number_id: "", waba_id: "",
        template_name: "nuovo_lead_foto", template_language: "it",
        verify_token: "", token_masked: null, app_secret_masked: null,
      });
      setForm({
        numero: "", phone_number_id: "", waba_id: "",
        template_name: "nuovo_lead_foto", template_language: "it",
        token: "", app_secret: "", verify_token: "",
      });
    }
    setLoading(false);
  }, []);
  useFocusEffect(useCallback(() => { load(); }, [load]));

  const save = async () => {
    const payload: any = {};
    ["numero", "phone_number_id", "waba_id", "template_name", "template_language", "verify_token"].forEach((k) => {
      if (form[k] !== undefined) payload[k] = form[k];
    });
    if (form.token) payload.token = form.token;
    if (form.app_secret) payload.app_secret = form.app_secret;
    const c = await api.patch("/integrations/whatsapp/config", payload);
    setCfg(c);
    setForm({ ...form, token: "", app_secret: "" });
    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
    setSaved(true);
    setTimeout(() => setSaved(false), 1800);
  };

  const copy = async (label: string, value: string) => {
    await Clipboard.setStringAsync(value);
    setCopied(label);
    setTimeout(() => setCopied(""), 1500);
  };

  if (loading || !cfg) {
    return <View style={{ flex: 1, backgroundColor: colors.surface }}><SubHeader title="WhatsApp Business" /><Loading /></View>;
  }
  return (
    <View style={{ flex: 1, backgroundColor: colors.surface }}>
      <SubHeader title="WhatsApp Business" />
      <KeyboardAwareScrollView
        contentContainerStyle={{ padding: spacing.lg, paddingBottom: insets.bottom + spacing["2xl"] }}
        bottomOffset={24}
        showsVerticalScrollIndicator={false}
      >
        <View style={[styles.statusCard, cfg.configured && styles.statusOk]}>
          <Feather name={cfg.configured ? "check-circle" : "alert-circle"} size={18} color={cfg.configured ? colors.onSuccess : colors.onWarning} />
          <Text style={styles.statusText}>
            {cfg.configured
              ? `Collegato al numero ${cfg.numero || "(impostato)"}`
              : "Non ancora collegato · inserisci le credenziali sotto"}
          </Text>
        </View>

        <Text style={styles.hint}>
          Puoi collegare prima il tuo numero WhatsApp personale per testare, poi sostituirlo con il
          numero Business di J&apos;adore Mimì — da qui, senza modificare il codice.
        </Text>

        {isAdmin ? (
          <>
            <Field label="Numero WhatsApp (visualizzato)" value={form.numero} onChange={(v: string) => setForm({ ...form, numero: v })} placeholder="+39 333 ..." />
            <Field label="Phone Number ID" value={form.phone_number_id} onChange={(v: string) => setForm({ ...form, phone_number_id: v })} />
            <Field label="WABA ID" value={form.waba_id} onChange={(v: string) => setForm({ ...form, waba_id: v })} />
            <Field label={`Access Token ${cfg.token_masked ? "(impostato: " + cfg.token_masked + ")" : ""}`} value={form.token} onChange={(v: string) => setForm({ ...form, token: v })} placeholder="Lascia vuoto per non modificare" secure />
            <Field label={`App Secret ${cfg.app_secret_masked ? "(impostato)" : ""}`} value={form.app_secret} onChange={(v: string) => setForm({ ...form, app_secret: v })} placeholder="Lascia vuoto per non modificare" secure />
            <Field label="Nome template (immagine)" value={form.template_name} onChange={(v: string) => setForm({ ...form, template_name: v })} />
            <Field label="Lingua template" value={form.template_language} onChange={(v: string) => setForm({ ...form, template_language: v })} />
            <Field label="Verify Token (per la verifica su Meta)" value={form.verify_token} onChange={(v: string) => setForm({ ...form, verify_token: v })} placeholder="es. supergirl2026" />
            <Text style={styles.fieldHint}>Usa un token corto e semplice (solo lettere/numeri): lo digiterai a mano su Meta, senza rischio di spazi nascosti.</Text>
            <GoldButton title={saved ? "Salvato ✓" : "Salva credenziali"} icon={saved ? "check" : "save"} onPress={save} testID="save-wa-config" />
          </>
        ) : (
          <Text style={styles.readonly}>Solo gli Admin possono modificare le credenziali WhatsApp.</Text>
        )}

        <Text style={styles.sectionTitle}>Webhook (da configurare su Meta)</Text>
        <CopyRow label="Callback URL" value={WEBHOOK_URL} copied={copied === "url"} onCopy={() => copy("url", WEBHOOK_URL)} />
        <CopyRow label="Verify Token" value={cfg.verify_token} copied={copied === "vt"} onCopy={() => copy("vt", cfg.verify_token)} />

        <View style={styles.note}>
          <Feather name="info" size={15} color={colors.onInfo} />
          <Text style={styles.noteText}>
            Il primo messaggio con foto richiede un template approvato da Meta (categoria UTILITY/MARKETING).
            Dopo la risposta della cliente, l&apos;AI risponde in tempo reale entro la finestra di 24h.
          </Text>
        </View>
      </KeyboardAwareScrollView>
    </View>
  );
}

function Field({ label, value, onChange, placeholder, secure }: any) {
  return (
    <View style={{ marginBottom: spacing.md }}>
      <Text style={styles.label}>{label}</Text>
      <TextInput
        value={value}
        onChangeText={onChange}
        placeholder={placeholder}
        placeholderTextColor={colors.onSurfaceTertiary}
        secureTextEntry={secure}
        autoCapitalize="none"
        style={styles.input}
      />
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
      <Pressable onPress={onCopy} style={styles.copyBtn} hitSlop={6} testID={`copy-wa-${label}`}>
        <Feather name={copied ? "check" : "copy"} size={16} color={colors.brandPrimary} />
      </Pressable>
    </View>
  );
}

const styles = StyleSheet.create({
  statusCard: { flexDirection: "row", alignItems: "center", gap: spacing.sm, backgroundColor: colors.warning, borderRadius: radius.sm, padding: spacing.md, marginBottom: spacing.md },
  statusOk: { backgroundColor: colors.success },
  statusText: { color: colors.onSurface, fontSize: 13, fontWeight: "600", flex: 1 },
  hint: { color: colors.onSurfaceTertiary, fontSize: 12.5, lineHeight: 18, marginBottom: spacing.lg },
  label: { color: colors.onSurfaceSecondary, fontSize: 12, fontWeight: "700", marginBottom: 6 },
  fieldHint: { color: colors.onSurfaceTertiary, fontSize: 11.5, lineHeight: 16, marginTop: -6, marginBottom: spacing.md },
  input: { color: colors.onSurface, fontSize: type.base, backgroundColor: colors.surfaceSecondary, borderRadius: radius.sm, borderWidth: 1, borderColor: colors.border, paddingHorizontal: spacing.md, paddingVertical: 11 },
  readonly: { color: colors.onSurfaceTertiary, fontSize: 12, fontStyle: "italic" },
  sectionTitle: { color: colors.onSurfaceTertiary, fontSize: 12, fontWeight: "700", letterSpacing: 1, textTransform: "uppercase", marginTop: spacing.xl, marginBottom: spacing.sm },
  copyRow: { flexDirection: "row", alignItems: "center", gap: spacing.sm, backgroundColor: colors.surfaceSecondary, borderRadius: radius.sm, borderWidth: 1, borderColor: colors.border, padding: spacing.md, marginBottom: spacing.sm },
  copyLabel: { color: colors.onSurfaceTertiary, fontSize: 11, fontWeight: "700" },
  copyValue: { color: colors.onSurface, fontSize: 12.5, marginTop: 2, fontFamily: font.display },
  copyBtn: { width: 36, height: 36, borderRadius: radius.sm, backgroundColor: colors.brandTertiary, alignItems: "center", justifyContent: "center" },
  note: { flexDirection: "row", gap: spacing.sm, backgroundColor: colors.info, borderRadius: radius.sm, padding: spacing.md, marginTop: spacing.lg },
  noteText: { color: colors.onInfo, fontSize: 12, flex: 1, lineHeight: 17 },
});
