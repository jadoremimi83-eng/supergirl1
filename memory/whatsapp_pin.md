# WhatsApp Cloud API — dati di registrazione numero (RISERVATO, server-side)

NON comunicare il PIN all'utente su sua esplicita richiesta ("scegli un PIN che ricordi, non comunicarlo a me").
Conservato qui per continuità operativa / ri-registrazione futura.

- Numero business: +39 393 470 6525
- display_phone_number: +39 393 470 6525
- phone_number_id (CORRETTO): 1283595714842859
- WABA ID: 1213843550375485
- Meta App ID: 1080460221022637
- verified_name: J'adore Mimì (name_status: APPROVED)
- Two-step verification PIN (impostato via /register): 633799
- Stato al 2026-09-07: status=CONNECTED, platform_type=CLOUD_API

Nota: il phone_number_id precedentemente salvato (1785595714842859) era ERRATO.
Altri numeri sul WABA (NON verificati): +39 393 227 4428 (1329476453580241), +39 328 091 1717 (1222201297652324).

## Aggiornamento 2026-09-07 (pomeriggio)
- Token TEMPORANEO precedente: scaduto (duravano poche ore).
- Nuovo token: **SYSTEM_USER, scadenza MAI (permanente)**, scopes whatsapp_business_management + whatsapp_business_messaging. Salvato in config produzione (••••ZDZD).
- WABA: account_review_status=APPROVED, business_verification_status=verified, ownership SELF.
- subscribed_apps: success. App subscription webhook: active.
- Numero +39 393 470 6525: CONNECTED / CLOUD_API / VERIFIED / name APPROVED.
- NESSUN template esiste ancora sul WABA (message_templates vuoto) -> per messaggi business-first serve creare/approvare un template (es. nuovo_lead_foto). Test in ENTRATA non richiede template.
