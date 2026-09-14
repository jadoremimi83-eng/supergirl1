import React, { useEffect, useRef, useState } from "react";
import { View, Text, StyleSheet, TextInput, Pressable, ScrollView, ActivityIndicator } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { Feather } from "@expo/vector-icons";
import { api } from "@/src/api";
import { colors, spacing, radius } from "@/src/theme";
import { SubHeader } from "@/src/components/SubHeader";

type Msg = { sender: "cliente" | "ai"; text: string; note?: string };

export default function TestAndrea() {
  const insets = useSafeAreaInsets();
  const [servizi, setServizi] = useState<any[]>([]);
  const [servizio, setServizio] = useState<string>("");
  const [sede, setSede] = useState<string>("Milano");
  const [messages, setMessages] = useState<Msg[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const scRef = useRef<ScrollView>(null);

  useEffect(() => {
    api.get("/services").then((s: any[]) => {
      setServizi(s || []);
      if (s?.length) setServizio(s[0].nome);
    }).catch(() => {});
  }, []);

  const send = async () => {
    const t = input.trim();
    if (!t || busy) return;
    const next = [...messages, { sender: "cliente" as const, text: t }];
    setMessages(next); setInput(""); setBusy(true);
    setTimeout(() => scRef.current?.scrollToEnd({ animated: true }), 100);
    try {
      const r = await api.post("/kb/test", { servizio, sede, messages: next });
      setMessages([...next, { sender: "ai", text: r.reply || r.error || "(nessuna risposta)", note: r.note }]);
    } catch {
      setMessages([...next, { sender: "ai", text: "(errore di connessione)" }]);
    }
    setBusy(false);
    setTimeout(() => scRef.current?.scrollToEnd({ animated: true }), 100);
  };

  return (
    <View style={{ flex: 1, backgroundColor: colors.surface }}>
      <SubHeader title="Test Andrea" />
      <View style={styles.config}>
        <Text style={styles.cfgLabel}>Trattamento</Text>
        <ScrollView horizontal showsHorizontalScrollIndicator={false} style={{ marginBottom: spacing.sm }}>
          {servizi.map((s) => (
            <Pressable key={s.id || s.nome} onPress={() => setServizio(s.nome)}
              style={[styles.chip, servizio === s.nome && styles.chipOn]}>
              <Text style={[styles.chipText, servizio === s.nome && styles.chipTextOn]}>{s.nome}</Text>
            </Pressable>
          ))}
        </ScrollView>
        <View style={{ flexDirection: "row", gap: spacing.sm }}>
          {["Milano", "Verona"].map((c) => (
            <Pressable key={c} onPress={() => setSede(c)} style={[styles.chip, sede === c && styles.chipOn]}>
              <Text style={[styles.chipText, sede === c && styles.chipTextOn]}>{c}</Text>
            </Pressable>
          ))}
          <Pressable onPress={() => setMessages([])} style={[styles.chip, { marginLeft: "auto" }]}>
            <Feather name="rotate-ccw" size={13} color={colors.onSurfaceSecondary} />
            <Text style={styles.chipText}> Reset</Text>
          </Pressable>
        </View>
      </View>

      <ScrollView ref={scRef} style={{ flex: 1 }} contentContainerStyle={{ padding: spacing.lg, gap: spacing.sm }}>
        {messages.length === 0 && (
          <Text style={styles.hint}>Scrivi come se fossi una cliente e verifica le risposte di Andrea (Knowledge Base attuale). Nessun dato viene salvato.</Text>
        )}
        {messages.map((m, i) => (
          <View key={i} style={{ gap: 6 }}>
            <View style={[styles.bubble, m.sender === "cliente" ? styles.bubbleUser : styles.bubbleAi]}>
              <Text style={styles.bubbleWho}>{m.sender === "cliente" ? "Cliente" : "Andrea"}</Text>
              <Text style={styles.bubbleText}>{m.text}</Text>
            </View>
            {!!m.note && (
              <View style={styles.note}>
                <Feather name="phone-call" size={12} color={colors.brandPrimary} />
                <Text style={styles.noteText}>{m.note}</Text>
              </View>
            )}
          </View>
        ))}
        {busy && <View style={[styles.bubble, styles.bubbleAi]}><ActivityIndicator color={colors.brandPrimary} /></View>}
      </ScrollView>

      <View style={[styles.inputBar, { paddingBottom: insets.bottom + spacing.md }]}>
        <TextInput value={input} onChangeText={setInput} placeholder="Scrivi un messaggio da cliente…"
          placeholderTextColor={colors.onSurfaceTertiary} style={styles.input} onSubmitEditing={send} returnKeyType="send" />
        <Pressable onPress={send} disabled={busy || !input.trim()} style={[styles.sendBtn, (busy || !input.trim()) && { opacity: 0.5 }]}>
          <Feather name="send" size={18} color={colors.onBrandPrimary} />
        </Pressable>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  config: { padding: spacing.lg, borderBottomWidth: 1, borderBottomColor: colors.border, backgroundColor: colors.surfaceSecondary },
  cfgLabel: { color: colors.onSurfaceTertiary, fontSize: 11, fontWeight: "700", letterSpacing: 1, textTransform: "uppercase", marginBottom: spacing.xs },
  chip: { flexDirection: "row", alignItems: "center", backgroundColor: colors.surface, borderRadius: radius.pill, borderWidth: 1, borderColor: colors.border, paddingHorizontal: spacing.md, paddingVertical: 7, marginRight: spacing.sm },
  chipOn: { backgroundColor: colors.brandPrimary, borderColor: colors.brandPrimary },
  chipText: { color: colors.onSurfaceSecondary, fontSize: 12.5, fontWeight: "600" },
  chipTextOn: { color: colors.onBrandPrimary },
  hint: { color: colors.onSurfaceTertiary, fontSize: 13, lineHeight: 19, textAlign: "center", marginTop: spacing.xl },
  bubble: { maxWidth: "78%", borderRadius: radius.md, padding: spacing.md },
  bubbleUser: { alignSelf: "flex-end", backgroundColor: colors.brandTertiary },
  bubbleAi: { alignSelf: "flex-start", backgroundColor: colors.surfaceSecondary, borderWidth: 1, borderColor: colors.border },
  bubbleWho: { color: colors.onSurfaceTertiary, fontSize: 10.5, fontWeight: "700", marginBottom: 3, textTransform: "uppercase", letterSpacing: 0.5 },
  bubbleText: { color: colors.onSurface, fontSize: 14.5, lineHeight: 20 },
  note: { flexDirection: "row", alignItems: "center", gap: 6, alignSelf: "flex-start", maxWidth: "78%", backgroundColor: colors.brandTertiary, borderRadius: radius.sm, paddingHorizontal: spacing.sm, paddingVertical: 6 },
  noteText: { flex: 1, color: colors.brandPrimary, fontSize: 11.5, lineHeight: 16, fontWeight: "600" },
  inputBar: { flexDirection: "row", alignItems: "center", gap: spacing.sm, padding: spacing.md, borderTopWidth: 1, borderTopColor: colors.border, backgroundColor: colors.surfaceSecondary },
  input: { flex: 1, color: colors.onSurface, fontSize: 15, backgroundColor: colors.surface, borderRadius: radius.pill, borderWidth: 1, borderColor: colors.border, paddingHorizontal: spacing.lg, paddingVertical: 11 },
  sendBtn: { width: 44, height: 44, borderRadius: 22, backgroundColor: colors.brandPrimary, alignItems: "center", justifyContent: "center" },
});
