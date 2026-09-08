import React, { useCallback, useRef, useState } from "react";
import {
  View,
  Text,
  StyleSheet,
  FlatList,
  TextInput,
  Pressable,
  Platform,
} from "react-native";
import { useLocalSearchParams, useRouter, useFocusEffect } from "expo-router";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { Feather } from "@expo/vector-icons";
import * as Haptics from "expo-haptics";
import { KeyboardAvoidingView } from "react-native-keyboard-controller";
import { Image } from "expo-image";
import { api } from "@/src/api";
import { colors, spacing, radius, type, font, stageOf } from "@/src/theme";
import { Avatar, AiBadge, Loading, Sheet, GoldButton } from "@/src/components/ui";
import { useAssistant } from "@/src/useAssistant";
import { chatTime } from "@/src/time";

type Msg = { id: string; sender: "cliente" | "ai" | "operatore"; text: string; created_at: string };

export default function Conversation() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const insets = useSafeAreaInsets();
  const router = useRouter();
  const listRef = useRef<FlatList>(null);
  const { assistant } = useAssistant();

  const [conv, setConv] = useState<any>(null);
  const [lead, setLead] = useState<any>(null);
  const [messages, setMessages] = useState<Msg[]>([]);
  const [loading, setLoading] = useState(true);
  const [text, setText] = useState("");
  const [simSheet, setSimSheet] = useState(false);
  const [simText, setSimText] = useState("");
  const [banner, setBanner] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const res = await api.get(`/conversations/${id}`);
      setConv(res.conversation);
      setLead(res.lead);
      setMessages(res.messages);
    } catch {}
    setLoading(false);
  }, [id]);

  useFocusEffect(
    useCallback(() => {
      load();
    }, [load])
  );

  const scrollEnd = () => setTimeout(() => listRef.current?.scrollToEnd({ animated: true }), 80);

  const sendManual = async () => {
    const t = text.trim();
    if (!t) return;
    setText("");
    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
    const msg = await api.post(`/conversations/${id}/messages`, { text: t });
    setMessages((m) => [...m, msg]);
    scrollEnd();
  };

  const takeConversation = async () => {
    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium);
    await api.post(`/conversations/${id}/take`);
    await load();
    setBanner("Hai preso in carico la conversazione. L'AI è disattivata.");
  };

  const reactivateAi = async () => {
    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium);
    await api.post(`/conversations/${id}/reactivate-ai`);
    await load();
    setBanner("AI riattivata. L'assistente può riprendere la conversazione.");
  };

  const simulateCustomer = async () => {
    const t = simText.trim();
    if (!t) return;
    setSimSheet(false);
    setSimText("");
    const msg = await api.post(`/conversations/${id}/simulate-customer`, { text: t });
    setMessages((m) => [...m, msg]);
    scrollEnd();
  };

  const simulateAi = async () => {
    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
    const res = await api.post(`/conversations/${id}/simulate-ai-turn`);
    await load();
    scrollEnd();
    if (res.handoff) {
      Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
      setBanner("Cliente pronta! Passata allo staff → DA FISSARE. Riassunto AI generato.");
    }
  };

  if (loading || !conv || !lead) {
    return (
      <View style={{ flex: 1, backgroundColor: colors.surface, paddingTop: insets.top }}>
        <Loading />
      </View>
    );
  }

  const aiActive = conv.ai_attiva;

  const renderMsg = ({ item }: { item: Msg }) => {
    const isCustomer = item.sender === "cliente";
    const isAi = item.sender === "ai";
    if ((item as any).type === "image" && (item as any).media_url) {
      const uri = `${process.env.EXPO_PUBLIC_BACKEND_URL}${(item as any).media_url}`;
      return (
        <View style={[styles.msgRow, styles.right]}>
          <View style={styles.imageBubble}>
            <Image source={{ uri }} style={styles.chatImage} contentFit="cover" transition={200} />
            <Text style={styles.imgCaption}>{item.text}</Text>
          </View>
        </View>
      );
    }
    return (
      <View style={[styles.msgRow, isCustomer ? styles.left : styles.right]}>
        <View
          style={[
            styles.bubble,
            isCustomer && styles.bubbleCustomer,
            isAi && styles.bubbleAi,
            item.sender === "operatore" && styles.bubbleOp,
          ]}
        >
          {!isCustomer && (
            <View style={styles.senderRow}>
              {isAi ? <Avatar uri={assistant.avatarUri} name={assistant.name} size={16} position="top" /> : null}
              <Text style={[styles.senderTag, isAi ? { color: colors.brandPrimary } : { color: colors.brandSecondary }]}>
                {isAi ? assistant.name : "OPERATORE"}
              </Text>
            </View>
          )}
          <Text style={[styles.msgText, item.sender === "operatore" && { color: colors.onSurfaceInverse }]}>
            {item.text}
          </Text>
          <Text
            style={[
              styles.msgTime,
              item.sender === "operatore" && { color: "rgba(10,10,10,0.5)" },
            ]}
          >
            {chatTime(item.created_at)}
          </Text>
        </View>
      </View>
    );
  };

  return (
    <View style={{ flex: 1, backgroundColor: colors.surface }}>
      {/* Header */}
      <View style={[styles.header, { paddingTop: insets.top + spacing.sm }]}>
        <Pressable testID="conv-back" onPress={() => router.back()} hitSlop={10} style={styles.backBtn}>
          <Feather name="chevron-left" size={26} color={colors.onSurface} />
        </Pressable>
        <Pressable style={styles.headerInfo} onPress={() => router.push(`/cliente/${lead.id}`)}>
          <Avatar uri={lead.foto_profilo} name={`${lead.nome} ${lead.cognome}`} size={42} />
          <View style={{ flex: 1 }}>
            <Text style={styles.headerName} numberOfLines={1}>
              {lead.nome} {lead.cognome}
            </Text>
            <View style={styles.headerSub}>
              <View style={[styles.stageDot, { backgroundColor: stageOf(conv.stato).accent }]} />
              <Text style={styles.headerStage} numberOfLines={1}>
                {stageOf(conv.stato).label}
              </Text>
            </View>
          </View>
        </Pressable>
        <AiBadge active={aiActive} />
      </View>

      {banner && (
        <Pressable
          style={styles.banner}
          onPress={() => router.push(`/cliente/${lead.id}`)}
          testID="conv-banner"
        >
          <Feather name="info" size={15} color={colors.onBrandTertiary} />
          <Text style={styles.bannerText}>{banner}</Text>
          <Feather name="x" size={16} color={colors.onSurfaceTertiary} onPress={() => setBanner(null)} />
        </Pressable>
      )}

      <KeyboardAvoidingView
        style={{ flex: 1 }}
        behavior={Platform.OS === "ios" ? "padding" : "translate-with-padding"}
        keyboardVerticalOffset={0}
      >
        <FlatList
          ref={listRef}
          data={messages}
          keyExtractor={(m) => m.id}
          renderItem={renderMsg}
          contentContainerStyle={{ padding: spacing.lg, gap: spacing.sm }}
          onContentSizeChange={() => listRef.current?.scrollToEnd({ animated: false })}
          showsVerticalScrollIndicator={false}
        />

        {/* Demo toolbar */}
        <View style={styles.demoBar}>
          <Text style={styles.demoLabel}>DEMO</Text>
          <Pressable style={styles.demoBtn} onPress={() => setSimSheet(true)} testID="sim-customer-button">
            <Feather name="user" size={13} color={colors.onSurfaceSecondary} />
            <Text style={styles.demoBtnText}>Simula cliente</Text>
          </Pressable>
          <Pressable
            style={[styles.demoBtn, !aiActive && { opacity: 0.4 }]}
            onPress={aiActive ? simulateAi : undefined}
            disabled={!aiActive}
            testID="sim-ai-button"
          >
            <Feather name="cpu" size={13} color={colors.brandPrimary} />
            <Text style={[styles.demoBtnText, { color: colors.brandPrimary }]}>Simula AI</Text>
          </Pressable>
        </View>

        {/* CTA prendi/riattiva */}
        <View style={styles.ctaWrap}>
          {aiActive ? (
            <Pressable style={styles.takeBtn} onPress={takeConversation} testID="take-conversation-button">
              <Feather name="user-check" size={18} color={colors.onBrandPrimary} />
              <Text style={styles.takeText}>PRENDI CONVERSAZIONE</Text>
            </Pressable>
          ) : (
            <Pressable style={styles.reactivateBtn} onPress={reactivateAi} testID="reactivate-ai-button">
              <Feather name="cpu" size={18} color={colors.brandPrimary} />
              <Text style={styles.reactivateText}>RIATTIVA AI</Text>
            </Pressable>
          )}
        </View>

        {/* Input */}
        <View style={[styles.inputBar, { paddingBottom: insets.bottom + spacing.sm }]}>
          <TextInput
            testID="message-input"
            value={text}
            onChangeText={setText}
            editable={!aiActive}
            placeholder={aiActive ? "Prendi la conversazione per rispondere…" : "Scrivi un messaggio…"}
            placeholderTextColor={colors.onSurfaceTertiary}
            style={styles.input}
            multiline
          />
          <Pressable
            testID="send-message-button"
            onPress={sendManual}
            disabled={aiActive || !text.trim()}
            style={[styles.sendBtn, (aiActive || !text.trim()) && { opacity: 0.4 }]}
          >
            <Feather name="send" size={18} color={colors.onBrandPrimary} />
          </Pressable>
        </View>
      </KeyboardAvoidingView>

      <Sheet visible={simSheet} onClose={() => setSimSheet(false)} title="Simula messaggio cliente">
        <Text style={styles.simHint}>
          Scrivi come se fossi la cliente. Prova con "Vorrei prenotare un appuntamento" per vedere
          l'handoff automatico dell'AI.
        </Text>
        <TextInput
          testID="sim-customer-input"
          value={simText}
          onChangeText={setSimText}
          placeholder="Messaggio della cliente…"
          placeholderTextColor={colors.onSurfaceTertiary}
          style={styles.simInput}
          multiline
        />
        <GoldButton title="Invia come cliente" icon="send" onPress={simulateCustomer} testID="sim-send" />
      </Sheet>
    </View>
  );
}

