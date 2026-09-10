# SUPER GIRL — PRD

## Problem statement (originale)
CRM conversazionale mobile-first con assistente AI per gestire i lead da Meta Ads via WhatsApp.
Flusso: Meta Ads → lead → WhatsApp → AI → qualificazione → LEAD PRONTA → DA FISSARE APPUNTAMENTO → operatore → appuntamento (inserito manualmente in gestionale esterno, NON integrato).
FASE 1 = demo completa con dati simulati, senza integrazioni reali (no Meta, no WhatsApp, no AI a pagamento, no credenziali reali). Predisporre DB/backend/frontend per collegare le API ufficiali in seguito senza ricostruire.

## Stack / Architettura
- Frontend: Expo (React Native) + expo-router, mobile-first (testato 390px). UI in italiano.
- Backend: FastAPI (`/app/backend/server.py`) — tutte le rotte con prefisso `/api`. Motore AI simulato e transizioni di stato lato server, dietro funzioni controllate (pronte per la Fase 4).
- DB: MongoDB. Collezioni: users, leads, conversations, messages, lead_status_history, services, locations, campaigns, knowledge_base, followups, followup_rules, notifications, ai_handoffs, settings.
- Auth: JWT (bcrypt) con ruoli admin/operator. Seed automatico all'avvio se DB vuoto (`seed_data.py`).
- Design: luxe dark — nero/antracite + champagne/oro + avorio. Serif display (Georgia). Identità originale (no Pipelean).

## Personas
- Admin (Giulia): configura Knowledge Base, servizi, sedi, team, follow-up, impostazioni; vede tutto.
- Operatore (Sara): gestisce chat, prende in carico conversazioni, fissa manualmente.

## Core requirements (static)
- 5 tab: Chat, Clienti, Pipeline, Analytics, Altro. Home "DA FISSARE ADESSO" come landing.
- Chat stile messaggistica con filtri (Tutte/AI/Operatore/Da fissare/Non lette), badge AI ATTIVA/OPERATORE, temperatura.
- Handoff AI→operatore automatico su intenzione di prenotare: AI OFF, stop follow-up, stato→da_fissare, notifica, riassunto AI strutturato.
- PRENDI CONVERSAZIONE / RIATTIVA AI immediati.
- Pipeline 8 stati, colonna DA FISSARE evidente, pulsante Cambia Stato (mobile).
- Identità lead + social (nome modulo + IG username/display + foto profilo + piattaforma), foto fittizie in Fase 1.
- Tracciamento pubblicitario: Piattaforma→Campagna→Inserzione→Servizio→Sede associato al lead.
- Analytics: metriche, funnel, % conversione, filtri periodo/sede/servizio/campagna/piattaforma.
- Knowledge Base editabile (Conoscenza AI). Regola: l'AI non inventa, altrimenti handoff.
- Sicurezza: JWT, ruoli separati, segreti solo lato server.

## Implementato (2026-06)
- [x] Auth JWT + ruoli + seed (admin/operator). 13 lead demo distribuiti negli 8 stati.
- [x] Chat list + filtri + conversazione (bolle distinte cliente/AI/operatore) + PRENDI/RIATTIVA AI + demo Simula cliente/AI.
- [x] Handoff AI automatico (prenotazione/operatore/situazione delicata) con riassunto strutturato, notifica, stop follow-up.
- [x] Clienti (ricerca) + scheda cliente (dati, social, riassunto AI, note staff, cambia stato/temperatura).
- [x] Pipeline collassabile con colonna DA FISSARE enfatizzata + Cambia Stato.
- [x] Analytics (KPI, funnel, %, per campagna) + filtri dimensionali.
- [x] Altro: Servizi (CRUD admin), Sedi (CRUD admin), Campagne, Team (add admin), Conoscenza AI (edit admin), Integrazioni (non attive Fase 2/3/4), Impostazioni (follow-up, notifiche).
- [x] Home priorità "DA FISSARE ADESSO" + centro Notifiche.
- [x] Testato: 27/27 backend + flussi frontend principali.

