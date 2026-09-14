import React, { useCallback, useRef, useState } from "react";
import { View, Text, StyleSheet, Pressable, TextInput, Image, ActivityIndicator, Linking } from "react-native";
import { KeyboardAwareScrollView } from "react-native-keyboard-controller";
import { useFocusEffect } from "expo-router";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { Feather } from "@expo/vector-icons";
import * as ImagePicker from "expo-image-picker";
import * as DocumentPicker from "expo-document-picker";
import * as Haptics from "expo-haptics";
import { api, uploadMetaAsset, uploadWelcomePhoto } from "@/src/api";
import { colors, spacing, radius, type } from "@/src/theme";
import { SubHeader } from "@/src/components/SubHeader";
import { GoldButton } from "@/src/components/ui";

const BASE = process.env.EXPO_PUBLIC_BACKEND_URL;

type Geo = { key: string; name: string; type: string };

export default function CreaCampagna() {
  const insets = useSafeAreaInsets();
  const [acct, setAcct] = useState<any>(null);
  const [asset, setAsset] = useState<{ kind: string; image_hash?: string; video_id?: string; thumb_url?: string } | null>(null);
  const [uploading, setUploading] = useState(false);
  const [creating, setCreating] = useState(false);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<any>(null);
  const [previews, setPreviews] = useState<any[]>([]);
  const [created, setCreated] = useState<any[]>([]);

  const [nome, setNome] = useState("");
  const [dest, setDest] = useState<"whatsapp" | "modulo">("whatsapp");
  const [plats, setPlats] = useState<string[]>(["facebook", "instagram"]);
  const [genere, setGenere] = useState<"tutti" | "donne" | "uomini">("tutti");
  const [etaMin, setEtaMin] = useState("25");
  const [etaMax, setEtaMax] = useState("55");
  const [budget, setBudget] = useState("10");
  const [messaggio, setMessaggio] = useState("Scopri di più, ti aspettiamo!");
  const [waWelcome, setWaWelcome] = useState("Ciao! Come possiamo aiutarti?");
  const [q1, setQ1] = useState("Quanto costa il trattamento?");
  const [q2, setQ2] = useState("Posso fissare un appuntamento?");
  const [welcomePhoto, setWelcomePhoto] = useState<string | null>(null);
  const [forms, setForms] = useState<any[]>([]);
  const [formId, setFormId] = useState<string | null>(null);
  const [creatingForm, setCreatingForm] = useState(false);

  const [geoQuery, setGeoQuery] = useState("");
  const [geoResults, setGeoResults] = useState<Geo[]>([]);
  const [geoSel, setGeoSel] = useState<Geo[]>([]);
  const geoTimer = useRef<any>(null);

  const load = useCallback(async () => {
    try {
      const [a, c, f] = await Promise.all([
        api.get("/meta/ad-account"), api.get("/meta/campaigns/created"), api.get("/meta/lead-forms"),
      ]);
      setAcct(a); setCreated(c); setForms(f);
      if (f.length && !formId) setFormId(f[0].id);
    } catch {}
  }, [formId]);
  useFocusEffect(useCallback(() => { load(); }, [load]));

  const createForm = async () => {
    setCreatingForm(true); setError(null);
    try {
      const r = await api.post("/meta/lead-forms", { nome: "Raccolta Dati" });
      const list = await api.get("/meta/lead-forms");
      setForms(list); setFormId(r.id);
      Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
    } catch (e: any) { setError(e.message || "Creazione modulo non riuscita"); }
    setCreatingForm(false);
  };

  const pickWelcomePhoto = async () => {
    setError(null);
    const res = await DocumentPicker.getDocumentAsync({ type: ["image/*"], copyToCacheDirectory: true, multiple: false });
    if (res.canceled || !res.assets?.length) return;
    const a = res.assets[0];
    try {
      const up = await uploadWelcomePhoto(a.uri, a.name || "welcome.jpg", a.mimeType || "image/jpeg");
      setWelcomePhoto(up.url);
      Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
    } catch (e: any) { setError(e.message || "Upload foto non riuscito"); }
  };

  const searchGeo = (q: string) => {
    setGeoQuery(q);
    if (geoTimer.current) clearTimeout(geoTimer.current);
    if (q.trim().length < 2) { setGeoResults([]); return; }
    geoTimer.current = setTimeout(async () => {
      try { setGeoResults(await api.get(`/meta/geo-search?q=${encodeURIComponent(q)}`)); } catch {}
    }, 350);
  };
  const addGeo = (g: Geo) => {
    if (!geoSel.find((x) => x.key === g.key)) setGeoSel([...geoSel, g]);
    setGeoQuery(""); setGeoResults([]);
    Haptics.selectionAsync();
  };

  const togglePlat = (p: string) =>
    setPlats((prev) => (prev.includes(p) ? prev.filter((x) => x !== p) : [...prev, p]));

  const pickAsset = async () => {
    setError(null);
    const perm = await ImagePicker.requestMediaLibraryPermissionsAsync();
    if (!perm.granted) { setError("Serve il permesso alla galleria per scegliere foto o video."); return; }
    const res = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ImagePicker.MediaTypeOptions.All, quality: 1, videoMaxDuration: 60,
    });
    if (res.canceled || !res.assets?.length) return;
    const a = res.assets[0];
    const isVideo = a.type === "video" || (a.fileName || "").toLowerCase().match(/\.(mp4|mov|m4v|avi)$/);
    const name = a.fileName || (isVideo ? "video.mp4" : "foto.jpg");
    const mime = isVideo ? "video/mp4" : "image/jpeg";
    setUploading(true);
    try {
      const up = await uploadMetaAsset(a.uri, name, mime);
      setAsset({ kind: up.type, image_hash: up.image_hash, video_id: up.video_id, thumb_url: up.thumb_url });
      Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
    } catch (e: any) { setError(e.message || "Upload non riuscito"); }
    setUploading(false);
  };

  const pickFromFiles = async () => {
    setError(null);
    const res = await DocumentPicker.getDocumentAsync({
      type: ["image/*", "video/*"], copyToCacheDirectory: true, multiple: false,
    });
    if (res.canceled || !res.assets?.length) return;
    const a = res.assets[0];
    const isVideo = (a.mimeType || "").startsWith("video") || (a.name || "").toLowerCase().match(/\.(mp4|mov|m4v|avi)$/);
    setUploading(true);
    try {
      const up = await uploadMetaAsset(a.uri, a.name || (isVideo ? "video.mp4" : "foto.jpg"), a.mimeType || (isVideo ? "video/mp4" : "image/jpeg"));
      setAsset({ kind: up.type, image_hash: up.image_hash, video_id: up.video_id, thumb_url: up.thumb_url });
      Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
    } catch (e: any) { setError(e.message || "Upload non riuscito"); }
    setUploading(false);
  };

  const toggleStatus = async (c: any) => {
    const next = c.status === "ACTIVE" ? "PAUSED" : "ACTIVE";
    setBusyId(c.campaign_id); setError(null);
    try {
      await api.patch(`/meta/campaigns/${c.campaign_id}/status`, { status: next });
      Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
      await load();
    } catch (e: any) { setError(e.message || "Impossibile cambiare stato"); }
    setBusyId(null);
  };
  const delCampaign = async (c: any) => {
    setBusyId(c.campaign_id);
    try { await api.del(`/meta/campaigns/${c.campaign_id}`); await load(); } catch {}
    setBusyId(null);
  };

  const create = async () => {
    setError(null); setResult(null); setPreviews([]);
    if (!nome.trim()) { setError("Dai un nome alla campagna."); return; }
    if (!asset) { setError("Carica prima una foto o un video."); return; }
    if (!plats.length) { setError("Scegli almeno una piattaforma (Facebook o Instagram)."); return; }
    if (dest === "modulo" && !formId) { setError("Seleziona o crea un modulo raccolta dati."); return; }
    setCreating(true);
    try {
      const body: any = {
        nome, destinazione: dest, piattaforme: plats, genere,
        lead_form_id: dest === "modulo" ? formId : undefined,
        eta_min: parseInt(etaMin) || 18, eta_max: parseInt(etaMax) || 65,
        budget_giornaliero_eur: parseFloat(budget) || 5,
        geo_keys: geoSel.map((g) => g.key), geo_countries: geoSel.length ? [] : ["IT"],
        testo_annuncio: messaggio,
        wa_welcome: waWelcome,
        wa_domande: [q1, q2].filter((x) => x.trim()),
        welcome_image_url: welcomePhoto,
        image_hash: asset.image_hash, video_id: asset.video_id, thumb_url: asset.thumb_url,
      };
      const r = await api.post("/meta/campaigns/create", body);
      setResult(r);
      Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
      try { const p = await api.get(`/meta/preview/${r.creative_id}`); setPreviews(p.previews || []); } catch {}
      load();
    } catch (e: any) { setError(e.message || "Creazione non riuscita"); }
    setCreating(false);
  };

  const openPreview = (url: string) => Linking.openURL(url);

  return (
    <View style={{ flex: 1, backgroundColor: colors.surface }}>
      <SubHeader title="Crea Campagna Meta" />
      <KeyboardAwareScrollView
        contentContainerStyle={{ padding: spacing.lg, paddingBottom: insets.bottom + spacing["2xl"], maxWidth: 720, width: "100%", alignSelf: "center" }}
        bottomOffset={24} showsVerticalScrollIndicator={false}
      >
        {/* Account status */}
        <View style={[styles.acctBox, acct?.configured ? styles.acctOk : styles.acctBad]}>
          <Feather name={acct?.configured ? "check-circle" : "alert-circle"} size={16} color={acct?.configured ? colors.onSuccess : colors.onWarning} />
          <Text style={styles.acctText}>
            {acct?.configured ? `Account: ${acct.account?.name} · ${acct.account?.currency}` : "Account pubblicitario non collegato"}
          </Text>
        </View>

        {error ? <View style={styles.errBox}><Text style={styles.errText}>{error}</Text></View> : null}

        {/* 1. Creatività */}
        <Text style={styles.section}>1 · Foto o Video</Text>
        <Pressable style={styles.assetBox} onPress={pickAsset} testID="pick-asset">
          {uploading ? <ActivityIndicator color={colors.brandPrimary} /> : asset ? (
            <View style={{ alignItems: "center", gap: 6 }}>
              {asset.thumb_url && asset.kind === "image" ? (
                <Image source={{ uri: `${BASE}${asset.thumb_url}` }} style={styles.thumb} />
              ) : (
                <Feather name={asset.kind === "video" ? "film" : "image"} size={30} color={colors.brandPrimary} />
              )}
              <Text style={styles.assetOk}>{asset.kind === "video" ? "Video caricato" : "Foto caricata"} · tocca per cambiare</Text>
            </View>
          ) : (
            <View style={{ alignItems: "center", gap: 8 }}>
              <Feather name="upload-cloud" size={30} color={colors.onSurfaceTertiary} />
              <Text style={styles.assetHint}>Carica una foto o un video{"\n"}Meta adatta i formati (Feed, Story, Reels) senza bande nere</Text>
            </View>
          )}
        </Pressable>
        <Pressable style={styles.fileBtn} onPress={pickFromFiles} testID="pick-file">
          <Feather name="folder" size={14} color={colors.brandPrimary} />
          <Text style={styles.fileBtnText}>Scegli file dal computer (foto o video)</Text>
        </Pressable>

        {/* 2. Nome + destinazione */}
        <Text style={styles.section}>2 · Nome e destinazione</Text>
        <Text style={styles.label}>Nome campagna (verrà salvata con prefisso SG-)</Text>
        <TextInput value={nome} onChangeText={setNome} placeholder="Es. Bomba Milano Estate" placeholderTextColor={colors.onSurfaceTertiary} style={styles.input} testID="camp-nome" />
        <View style={styles.rowChips}>
          {(["whatsapp", "modulo"] as const).map((d) => (
            <Chip key={d} active={dest === d} label={d === "whatsapp" ? "WhatsApp" : "Modulo"} icon={d === "whatsapp" ? "message-circle" : "file-text"} onPress={() => setDest(d)} testID={`dest-${d}`} />
          ))}
        </View>
        {dest === "modulo" && (
          <View style={styles.formBox}>
            <Text style={styles.label}>Modulo raccolta dati (Nome, Cognome, Telefono — no email)</Text>
            {forms.length > 0 ? (
              <View style={styles.rowChips}>
                {forms.map((f) => (
                  <Chip key={f.id} active={formId === f.id} label={f.name.replace(/^SG-\s*/, "")} onPress={() => setFormId(f.id)} testID={`form-${f.id}`} />
                ))}
              </View>
            ) : <Text style={styles.hintSmall}>Nessun modulo SG- ancora. Creane uno qui sotto.</Text>}
            <Pressable style={styles.fileBtn} onPress={createForm} disabled={creatingForm} testID="create-form">
              {creatingForm ? <ActivityIndicator color={colors.brandPrimary} /> : <Feather name="plus" size={14} color={colors.brandPrimary} />}
              <Text style={styles.fileBtnText}>Crea nuovo modulo raccolta dati</Text>
            </Pressable>
          </View>
        )}

        {/* 3. Piattaforme */}
        <Text style={styles.section}>3 · Piattaforme</Text>
        <View style={styles.rowChips}>
          <Chip active={plats.includes("facebook")} label="Facebook" icon="facebook" onPress={() => togglePlat("facebook")} testID="plat-fb" />
          <Chip active={plats.includes("instagram")} label="Instagram" icon="instagram" onPress={() => togglePlat("instagram")} testID="plat-ig" />
        </View>

        {/* 4. Targeting */}
        <Text style={styles.section}>4 · Pubblico</Text>
        <Text style={styles.label}>Sede / Area (cerca città o regione)</Text>
        <TextInput value={geoQuery} onChangeText={searchGeo} placeholder="Es. Milano" placeholderTextColor={colors.onSurfaceTertiary} style={styles.input} testID="geo-search" />
        {geoResults.length > 0 && (
          <View style={styles.geoList}>
            {geoResults.map((g) => (
              <Pressable key={g.key} onPress={() => addGeo(g)} style={styles.geoItem}>
                <Feather name="map-pin" size={13} color={colors.brandPrimary} />
                <Text style={styles.geoItemText}>{g.name}</Text>
              </Pressable>
            ))}
          </View>
        )}
        {geoSel.length > 0 && (
          <View style={styles.geoSelWrap}>
            {geoSel.map((g) => (
              <Pressable key={g.key} onPress={() => setGeoSel(geoSel.filter((x) => x.key !== g.key))} style={styles.geoTag}>
                <Text style={styles.geoTagText}>{g.name}</Text>
                <Feather name="x" size={12} color={colors.brandPrimary} />
              </Pressable>
            ))}
          </View>
        )}
        <Text style={styles.hintSmall}>Se non scegli nessuna zona, la campagna copre tutta Italia.</Text>

        <Text style={styles.label}>Genere</Text>
        <View style={styles.rowChips}>
          {(["tutti", "donne", "uomini"] as const).map((g) => (
            <Chip key={g} active={genere === g} label={g[0].toUpperCase() + g.slice(1)} onPress={() => setGenere(g)} testID={`gen-${g}`} />
          ))}
        </View>

        <View style={{ flexDirection: "row", gap: spacing.md }}>
          <View style={{ flex: 1 }}>
            <Text style={styles.label}>Età min</Text>
            <TextInput value={etaMin} onChangeText={setEtaMin} keyboardType="number-pad" style={styles.input} testID="eta-min" />
          </View>
          <View style={{ flex: 1 }}>
            <Text style={styles.label}>Età max</Text>
            <TextInput value={etaMax} onChangeText={setEtaMax} keyboardType="number-pad" style={styles.input} testID="eta-max" />
          </View>
          <View style={{ flex: 1 }}>
            <Text style={styles.label}>Budget/giorno €</Text>
            <TextInput value={budget} onChangeText={setBudget} keyboardType="decimal-pad" style={styles.input} testID="budget" />
          </View>
        </View>

        {/* 5. Testo annuncio */}
        <Text style={styles.section}>5 · Testo dell&apos;annuncio</Text>
        <Text style={styles.hintSmall}>La descrizione che accompagna foto/video su Facebook e Instagram.</Text>
        <TextInput value={messaggio} onChangeText={setMessaggio} multiline style={[styles.input, { minHeight: 70, textAlignVertical: "top", marginTop: 6 }]} testID="messaggio" />

        {/* 6. Messaggio WhatsApp (solo destinazione WhatsApp) */}
        {dest === "whatsapp" && (
          <>
            <Text style={styles.section}>6 · Messaggio WhatsApp iniziale</Text>
            <Text style={styles.hintSmall}>Il saluto che la cliente vede aprendo WhatsApp, con due domande rapide toccabili.</Text>
            <Text style={styles.label}>Messaggio di benvenuto</Text>
            <TextInput value={waWelcome} onChangeText={setWaWelcome} style={styles.input} testID="wa-welcome" />
            <Text style={styles.label}>Foto da inviare col primo messaggio (opzionale)</Text>
            <Pressable style={styles.assetBox} onPress={pickWelcomePhoto} testID="pick-welcome-photo">
              {welcomePhoto ? (
                <View style={{ alignItems: "center", gap: 6 }}>
                  <Image source={{ uri: `${BASE}${welcomePhoto}` }} style={styles.thumb} />
                  <Text style={styles.assetOk}>Foto pronta · tocca per cambiare</Text>
                </View>
              ) : (
                <View style={{ alignItems: "center", gap: 8 }}>
                  <Feather name="image" size={26} color={colors.onSurfaceTertiary} />
                  <Text style={styles.assetHint}>Scegli una foto (es. del trattamento){"\n"}da qualsiasi cartella del dispositivo</Text>
                </View>
              )}
            </Pressable>
            <Text style={styles.label}>Domanda rapida 1</Text>
            <TextInput value={q1} onChangeText={setQ1} style={styles.input} testID="wa-q1" maxLength={80} />
            <Text style={styles.label}>Domanda rapida 2</Text>
            <TextInput value={q2} onChangeText={setQ2} style={styles.input} testID="wa-q2" maxLength={80} />
          </>
        )}


        <View style={{ marginTop: spacing.lg }}>
          <GoldButton title={creating ? "Creazione in corso…" : "Crea campagna (in pausa)"} icon="target" onPress={create} disabled={creating} testID="create-campaign" />
        </View>

        {/* Result + previews */}
        {result && (
          <View style={styles.resultBox}>
            <Text style={styles.resultTitle}>✓ Campagna creata in PAUSA: {result.nome}</Text>
            <Text style={styles.resultSub}>Rivedila e attivala da Gestione Inserzioni quando vuoi.</Text>
            {previews.length > 0 && (
              <>
                <Text style={styles.previewLabel}>ANTEPRIME (formato già adattato)</Text>
                <View style={styles.rowChips}>
                  {previews.map((p) => (
                    <Pressable key={p.format} onPress={() => openPreview(p.url)} style={styles.prevBtn} testID={`preview-${p.format}`}>
                      <Feather name="eye" size={13} color={colors.brandPrimary} />
                      <Text style={styles.prevText}>{p.label}</Text>
                    </Pressable>
                  ))}
                </View>
              </>
            )}
          </View>
        )}

        {/* Created list */}
        {created.length > 0 && (
          <>
            <Text style={styles.section}>Campagne create</Text>
            {created.map((c) => {
              const active = c.status === "ACTIVE";
              const busy = busyId === c.campaign_id;
              return (
                <View key={c.id} style={styles.createdItem}>
                  <Feather name="target" size={15} color={colors.brandPrimary} />
                  <View style={{ flex: 1 }}>
                    <Text style={styles.createdName}>{c.nome}</Text>
                    <Text style={styles.createdMeta}>
                      {c.destinazione === "whatsapp" ? "WhatsApp" : "Modulo"} · {active ? "ATTIVA" : "IN PAUSA"}
                    </Text>
                  </View>
                  {busy ? <ActivityIndicator color={colors.brandPrimary} /> : (
                    <>
                      <Pressable onPress={() => toggleStatus(c)} testID={`toggle-${c.campaign_id}`}
                        style={[styles.stateBtn, active ? styles.statePause : styles.statePlay]}>
                        <Feather name={active ? "pause" : "play"} size={13} color={active ? colors.onSurface : colors.onBrandPrimary} />
                        <Text style={[styles.stateBtnText, { color: active ? colors.onSurface : colors.onBrandPrimary }]}>
                          {active ? "Pausa" : "Attiva"}
                        </Text>
                      </Pressable>
                      <Pressable onPress={() => delCampaign(c)} style={styles.delBtn} testID={`del-${c.campaign_id}`}>
                        <Feather name="trash-2" size={14} color={colors.onSurfaceTertiary} />
                      </Pressable>
                    </>
                  )}
                </View>
              );
            })}
            <Text style={styles.hintSmall}>In pausa non spende nulla. Attivando, Meta può iniziare a erogare dopo l&apos;approvazione.</Text>

          </>
        )}
      </KeyboardAwareScrollView>
    </View>
  );
}