const styles = StyleSheet.create({
  header: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.sm,
    paddingHorizontal: spacing.md,
    paddingBottom: spacing.md,
    backgroundColor: colors.surfaceSecondary,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
  },
  backBtn: { padding: 2 },
  headerInfo: { flex: 1, flexDirection: "row", alignItems: "center", gap: spacing.sm },
  headerName: { color: colors.onSurface, fontSize: type.lg, fontWeight: "700" },
  headerSub: { flexDirection: "row", alignItems: "center", gap: 5, marginTop: 2 },
  stageDot: { width: 7, height: 7, borderRadius: 3.5 },
  headerStage: { color: colors.onSurfaceTertiary, fontSize: 10.5, fontWeight: "600", letterSpacing: 0.3, flex: 1 },
  banner: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.sm,
    backgroundColor: colors.brandTertiary,
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.md,
    borderBottomWidth: 1,
    borderBottomColor: colors.borderStrong,
  },
  bannerText: { color: colors.onBrandTertiary, fontSize: 12.5, flex: 1, fontWeight: "600" },
  msgRow: { flexDirection: "row" },
  left: { justifyContent: "flex-start" },
  right: { justifyContent: "flex-end" },
  bubble: { maxWidth: "82%", borderRadius: radius.md, paddingHorizontal: spacing.md, paddingVertical: spacing.sm },
  bubbleCustomer: {
    backgroundColor: colors.surfaceSecondary,
    borderWidth: 1,
    borderColor: colors.border,
    borderTopLeftRadius: 4,
  },
  bubbleAi: {
    backgroundColor: colors.brandTertiary,
    borderWidth: 1,
    borderColor: colors.borderStrong,
    borderTopRightRadius: 4,
  },
  bubbleOp: { backgroundColor: colors.surfaceInverse, borderTopRightRadius: 4 },
  imageBubble: { maxWidth: "82%", borderRadius: radius.md, overflow: "hidden", backgroundColor: colors.brandTertiary, borderWidth: 1, borderColor: colors.borderStrong },
  chatImage: { width: 240, height: 180, backgroundColor: colors.surfaceTertiary },
  imgCaption: { color: colors.onBrandTertiary, fontSize: 11, fontWeight: "700", padding: spacing.sm },
  senderTag: { fontSize: 9.5, fontWeight: "800", letterSpacing: 0.6, marginBottom: 2 },
  senderRow: { flexDirection: "row", alignItems: "center", gap: 5, marginBottom: 3 },
  msgText: { color: colors.onSurface, fontSize: 14.5, lineHeight: 20 },
  msgTime: { color: colors.onSurfaceTertiary, fontSize: 10, alignSelf: "flex-end", marginTop: 3 },
  demoBar: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.sm,
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.sm,
    borderTopWidth: 1,
    borderTopColor: colors.divider,
    backgroundColor: colors.surface,
  },
  demoLabel: {
    color: colors.onSurfaceTertiary,
    fontSize: 9,
    fontWeight: "800",
    letterSpacing: 1,
    marginRight: spacing.xs,
  },
  demoBtn: {
    flexDirection: "row",
    alignItems: "center",
    gap: 5,
    paddingHorizontal: spacing.md,
    paddingVertical: 7,
    borderRadius: radius.pill,
    borderWidth: 1,
    borderColor: colors.border,
    backgroundColor: colors.surfaceSecondary,
  },
  demoBtnText: { color: colors.onSurfaceSecondary, fontSize: 12, fontWeight: "700" },
  ctaWrap: { paddingHorizontal: spacing.lg, paddingTop: spacing.xs },
  takeBtn: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: spacing.sm,
    backgroundColor: colors.brandPrimary,
    borderRadius: radius.md,
    paddingVertical: 13,
  },
  takeText: { color: colors.onBrandPrimary, fontSize: 14, fontWeight: "800", letterSpacing: 0.8 },
  reactivateBtn: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: spacing.sm,
    borderWidth: 1,
    borderColor: colors.borderStrong,
    borderRadius: radius.md,
    paddingVertical: 13,
  },
  reactivateText: { color: colors.brandPrimary, fontSize: 14, fontWeight: "800", letterSpacing: 0.8 },
  inputBar: {
    flexDirection: "row",
    alignItems: "flex-end",
    gap: spacing.sm,
    paddingHorizontal: spacing.lg,
    paddingTop: spacing.sm,
    backgroundColor: colors.surface,
  },
  input: {
    flex: 1,
    color: colors.onSurface,
    fontSize: type.lg,
    backgroundColor: colors.surfaceSecondary,
    borderRadius: radius.lg,
    borderWidth: 1,
    borderColor: colors.border,
    paddingHorizontal: spacing.lg,
    paddingVertical: Platform.OS === "ios" ? 12 : 8,
    maxHeight: 120,
  },
  sendBtn: {
    width: 46,
    height: 46,
    borderRadius: 23,
    backgroundColor: colors.brandPrimary,
    alignItems: "center",
    justifyContent: "center",
  },
  simHint: { color: colors.onSurfaceTertiary, fontSize: 13, marginBottom: spacing.md, lineHeight: 19 },
  simInput: {
    color: colors.onSurface,
    fontSize: type.lg,
    backgroundColor: colors.surface,
    borderRadius: radius.md,
    borderWidth: 1,
    borderColor: colors.border,
    padding: spacing.md,
    minHeight: 80,
    marginBottom: spacing.lg,
    textAlignVertical: "top",
  },
});