## Backlog / Fasi future (NON in Fase 1)
- P1 Fase 2: webhook Meta Lead Ads → creazione lead/campagna/inserzione/conversazione. [FATTO — infrastruttura + simulatore, credenziali reali da inserire]
- P1 Fase 3: WhatsApp Business Cloud API (inbound/outbound/webhook/template/stati/opt-in).
- P1 Fase 4: AI reale (provider) con Knowledge Base, storia, regole handoff via funzioni backend controllate.
- P2: follow-up realmente schedulati; notifiche push (solo su build reale); split server.py in router; analytics via aggregation pipeline; spostare retrieve_and_ingest fuori dal request path del webhook (BackgroundTask) per rispettare il timeout 5s di Meta.

## Fase 2 — Meta Lead Ads (2026-06)
- Infrastruttura tecnica completa (secrets solo lato server, `.env`: META_APP_ID/APP_SECRET/PAGE_ACCESS_TOKEN/PAGE_ID/VERIFY_TOKEN/API_VERSION):
  - GET `/api/integrations/meta/webhook` (verifica hub.challenge + verify token)
  - POST `/api/integrations/meta/webhook` (verifica X-Hub-Signature-256, parsing leadgen, Graph API retrieve → ingest) — attivo solo quando le credenziali reali sono inserite
  - `ingest_meta_lead()`: lead(nuovo_lead, origine=meta) → associazione/creazione campagna+inserzione → conversazione(ai_attiva) → messaggio AI iniziale (workflow WhatsApp simulato, reale in Fase 3) → follow-up programmato → notifica nuova_chat. Idempotente su leadgen_id.
  - GET `/api/integrations/meta/status` (verify_token visibile solo admin)
  - POST `/api/integrations/meta/simulate` (admin) — Simulatore Lead Meta
- Frontend: schermata `/altro/meta` con stato integrazione, Callback URL + Verify Token copiabili, guida passo-passo per creare l'app Meta, e Simulatore Lead (admin) che crea il lead e apre la conversazione.
- Testato: 16/16 backend (incl. idempotenza dopo fix) + flusso frontend admin end-to-end.
- DA FARE per attivazione reale: l'utente fornisce App ID, App Secret, Page Access Token, Page ID → inserimento in `.env` → configurazione webhook su Meta (Callback URL + Verify Token, campo `leadgen`) → verifica Business + App Review `leads_retrieval`.


## Fase 3 — WhatsApp + AI reale + Immagini trattamenti (2026-06)
- **AI commerciale reale**: GPT-5.4 via Emergent universal key (`EMERGENT_LLM_KEY`, `AI_MODEL`). `ai_generate_reply()` genera risposte brevi in italiano orientate alla prenotazione (bisogno→giorno→orario→appuntamento), usate sia da `simulate-ai-turn` sia dal webhook WhatsApp inbound. Handoff su intenzione di prenotare invariato.
- **Immagini trattamenti (Object Storage)**: `POST /api/upload` (admin) → Emergent Object Storage; `GET /api/files/{path}` pubblico. Campo `services.immagine`. Upload/anteprima dalla schermata Servizi (expo-image-picker). Trattamenti J'adore Mimì: Bomba, Model Leg, Lifting Colombiano, Fire Cupping, Bambolona.
- **Primo messaggio**: all'ingresso lead, foto prima/dopo del trattamento (se impostata) + copy "Ciao {nome}, sono Andrea di J'adore Mimì …" (mattina/pomeriggio). Foto solo all'inizio.
- **WhatsApp Business Cloud API**: credenziali EDITABILI da Admin e salvate nel DB (`integration_config` key=whatsapp) → numero sostituibile senza rebuild. Endpoint config GET/PATCH (token/app_secret mascherati), webhook verify/receive/status, invio `whatsapp_send_template` (immagine header + {name}/{service}) e `whatsapp_send_text` (finestra 24h). Attivi solo se configurato; URL immagine reso assoluto via `PUBLIC_BASE_URL`.
- Frontend: schermata `/altro/whatsapp` (WhatsApp Business Settings) + immagini nei Servizi + bolle immagine in chat.
- Env aggiunti: EMERGENT_LLM_KEY, AI_MODEL, AI_PROVIDER, WHATSAPP_* , PUBLIC_BASE_URL. Tutti i segreti lato server; le credenziali WhatsApp editabili sono in DB (mai nel codice).
- Testato: 19/19 backend + flusso frontend. DA FARE attivazione reale: inserire credenziali WhatsApp (numero personale per test → poi Business) da Impostazioni, creare/approvare template immagine su Meta, e per Meta Lead Ads i token reali.