function Chip({ active, label, icon, onPress, testID }: any) {
  return (
    <Pressable onPress={onPress} testID={testID} style={[styles.chip, active && styles.chipOn]}>
      {icon ? <Feather name={icon} size={13} color={active ? colors.onBrandPrimary : colors.onSurfaceSecondary} /> : null}
      <Text style={[styles.chipText, active && styles.chipTextOn]}>{label}</Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  acctBox: { flexDirection: "row", alignItems: "center", gap: spacing.sm, borderRadius: radius.md, padding: spacing.md, marginBottom: spacing.md, borderWidth: 1 },
  acctOk: { backgroundColor: colors.surfaceSecondary, borderColor: colors.onSuccess },
  acctBad: { backgroundColor: colors.surfaceSecondary, borderColor: colors.warning },
  acctText: { color: colors.onSurface, fontSize: 13, fontWeight: "600", flex: 1 },
  errBox: { backgroundColor: colors.warning, borderRadius: radius.sm, padding: spacing.md, marginBottom: spacing.md },
  errText: { color: colors.onWarning, fontSize: 13, fontWeight: "600" },
  section: { color: colors.brandPrimary, fontSize: 12, fontWeight: "800", letterSpacing: 0.8, textTransform: "uppercase", marginTop: spacing.lg, marginBottom: spacing.sm },
  label: { color: colors.onSurfaceSecondary, fontSize: 12.5, fontWeight: "700", marginBottom: 6, marginTop: spacing.sm },
  input: { color: colors.onSurface, fontSize: type.base, backgroundColor: colors.surfaceSecondary, borderRadius: radius.sm, borderWidth: 1, borderColor: colors.border, paddingHorizontal: spacing.md, paddingVertical: 10 },
  assetBox: { borderRadius: radius.md, borderWidth: 1.5, borderColor: colors.border, borderStyle: "dashed", backgroundColor: colors.surfaceSecondary, padding: spacing.xl, alignItems: "center", justifyContent: "center", minHeight: 130 },
  assetHint: { color: colors.onSurfaceTertiary, fontSize: 12.5, textAlign: "center", lineHeight: 18 },
  assetOk: { color: colors.onSurface, fontSize: 13, fontWeight: "600" },
  fileBtn: { flexDirection: "row", alignItems: "center", justifyContent: "center", gap: 8, marginTop: spacing.sm, paddingVertical: 10, borderRadius: radius.sm, borderWidth: 1, borderColor: colors.border, backgroundColor: colors.surfaceSecondary },
  fileBtnText: { color: colors.brandPrimary, fontSize: 13, fontWeight: "700" },
  formBox: { backgroundColor: colors.surfaceSecondary, borderRadius: radius.md, borderWidth: 1, borderColor: colors.border, padding: spacing.md, marginTop: spacing.sm },
  stateBtn: { flexDirection: "row", alignItems: "center", gap: 5, paddingHorizontal: spacing.md, paddingVertical: 8, borderRadius: radius.pill },
  statePlay: { backgroundColor: colors.brandPrimary },
  statePause: { backgroundColor: colors.surfaceTertiary, borderWidth: 1, borderColor: colors.border },
  stateBtnText: { fontSize: 12.5, fontWeight: "800" },
  delBtn: { width: 34, height: 34, borderRadius: radius.sm, alignItems: "center", justifyContent: "center", borderWidth: 1, borderColor: colors.border, backgroundColor: colors.surface },
  thumb: { width: 96, height: 96, borderRadius: radius.sm },
  rowChips: { flexDirection: "row", flexWrap: "wrap", gap: spacing.sm },
  chip: { flexDirection: "row", alignItems: "center", gap: 6, paddingHorizontal: spacing.md, paddingVertical: 9, borderRadius: radius.pill, borderWidth: 1, borderColor: colors.border, backgroundColor: colors.surfaceSecondary },
  chipOn: { backgroundColor: colors.brandPrimary, borderColor: colors.brandPrimary },
  chipText: { color: colors.onSurfaceSecondary, fontSize: 13, fontWeight: "700" },
  chipTextOn: { color: colors.onBrandPrimary },
  geoList: { backgroundColor: colors.surfaceSecondary, borderRadius: radius.sm, borderWidth: 1, borderColor: colors.border, marginTop: 6, overflow: "hidden" },
  geoItem: { flexDirection: "row", alignItems: "center", gap: 8, paddingHorizontal: spacing.md, paddingVertical: 10, borderBottomWidth: 1, borderBottomColor: colors.border },
  geoItemText: { color: colors.onSurface, fontSize: 13, flex: 1 },
  geoSelWrap: { flexDirection: "row", flexWrap: "wrap", gap: spacing.sm, marginTop: spacing.sm },
  geoTag: { flexDirection: "row", alignItems: "center", gap: 6, backgroundColor: colors.brandTertiary, borderRadius: radius.pill, paddingHorizontal: spacing.md, paddingVertical: 6 },
  geoTagText: { color: colors.brandPrimary, fontSize: 12.5, fontWeight: "700" },
  hintSmall: { color: colors.onSurfaceTertiary, fontSize: 11.5, marginTop: 6, fontStyle: "italic" },
  resultBox: { backgroundColor: colors.surfaceSecondary, borderRadius: radius.md, borderWidth: 1, borderColor: colors.onSuccess, padding: spacing.lg, marginTop: spacing.lg },
  resultTitle: { color: colors.onSurface, fontSize: 14.5, fontWeight: "800" },
  resultSub: { color: colors.onSurfaceTertiary, fontSize: 12.5, marginTop: 4 },
  previewLabel: { color: colors.onSurfaceTertiary, fontSize: 10.5, fontWeight: "800", letterSpacing: 1, marginTop: spacing.md, marginBottom: spacing.sm },
  prevBtn: { flexDirection: "row", alignItems: "center", gap: 6, backgroundColor: colors.brandTertiary, borderRadius: radius.pill, paddingHorizontal: spacing.md, paddingVertical: 8 },
  prevText: { color: colors.brandPrimary, fontSize: 12.5, fontWeight: "700" },
  createdItem: { flexDirection: "row", alignItems: "center", gap: spacing.md, backgroundColor: colors.surfaceSecondary, borderRadius: radius.sm, borderWidth: 1, borderColor: colors.border, padding: spacing.md, marginBottom: spacing.sm },
  createdName: { color: colors.onSurface, fontSize: 13.5, fontWeight: "700" },
  createdMeta: { color: colors.onSurfaceTertiary, fontSize: 11.5, marginTop: 2 },
});
