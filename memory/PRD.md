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

## Credenziali demo
admin@supergirl.app / Admin123! · operatore@supergirl.app / Operatore123!