## Assistente AI — avatar (2026-06)
- Config `integration_config` key=assistant `{name, avatar_url}`. GET `/api/assistant` (auth), PATCH (admin).
- Avatar ufficiale caricato su Object Storage e impostato di default. Mostrato: profilo assistente (Impostazioni → Assistente AI) con "Cambia foto" admin, e accanto ai messaggi AI in chat. Sostituibile da Admin senza codice (`useAssistant` hook lato frontend).

## Credenziali demo
admin@supergirl.app / Admin123! · operatore@supergirl.app / Operatore123!

## Fix verifica webhook WhatsApp su Meta (2026-06)
- Diagnosi (solo curl, nessun deploy): endpoint `GET /api/integrations/whatsapp/webhook` tecnicamente perfetto — HTTP 200, body raw challenge, `text/plain`, nessun redirect/CORS/blocco, raggiungibile anche dai crawler Meta/WhatsApp. Cause reali del rifiuto Meta isolate: (A) spazio/a-capo invisibile nel Verify Token copiato → 403; (B) `/` finale nel Callback URL → 307 redirect (Meta non lo segue).
- Fix applicato: (1) confronto verify_token con `.strip()` su entrambi i lati → tollera spazi/a-capo accidentali; (2) strip dei campi al salvataggio PATCH; (3) campo "Verify Token" ora EDITABILE da Admin → WhatsApp Business; (4) token attivo impostato a `supergirl2026` (corto, digitabile a mano).
- Istruzioni utente su Meta: Callback URL senza `/` finale + Verify Token `supergirl2026` (digitato) → Verifica e salva.
- Verificato via curl: token pulito/con spazio/con a-capo → 200; token errato → 403.

