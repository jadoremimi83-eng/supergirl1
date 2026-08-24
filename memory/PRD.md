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
- P1 Fase 2: webhook Meta Lead Ads → creazione lead/campagna/inserzione/conversazione.
- P1 Fase 3: WhatsApp Business Cloud API (inbound/outbound/webhook/template/stati/opt-in).
- P1 Fase 4: AI reale (provider) con Knowledge Base, storia, regole handoff via funzioni backend controllate.
- P2: follow-up realmente schedulati; notifiche push (solo su build reale); split server.py in router; analytics via aggregation pipeline.

## Credenziali demo
admin@supergirl.app / Admin123! · operatore@supergirl.app / Operatore123!