## Attivazione WhatsApp Cloud API reale — RISOLTA (2026-09-07, produzione)
- **Webhook**: il pulsante "Verifica e salva" della nuova UI Meta "Casi d'uso" (use_cases/customize) è ROTTO per questa app (pannello bianco, `TypeError: Failed to fetch` + richieste bloccate da CSP, nessuna mutation inviata → i server Meta non chiamavano mai il webhook). Provato: da produzione l'endpoint risponde sempre 200 con body=challenge (token `supergirl2026`, DB). Soluzione: registrazione webhook via **Graph API** `POST /{app_id}/subscriptions` (object=whatsapp_business_account, callback_url=prod, verify_token=supergirl2026, fields=messages) con app access token `{app_id}|{app_secret}` → `{"success":true}`, subscription `active:true`. Diagnostica di produzione ha catturato la GET REALE di Meta (UA `facebookplatform/1.0`, IP Facebook 69.171.242.4, challenge ok, 200). Verifica webhook COMPLETATA e permanente.
- **Diagnostica temporanea** aggiunta: collezione `wa_webhook_debug` + endpoint admin `GET /api/integrations/whatsapp/webhook-debug` (nessun token in chiaro: solo match booleano + maschera). DA RIMUOVERE quando l'utente conferma la chiusura.
- **Access token**: quello vecchio era scaduto; l'utente ha fornito nuovo token USER (scope whatsapp_business_management + messaging sul WABA). Salvato in config produzione.
- **phone_number_id CORRETTO**: era salvato `1785595714842859` (errato) → corretto in `1283595714842859` (+39 393 470 6525, verificato). Config produzione aggiornata (numero + token + phone_number_id).
- **Iscrizione WABA**: `POST /{waba_id}/subscribed_apps` → success.
- **Registrazione numero Cloud API**: `POST /{phone_number_id}/register` con PIN 2FA (token NELL'HEADER Authorization, NON nel body — il body access_token dava code 100 subcode 33). Ora status=CONNECTED, platform_type=CLOUD_API. PIN salvato in /app/memory/whatsapp_pin.md.
- **NEXT**: test end-to-end reale (utente scrive al numero → webhook inbound → AI Andrea risponde). Poi: token permanente (System User) al posto di quello temporaneo; approvazione template `nuovo_lead_foto`.

## TEST E2E WhatsApp REALE — SUCCESSO (2026-09-07, produzione)
- Fix inbound organico deployato: `handle_inbound_wa` ora crea lead+conversazione (origine=whatsapp_organico, campagna "WhatsApp Diretto") per numeri sconosciuti, poi AI risponde. `create_inbound_lead()` aggiunta.
- POST webhook: aggiunto logging diagnostico (WA_WEBHOOK_POST + wa_webhook_debug kind=inbound_post) con from/texts/sig_valid/statuses. DA RIMUOVERE a fine collaudo (insieme a GET webhook-debug + collezione wa_webhook_debug).
- Pagina Privacy pubblica: GET /api/privacy (HTMLResponse) -> per pubblicazione app Meta. URL: https://ai-conversion-4.emergent.host/api/privacy
- Profilo WhatsApp Business: nome "J'adore Mimì" (verified_name APPROVED), foto profilo = foto brandizzata Andrea (caricata via Resumable Upload API), about impostato.
- Token permanente System User (scad. MAI) salvato in prod. phone_number_id=1283595714842859 (+39 393 470 6525) CONNECTED/CLOUD_API. WABA subscribed_apps=success. App subscription webhook active.
- E2E confermato: inbound da +39 348 902 0968 -> lead "MC" -> AI reply "Ciao MC 💕..." -> status sent+read.
- PROSSIMO: pubblicare app Meta (Live + Advanced Access whatsapp_business_messaging) usando Privacy URL, per aprire a TUTTI gli utenti (oltre ai numeri di test). Poi rimuovere diagnostica.

## Pulizia + Template (2026-09-07, autonomo)
- RIMOSSA diagnostica WhatsApp: eliminati _save_wa_debug, WA_WEBHOOK_GET/POST logging, endpoint /integrations/whatsapp/webhook-debug, scritture wa_webhook_debug. Mantenuti: .strip() verify_token, fix inbound organico (create_inbound_lead), pagina /api/privacy. (Richiede REDEPLOY per attivare la pulizia in produzione.)
- Template WhatsApp "nuovo_lead_foto" (it, MARKETING, header IMAGE + body {{1}}=nome {{2}}=servizio) creato e inviato in approvazione a Meta: id 1953039642036943, status PENDING. Compatibile con whatsapp_send_template esistente.
- DA FARE (richiede input utente, non autonomo): push mobile (google-services.json + build), collegamento Lead Ads (Page Access Token + subscribe leadgen su Pagina FB), notifiche desktop/browser (frontend).

## Push notifications (2026-09-07) — Emergent managed relay
- google-services.json (progetto super-girl-5dcb8, package com.emergent.aiconversion.pj7r40) caricato in /app/frontend/google-services.json + app.json android.googleServicesFile.
- Backend: POST /api/register-push + send_push() + notify_staff_push() (relay a integrations.emergentagent.com con X-Push-Key=EMERGENT_PUSH_KEY). EMERGENT_PUSH_KEY=placeholder in backend/.env (il deployer inserisce la chiave vera al build). Chiamata in do_handoff quando motivo=="prenotazione" -> push a tutto lo staff con action_url=/conversation/{id}.
- Frontend: src/push.ts (registerForPush con getDevicePushTokenAsync), wiring in auth.tsx (login + restore), _layout.tsx con setNotificationHandler + channel default (module scope), tap handlers (warm+cold) che aprono /conversation/{id}, nudge settimanale con Linking.openSettings. app.json plugin expo-notifications aggiunto.
- LIMITE: funziona SOLO su build reale iOS/Android dopo Publish->Deploy->Generate build (NON in Expo Go/web/preview). Al build l'utente dovrà caricare Google service account JSON + APNs .p8 (guide nella UI di build).
- Nota: le push del relay gestito sono MOBILI (FCM/APNs). Le notifiche desktop/browser sul PC della segretaria NON sono coperte da questo servizio (resta la notifica in-app / campanella mentre l'app web è aperta).

## Modifiche WhatsApp (2026-09-08)
- Etichetta chat: rimosso "· AI" → in conversation/[id].tsx ora la bolla mostra solo il nome assistente ("Andrea"). Il flag AI resta interno (sender="ai" nel DB).
- Typing indicator: nuovo helper whatsapp_send_typing(message_id) → POST /{pnid}/messages con status=read + typing_indicator{type:text}. Chiamato in handle_inbound_wa subito dopo il guard ai_attiva (prima di ai_generate_reply). Mostra "Andrea sta scrivendo…" fino a ~25s o fino all'invio della risposta. Non blocca (try/except).
- Follow-up automatici (2 step 4h+giorno dopo, orari 9-19, testi modificabili + message_options), segmentazione (/segments + filtri /leads + UI chip in clienti.tsx), push notifiche, template nuovo_lead_foto + promemoria_followup (PENDING): TUTTO richiede un unico Publish->Deploy per andare live in produzione.

## Nuovo stato "IN ATTESA DI CHIAMATA" + hardening prezzi AI (2026-06, sessione fork)
- NUOVO stato pipeline `attesa_chiamata` (label "IN ATTESA DI CHIAMATA", order 5) aggiunto a PIPELINE_STAGES e a STAGES (theme.ts). È il target dell'handoff AI su intenzione di prenotare: `do_handoff` con motivo="prenotazione" → `attesa_chiamata` (gli altri motivi restano `da_fissare`). Messaggio handoff aggiornato: "Benissimo! Controllo subito le disponibilità e ti richiamo io a breve...".
- Home /home/priorities e filtro conversazioni "da_fissare" includono ora sia `attesa_chiamata` sia `da_fissare`. Analytics conteggia `attesa_chiamata` come booking-ready. _send_one_followup salta anche `attesa_chiamata`. change_status gestisce `attesa_chiamata` (handoff_at + notifica).
- Frontend: pipeline colonna evidenziata (star) + espansa di default; chat badge star anche per attesa_chiamata; scheda cliente usa STAGES keys → picker aggiornato automaticamente.
- Seed: Camilla → attesa_chiamata, Beatrice → da_fissare (una lead per colonna in demo).
- HARDENING PREZZI AI (build_ai_system_prompt): se il servizio NON ha prezzo nel DB → l'AI NON inventa e dice che verifica col team; se ha promozione → DEVE sempre citare la scadenza dinamica (promo_end gg/mm/aaaa); usa solo valori DB/KB. Verificato via curl (Bomba: prezzo esatto + "valida fino al 18/09/2026").
- Fix dati demo: rimosso servizio orfano 'Laser Diodo' (non presente in services) → collezioni demo ripopolate dal seed pulito (integration_config WhatsApp preservato).
- TEST: testing_agent E2E backend PASS (10-11/11) — handoff→attesa_chiamata, tono naturale (no "AI", no "Perfetto" ripetuto), pipeline/home/config includono lo stato. Report: /app/test_reports/iteration_5.json.
- PROSSIMO: P1 "Training Andrea" (UI Admin per KB/servizi/prezzi/promo), P1 Meta Lead Ads reali (attesa Page ID + Page Access Token utente).

## Personalità AI riscritta + typing proporzionale + niente cuori (2026-06, sessione fork)
- PERSONALITÀ (build_ai_system_prompt riscritto): Andrea = estetista/consulente donna esperta, tono caldo/confidenziale ma mai formale o robotico. Regole: DIVIETO ASSOLUTO di cuori (❤️💕💛🩷…) in ogni messaggio; altre emoji (es. 😊) solo di rado. Aperture VARIE (vietato iniziare sempre con Certo/Certamente/Perfetto/Assolutamente; usarle raramente); ammesse espressioni naturali ("Ok","Sì, guarda…","Allora…","Ti spiego","Ti dico subito…","Guarda, in questo caso…"). Confidenza alternata ("guarda","ti spiego","secondo me","in questo caso", occasionale "tesoro/cara") MA NON al primo messaggio (diventa confidenziale col progredire). Anti-schema (varia apertura/lunghezza/spiegazione/domanda/emoji/chiusura, non ripetere cose già dette). Lunghezza: breve per domande semplici, lungo solo per spiegare trattamento/promo. Incluso esempio di tono (2 modi diversi per la stessa domanda cellulite).
- GARANZIA HARD anti-cuori: `strip_hearts()` (regex su tutti i codepoint dei cuori) applicata a ogni risposta AI in ai_generate_reply. Rimossi i cuori anche da tutti i testi hardcoded live: greeting iniziale (ora senza domanda mattina/pomeriggio), messaggi di handoff (detect_handoff), follow-up di default + message_options, fallback.
- TYPING PROPORZIONALE (solo path WhatsApp reale): `typing_seconds(text)` = 1.8 + len/20, clamp [2,12]s. In handle_inbound_wa: si invia subito "Andrea sta scrivendo…", si genera la risposta, poi si attende un tempo proporzionale alla lunghezza (scontando il tempo di generazione) prima di inviare. Il POST webhook ora lancia handle_inbound_wa in background (asyncio.create_task + _safe_handle_inbound) per non bloccare il 200 a Meta durante l'attesa. NB: verificabile solo su WhatsApp reale (non in Expo Go/preview).
## Separazione SG- anche per Click-to-WhatsApp (2026-06, SOLO backend)
- Richiesta: i messaggi WhatsApp da annunci (CTWA) attivano Super Girl SOLO se annuncio o campagna ha prefisso SG-; campagne agenzia (senza SG-) NON gestite. Organico (senza annuncio) invariato.
- server.py: `sg_prefixed(name)` regex `^\s*SG\s*-` (accetta "SG-"/"SG -", case-insensitive) usata per moduli e per campagne/annunci CTWA. `form_name_allowed` usa `sg_prefixed`. `ctwa_ad_info(referral)`: da referral.source_id (ad id) via Graph → name+campaign{name}+creative(instagram) → (allowed, campagna, inserzione, piattaforma). `create_inbound_lead` accetta campagna/inserzione/piattaforma/origine.
- `handle_inbound_wa`: numero NUOVO con referral(ad) → gate SG- fail-closed (non-SG o non risolvibile → RETURN, niente lead/risposta); SG- → lead con campagna/annuncio reali + AI. Nessun referral → organico standard. Lead esistenti non ri-filtrati.
- Test offline: sg_prefixed 8/8; ctwa_ad_info SG→True, agenzia→False, non-leggibile→False, no source_id→False. Richiede REDEPLOY per la produzione (no build APK).

## Regola SOLO-BACKEND: importa solo moduli "SG -" (2026-06, AUTORITATIVA)
- Richiesta utente: Super Girl importa i lead SOLO dai moduli Meta il cui NOME inizia con "SG -" (es. "SG - Model Leg settembre"). Tutti gli altri moduli (agenzia) ignorati. Nessuna schermata (per non richiedere build Android).
- Implementazione (server.py): costante `SG_FORM_PREFIX = os.environ.get("META_FORM_PREFIX","SG -")`. In `retrieve_and_ingest` si recupera il nome del modulo (nodo lead `form{id,name}`, fallback `graph_get(form_id,"name")`) e si applica `form_name_allowed()` = nome.strip().upper().startswith("SG -"). FAIL-CLOSED: se il nome non è disponibile → lead IGNORATO (protegge i moduli dell'agenzia e blocca import in fase di config). `form_name` salvato sul lead.
- Rimossa la schermata `app/altro/moduli-meta.tsx` e il link in meta.tsx (l'utente vuole solo backend). Gli endpoint whitelist (forms/filter-mode) restano ma NON sono più il gate: la regola prefisso è autoritativa e sempre attiva (default filter_mode "all").
- Test offline (mock Graph): SG - → importato (form_name salvato); nome agenzia → skip reason=form_prefix; nome assente → skip (fail-closed). Unit test form_name_allowed: 9/9 OK.
- IMPORTANTE: è modifica SOLO backend → NON richiede una nuova build Android. Per essere live in PRODUZIONE (emergent.host) serve comunque un REDEPLOY del backend (non un build APK) + i segreti Meta nel Deployment. In fase di test usare un modulo "SG - TEST".

## Filtro moduli Meta (form_id whitelist) + schermata gestione (2026-06)
- Obiettivo utente: Super Girl deve acquisire SOLO i lead dei moduli (form_id) scelti dall'utente, senza toccare l'integrazione dell'agenzia sulla stessa Pagina.
- Backend (server.py): nuova modalità `filter_mode` in `db.meta_settings` ("all" default = tutti i moduli; "whitelist" = solo attivati). Collezione `db.meta_forms` {form_id, name, status, leads_count, enabled}. Endpoint admin: `GET /integrations/meta/forms` (Graph `/{page}/leadgen_forms` + merge stato DB; fallback ai moduli salvati se Graph 403), `POST /integrations/meta/forms/{form_id}` {enabled,name} (upsert toggle), `POST /integrations/meta/filter-mode` {mode}. `meta_status` ora ritorna filter_mode + enabled_forms.
- Webhook `leadgen`: in modalità whitelist ingerisce SOLO i form_id attivati (altri loggati e ignorati); AUTO-SCOPERTA: ogni form_id in arrivo viene registrato in meta_forms (enabled=false) così compare nell'app. `form_id` salvato anche sul lead.
- Nota permesso: listare i moduli via Graph richiede `pages_manage_ads` (token attuale non ce l'ha → 403 gestito): i moduli compaiono comunque tramite auto-scoperta o aggiunta manuale per ID.
- Frontend: nuova schermata `app/altro/moduli-meta.tsx` (switch modalità filtro, lista moduli con Switch per attivare/disattivare, aggiunta manuale per ID, pull-to-refresh). Link da `app/altro/meta.tsx` ("Moduli lead collegati", solo admin).
- Test: curl (filter-mode, toggle, listing fallback, webhook 3 casi: attivo→ingest, non attivo→skip, nuovo→auto-scoperto) + screenshot interazione (attiva whitelist, aggiungi modulo → compare attivo). L'integrazione dell'agenzia NON è toccata (il filtro agisce solo nell'ingestione di Super Girl).
- PRODUZIONE: essendo codice + config, per andare live sull'app installata serve (a) impostare i segreti Meta mancanti nel Deployment (META_APP_ID, META_PAGE_ID, META_PAGE_ACCESS_TOKEN; APP_SECRET/VERIFY già presenti) e (b) un redeploy (il backend deployato su emergent.host usa uno snapshot, DB separato dai 13 lead demo dell'anteprima; ha i lead reali).

## Setup Meta Lead Ads (2026-06)
- Token Pagina validato (Pagina "J'adore Mimì 2025", id 489009670970857, app 1080460221022637; scopes: leads_retrieval, ads_management, pages_read_engagement, pages_show_list). Scadenza ~set 2026 (non permanente → valutare System User token).
- Sottoscrizione Pagina→app `leadgen`: success:true. Sottoscrizione app-level object=page fields=leadgen callback `https://ai-conversion-4.emergent.host/api/integrations/meta/webhook` verify token `sg_meta_verify_...` → active:true (Meta ha verificato la callback). App-secret firma webhook OK (403 su firma errata). Secrets Meta salvati in `/app/backend/.env` (anteprima); su deployato mancano PAGE_ID/PAGE_TOKEN/APP_ID.
