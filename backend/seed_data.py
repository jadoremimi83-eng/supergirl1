"""Seed dati demo per SUPER GIRL — Fase 1.

Popola: users (admin+operatore), services, locations, campaigns,
knowledge_base, followup_rules, settings, e 13 lead distribuiti negli stati
della pipeline con conversazioni WhatsApp realistiche simulate.
Tutti i dati aziendali sono FITTIZI.
"""
import uuid
import bcrypt
from datetime import datetime, timedelta, timezone


def now_utc():
    return datetime.now(timezone.utc)


def iso(dt):
    return dt.astimezone(timezone.utc).isoformat()


def h(pw):
    return bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()


# Profili social FITTIZI per la demo (Fase 1). Alcuni lead non hanno foto/IG
# per simulare i casi in cui Meta non fornisce il dato -> avatar neutro.
def _p(name, w):
    return f"https://randomuser.me/api/portraits/women/{w}.jpg"


IG_PROFILES = {
    "Martina":   {"piattaforma": "Instagram", "ig_username": "@marti_fit88",
                  "ig_display_name": "Martina R.", "foto_profilo": _p("m", 1)},
    "Chiara":    {"piattaforma": "Facebook", "ig_username": None,
                  "ig_display_name": "Chiara Bianchi", "foto_profilo": None},
    "Federica":  {"piattaforma": "Instagram", "ig_username": "@fede.conti",
                  "ig_display_name": "Fede", "foto_profilo": _p("f", 3)},
    "Alessia":   {"piattaforma": "Instagram", "ig_username": "@ale_glow",
                  "ig_display_name": "Alessia F.", "foto_profilo": _p("a", 4)},
    "Valentina": {"piattaforma": "Instagram", "ig_username": "@vale.ry",
                  "ig_display_name": "Vale", "foto_profilo": _p("v", 5)},
    "Elena":     {"piattaforma": "Facebook", "ig_username": None,
                  "ig_display_name": "Elena Greco", "foto_profilo": _p("e", 6)},
    "Giorgia":   {"piattaforma": "Instagram", "ig_username": "@gio_deluca",
                  "ig_display_name": "Giorgia", "foto_profilo": _p("g", 7)},
    "Sofia":     {"piattaforma": "Instagram", "ig_username": "@sofia.marino",
                  "ig_display_name": "Sofia M.", "foto_profilo": _p("s", 8)},
    "Beatrice":  {"piattaforma": "Instagram", "ig_username": "@bea_fontana",
                  "ig_display_name": "Bea", "foto_profilo": _p("b", 9)},
    "Camilla":   {"piattaforma": "Instagram", "ig_username": "@cami.villa",
                  "ig_display_name": "Camilla V.", "foto_profilo": _p("c", 10)},
    "Ludovica":  {"piattaforma": "Instagram", "ig_username": "@ludo.costa",
                  "ig_display_name": "Ludo", "foto_profilo": _p("l", 11)},
    "Francesca": {"piattaforma": "Instagram", "ig_username": "@franci_m",
                  "ig_display_name": "Franci", "foto_profilo": None},
    "Ilaria":    {"piattaforma": "Instagram", "ig_username": "@ila.barbieri",
                  "ig_display_name": "Ilaria B.", "foto_profilo": _p("i", 13)},
}


async def seed_database(db):
    if await db.users.count_documents({}) > 0:
        return  # già popolato

    # ------------------------------------------------------------------ USERS
    admin_id = str(uuid.uuid4())
    op_id = str(uuid.uuid4())
    users = [
        {"id": admin_id, "name": "Giulia Admin", "email": "admin@supergirl.app",
         "role": "admin", "password_hash": h("Admin123!"),
         "avatar_color": "#D4AF37"},
        {"id": op_id, "name": "Sara Operatrice", "email": "operatore@supergirl.app",
         "role": "operator", "password_hash": h("Operatore123!"),
         "avatar_color": "#B68D40"},
    ]
    await db.users.insert_many(users)

    # -------------------------------------------------------------- LOCATIONS
    locations = [
        {"id": str(uuid.uuid4()), "nome": "Milano Centro",
         "indirizzo": "Via della Spiga 12, Milano", "telefono": "+39 02 1234567",
         "orari": "Lun-Sab 9:00-19:00", "info": "Parcheggio convenzionato in zona."},
        {"id": str(uuid.uuid4()), "nome": "Verona",
         "indirizzo": "Via Mazzini 24, Verona", "telefono": "+39 045 7654321",
         "orari": "Lun-Ven 9:30-19:30, Sab 9:30-14:00",
         "info": "A 5 minuti da Piazza Bra."},
    ]
    await db.locations.insert_many(locations)

    # --------------------------------------------------------------- SERVICES
    services = [
        {"id": str(uuid.uuid4()), "nome": "Bomba",
         "descrizione": "Trattamento corpo d'urto anti-cellulite e drenante, rimodella e sgonfia.",
         "prezzo": "€90 a seduta · Pacchetto 5 sedute €399",
         "promozione": "Prima seduta di prova a €49",
         "info": "Ideale per cellulite, ritenzione e girovita. Ciclo consigliato 5-8 sedute.",
         "faq": "Fa male? No, è drenante e rilassante.", "immagine": ""},
        {"id": str(uuid.uuid4()), "nome": "Model Leg",
         "descrizione": "Trattamento gambe leggere: drena, sgonfia e tonifica.",
         "prezzo": "€80 a seduta · Pacchetto 5 €359",
         "promozione": "", "info": "Perfetto per gambe gonfie e pesanti.",
         "faq": "Ogni quanto? 1-2 volte a settimana.", "immagine": ""},
        {"id": str(uuid.uuid4()), "nome": "Lifting Colombiano",
         "descrizione": "Massaggio rassodante e rimodellante corpo effetto lifting.",
         "prezzo": "€100 a seduta",
         "promozione": "Pacchetto 6 sedute €499", "info": "Tonifica glutei e silhouette.",
         "faq": "Risultati? Visibili dal ciclo completo.", "immagine": ""},
        {"id": str(uuid.uuid4()), "nome": "Fire Cupping",
         "descrizione": "Coppettazione a caldo: drena, decontrae e attiva la circolazione.",
         "prezzo": "€70 a seduta",
         "promozione": "", "info": "Ottimo su schiena e zone con ritenzione.",
         "faq": "Lascia segni? Un lieve arrossamento temporaneo.", "immagine": ""},
        {"id": str(uuid.uuid4()), "nome": "Bambolona",
         "descrizione": "Trattamento viso illuminante e rimpolpante effetto bambola.",
         "prezzo": "€75 a seduta",
         "promozione": "Prima consulenza viso gratuita",
         "info": "Pelle luminosa e compatta.", "faq": "Adatto a pelli sensibili? Sì.",
         "immagine": ""},
    ]
    await db.services.insert_many(services)

    # Alias: mappa i vecchi nomi demo ai trattamenti reali (per i lead seed)
    svc = {
        "Trattamento Corpo Rimodellante": "Bomba",
        "Pulizia Viso Profonda": "Bambolona",
        "Laser Epilazione Definitiva": "Model Leg",
        "Medicina Estetica Viso": "Lifting Colombiano",
    }

    # --------------------------------------------------------------- CAMPAIGNS
    campaigns = [
        {"id": str(uuid.uuid4()), "nome": "Corpo Estate 2026",
         "inserzioni": ["Video Addome Piatto", "Carosello Rimodellante"],
         "servizio": "Trattamento Corpo Rimodellante"},
        {"id": str(uuid.uuid4()), "nome": "Viso Glow",
         "inserzioni": ["Foto Prima/Dopo Viso", "Reel Pelle Luminosa"],
         "servizio": "Pulizia Viso Profonda"},
        {"id": str(uuid.uuid4()), "nome": "Epilazione Definitiva",
         "inserzioni": ["Promo Pacchetto Ascelle+Inguine", "Video Laser Diodo"],
         "servizio": "Laser Epilazione Definitiva"},
    ]
    await db.campaigns.insert_many(campaigns)

    # --------------------------------------------------------- KNOWLEDGE BASE
    await db.knowledge_base.insert_one({
        "id": str(uuid.uuid4()),
        "azienda": "J'adore Mimì è un centro di estetica avanzata con sedi a Milano "
                   "e Roma. Trattamenti corpo e viso: Bomba, Model Leg, Lifting "
                   "Colombiano, Fire Cupping, Bambolona.",
        "servizi": "Bomba (anti-cellulite/drenante), Model Leg (gambe leggere), "
                   "Lifting Colombiano (rassodante corpo), Fire Cupping (coppettazione), "
                   "Bambolona (viso illuminante).",
        "prezzi": "Trattamento Corpo €120/seduta (pacchetto 5 a €499). "
                  "Pulizia Viso €70. Laser da €50 a zona. "
                  "Medicina estetica su valutazione medica.",
        "promozioni": "Prima consulenza corpo gratuita. Pacchetto laser "
                      "ascelle+inguine a €399.",
        "sedi": "Milano Centro (Via della Spiga 12) e Verona "
                "(Via Mazzini 24).",
        "orari": "Milano: Lun-Sab 9-19. Verona: Lun-Ven 9:30-19:30, Sab 9:30-14.",
        "faq": "Quante sedute servono? Dipende dal trattamento. "
               "I trattamenti sono dolorosi? Generalmente no.",
        "obiezioni": "'Costa troppo' -> valorizzare i risultati e i pacchetti. "
                     "'Non ho tempo' -> proporre orari flessibili. "
                     "'Ho paura del dolore' -> rassicurare sulle tecnologie usate.",
        "pagamenti": "Contanti, carte, bancomat. Possibilità di rateizzazione "
                     "sui pacchetti.",
        "tono_di_voce": "Caldo, empatico, femminile, professionale. Messaggi brevi "
                        "adatti a WhatsApp. Una domanda alla volta.",
        "info_commerciali": "Obiettivo: portare i lead qualificati a fissare una "
                            "prima visita/consulenza.",
        "istruzioni": "Non inventare mai informazioni. Se non conosci la risposta, "
                      "di' che farai intervenire lo staff.",
        "non_comunicare": "Non comunicare mai indirizzi email interni, dati di "
                          "altri clienti o dettagli medici non verificati.",
    })

    # ------------------------------------------------------- FOLLOWUP RULES
    await db.followup_rules.insert_one({
        "id": str(uuid.uuid4()),
        "enabled": True,
        "steps": [
            {"label": "Follow-up 1", "delay": "2 ore",
             "message": "Ciao! Sono ancora qui se vuoi qualche informazione 😊"},
            {"label": "Follow-up 2", "delay": "24 ore",
             "message": "Ciao! Volevo sapere se posso aiutarti a scegliere il "
                        "trattamento più adatto a te 💛"},
            {"label": "Follow-up 3", "delay": "3 giorni",
             "message": "Ultimo messaggio da parte mia 😊 Se vuoi resto a "
                        "disposizione quando preferisci!"},
        ],
    })

    # ----------------------------------------------------------- SETTINGS
    await db.settings.insert_one({
        "id": str(uuid.uuid4()),
        "account": {"azienda": "SUPER GIRL", "email": "admin@supergirl.app"},
        "sicurezza": {"twofa": False},
        "ai": {"attiva": True, "modello": "Demo (simulato)",
               "handoff_su_prenotazione": True},
        "notifiche": {"cliente_da_fissare": True, "ai_intervento": True,
                      "nuova_chat": True, "nuovo_messaggio": True},
    })

    # ------------------------------------------------------------------ LEADS
    N = now_utc()

    def conv_id():
        return str(uuid.uuid4())

    leads = []
    conversations = []
    messages = []
    notifications = []
    history = []
    handoffs = []
    followups = []

    def add_lead(nome, cognome, tel, email, servizio, sede, campagna, inserzione,
                 stato, temp, days_ago, operatore, ai_attiva, unread,
                 msgs, esigenza="", obiezioni="", ai_summary=None,
                 handoff_ago_hours=None):
        lid = str(uuid.uuid4())
        cid = conv_id()
        acq = N - timedelta(days=days_ago)
        last = msgs[-1][2] if msgs else acq
        handoff_at = None
        if handoff_ago_hours is not None:
            handoff_at = iso(N - timedelta(hours=handoff_ago_hours))
        social = IG_PROFILES.get(nome, {
            "piattaforma": "Instagram", "ig_username": None,
            "ig_display_name": None, "foto_profilo": None})
        lead = {
            "id": lid, "nome": nome, "cognome": cognome, "telefono": tel,
            "email": email, "servizio": servizio, "sede": sede,
            "campagna": campagna, "inserzione": inserzione,
            "piattaforma": social["piattaforma"],
            "ig_username": social["ig_username"],
            "ig_display_name": social["ig_display_name"],
            "foto_profilo": social["foto_profilo"],
            "data_acquisizione": iso(acq), "ultimo_contatto": iso(last),
            "stato_pipeline": stato, "temperature": temp,
            "operatore_assegnato": operatore, "esigenza": esigenza,
            "obiezioni": obiezioni, "note_staff": "",
            "ai_summary": ai_summary, "handoff_at": handoff_at,
        }
        leads.append(lead)
        conversations.append({
            "id": cid, "lead_id": lid, "ai_attiva": ai_attiva, "stato": stato,
            "unread": unread, "operatore": operatore,
            "last_message": msgs[-1][1] if msgs else "",
            "last_message_at": iso(last),
        })
        for sender, text, ts in msgs:
            messages.append({
                "id": str(uuid.uuid4()), "conversation_id": cid,
                "sender": sender, "text": text, "created_at": iso(ts),
                "read": True,
            })
        return lead, cid

    def t(days_ago, mins=0):
        return N - timedelta(days=days_ago) + timedelta(minutes=mins)

    # ---- 2 NUOVO LEAD ----
    add_lead("Martina", "Rossi", "+39 331 1112233", "martina.rossi@email.it",
             svc["Trattamento Corpo Rimodellante"], "Milano Centro",
             "Corpo Estate 2026", "Video Addome Piatto",
             "nuovo_lead", "da_coltivare", 0, None, True, 1,
             [("cliente", "Salve, ho visto la pubblicità su Instagram", t(0, 1))],
             esigenza="Rimodellamento addome")

    add_lead("Chiara", "Bianchi", "+39 340 2223344", "chiara.b@email.it",
             svc["Laser Epilazione Definitiva"], "Verona",
             "Epilazione Definitiva", "Promo Pacchetto Ascelle+Inguine",
             "nuovo_lead", "da_coltivare", 0, None, True, 1,
             [("cliente", "Buongiorno, informazioni sul laser", t(0, 5))],
             esigenza="Epilazione ascelle e inguine")

    # ---- 2 AI IN CONVERSAZIONE ----
    add_lead("Federica", "Conti", "+39 333 4445566", "fede.conti@email.it",
             svc["Trattamento Corpo Rimodellante"], "Milano Centro",
             "Corpo Estate 2026", "Carosello Rimodellante",
             "ai_conversazione", "da_coltivare", 1, None, True, 0,
             [("cliente", "Ciao, vorrei info sul trattamento corpo", t(1, 0)),
              ("ai", "Ciao Federica! Che bello sentirti 😊 Posso chiederti "
                     "qual è l'obiettivo principale che vorresti raggiungere?", t(1, 2)),
              ("cliente", "Vorrei ridurre la pancetta dopo la gravidanza", t(1, 6)),
              ("ai", "Capisco benissimo, è una richiesta molto comune. "
                     "C'è una zona in particolare su cui vorresti lavorare?", t(1, 8))],
             esigenza="Riduzione addome post gravidanza")

    add_lead("Alessia", "Ferrari", "+39 320 5556677", "alessia.f@email.it",
             svc["Pulizia Viso Profonda"], "Verona",
             "Viso Glow", "Reel Pelle Luminosa",
             "ai_conversazione", "da_coltivare", 2, None, True, 0,
             [("cliente", "Salve, ho la pelle spenta, cosa consigliate?", t(2, 0)),
              ("ai", "Ciao Alessia! Per aiutarti al meglio posso chiederti "
                     "qual è il tuo obiettivo principale? 😊", t(2, 3))],
             esigenza="Pelle spenta, vuole luminosità")

    # ---- 2 IN ATTESA CLIENTE ----
    add_lead("Valentina", "Russo", "+39 347 6667788", "vale.russo@email.it",
             svc["Laser Epilazione Definitiva"], "Milano Centro",
             "Epilazione Definitiva", "Video Laser Diodo",
             "in_attesa", "interessata", 3, None, True, 0,
             [("cliente", "Quanto costa il laser gambe complete?", t(3, 0)),
              ("ai", "Ciao Valentina! Le gambe complete rientrano nei nostri "
                     "pacchetti dedicati. Preferisci la sede di Milano o Roma? 😊",
               t(3, 4))],
             esigenza="Laser gambe complete")

    add_lead("Elena", "Greco", "+39 349 7778899", "elena.greco@email.it",
             svc["Trattamento Corpo Rimodellante"], "Verona",
             "Corpo Estate 2026", "Video Addome Piatto",
             "in_attesa", "da_coltivare", 4, None, True, 0,
             [("cliente", "Il trattamento corpo fa male?", t(4, 0)),
              ("ai", "Assolutamente no Elena, è un trattamento rilassante 💛 "
                     "Hai già provato trattamenti simili in passato?", t(4, 2))],
             esigenza="Info trattamento corpo, teme il dolore",
             obiezioni="Paura del dolore")

    # ---- 2 INTERESSATE ----
    add_lead("Giorgia", "De Luca", "+39 351 8889900", "giorgia.dl@email.it",
             svc["Medicina Estetica Viso"], "Milano Centro",
             "Viso Glow", "Foto Prima/Dopo Viso",
             "interessata", "interessata", 5, "Sara Operatrice", True, 0,
             [("cliente", "Mi interessa molto il filler labbra", t(5, 0)),
              ("ai", "Che bello Giorgia! Il filler labbra è molto richiesto. "
                     "Preferisci un effetto naturale o più definito? 😊", t(5, 3)),
              ("cliente", "Naturale, ho un po' paura dell'effetto finto", t(5, 20)),
              ("ai", "Ti capisco perfettamente 💛 I nostri medici lavorano proprio "
                     "per un risultato armonioso e naturale. Vuoi maggiori dettagli?",
               t(5, 22)),
              ("cliente", "Sì volentieri, e vorrei sapere il prezzo", t(5, 40))],
             esigenza="Filler labbra effetto naturale",
             obiezioni="Paura effetto finto")

    add_lead("Sofia", "Marino", "+39 352 9990011", "sofia.marino@email.it",
             svc["Trattamento Corpo Rimodellante"], "Verona",
             "Corpo Estate 2026", "Carosello Rimodellante",
             "interessata", "molto_calda", 6, "Sara Operatrice", True, 0,
             [("cliente", "Ho visto i risultati sul carosello, wow!", t(6, 0)),
              ("ai", "Grazie Sofia! 😊 Risultati così si ottengono col ciclo "
                     "completo. Su quale zona vorresti concentrarti?", t(6, 2)),
              ("cliente", "Addome e fianchi. Quanto dura una seduta?", t(6, 30)),
              ("ai", "Circa 45 minuti a seduta 💛 Molto rilassante. "
                     "Ti piacerebbe organizzare una prima visita conoscitiva?",
               t(6, 32))],
             esigenza="Rimodellamento addome e fianchi")

    # ---- 2 DA FISSARE ----
    l1, c1 = add_lead(
        "Beatrice", "Fontana", "+39 333 1234567", "bea.fontana@email.it",
        svc["Trattamento Corpo Rimodellante"], "Milano Centro",
        "Corpo Estate 2026", "Video Addome Piatto",
        "da_fissare", "molto_calda", 2, "Sara Operatrice", False, 0,
        [("cliente", "Vorrei info sul trattamento corpo, zona addome", t(2, 0)),
         ("ai", "Ciao Beatrice! 😊 Il trattamento addome è tra i più richiesti. "
                "Qual è il tuo obiettivo principale?", t(2, 5)),
         ("cliente", "Ridurre il girovita, ho chiesto anche i risultati", t(2, 20)),
         ("ai", "Con il ciclo completo i risultati sul girovita sono ottimi 💛 "
                "Vuoi conoscere i prezzi?", t(2, 22)),
         ("cliente", "Sì e vorrei venire venerdì pomeriggio", t(2, 40)),
         ("ai", "Che bello! 😊 Ti metto subito in contatto con una nostra "
                "specialista che ti ricontatterà a brevissimo per fissare "
                "l'appuntamento nel giorno che preferisci. A prestissimo! 💛",
          t(2, 41))],
        esigenza="Riduzione girovita, zona addome",
        obiezioni="Ha chiesto risultati e prezzo",
        ai_summary=(
            "Nome cliente: Beatrice Fontana\n"
            "Servizio richiesto: Trattamento Corpo Rimodellante\n"
            "Sede: Milano Centro\n"
            "Livello di interesse: Molto Calda\n"
            "Esigenza principale: Riduzione girovita, zona addome\n"
            "Domande effettuate: Ha chiesto risultati e prezzo | Quando può venire\n"
            "Eventuali obiezioni: Nessuna, molto motivata\n"
            "Ultima richiesta della cliente: Vorrei venire venerdì pomeriggio\n"
            "Motivo del passaggio allo staff: La cliente ha manifestato "
            "l'intenzione concreta di prenotare."),
        handoff_ago_hours=2)

    l2, c2 = add_lead(
        "Camilla", "Villa", "+39 334 7654321", "camilla.villa@email.it",
        svc["Laser Epilazione Definitiva"], "Verona",
        "Epilazione Definitiva", "Promo Pacchetto Ascelle+Inguine",
        "attesa_chiamata", "molto_calda", 1, "Sara Operatrice", False, 0,
        [("cliente", "Buongiorno, mi interessa il pacchetto ascelle e inguine",
          t(1, 0)),
         ("ai", "Ciao Camilla! Ottima scelta 😊 Il pacchetto è in promo a €399. "
                "Hai già fatto sedute di laser in passato?", t(1, 3)),
         ("cliente", "No, è la prima volta. Fa male?", t(1, 15)),
         ("ai", "Tranquilla 💛 Grazie al sistema di raffreddamento la sensazione "
                "è minima. Vuoi che ti spieghi come funziona la prima seduta?",
          t(1, 17)),
         ("cliente", "Sì. Anzi, vorrei direttamente prenotare la prima seduta",
          t(1, 30)),
         ("ai", "Che bello! 😊 Ti metto subito in contatto con una nostra "
                "specialista che ti ricontatterà a brevissimo per fissare "
                "l'appuntamento nel giorno che preferisci. A prestissimo! 💛",
          t(1, 31))],
        esigenza="Pacchetto laser ascelle + inguine",
        obiezioni="Prima volta, chiedeva se fa male",
        ai_summary=(
            "Nome cliente: Camilla Villa\n"
            "Servizio richiesto: Laser Epilazione Definitiva (pacchetto ascelle+inguine)\n"
            "Sede: Roma Prati\n"
            "Livello di interesse: Molto Calda\n"
            "Esigenza principale: Pacchetto laser ascelle + inguine\n"
            "Domande effettuate: Fa male? | Come funziona la prima seduta\n"
            "Eventuali obiezioni: Prima volta, timore del dolore (rassicurata)\n"
            "Ultima richiesta della cliente: Vorrei direttamente prenotare la prima seduta\n"
            "Motivo del passaggio allo staff: La cliente ha manifestato "
            "l'intenzione concreta di prenotare."),
        handoff_ago_hours=20)

    # ---- 1 APPUNTAMENTO FISSATO ----
    add_lead("Ludovica", "Costa", "+39 335 1122334", "ludo.costa@email.it",
             svc["Pulizia Viso Profonda"], "Milano Centro",
             "Viso Glow", "Foto Prima/Dopo Viso",
             "appuntamento_fissato", "molto_calda", 7, "Sara Operatrice", False, 0,
             [("cliente", "Vorrei prenotare una pulizia viso", t(7, 0)),
              ("ai", "Che bello! 😊 Ti metto subito in contatto con una nostra "
                     "specialista. A prestissimo! 💛", t(7, 2)),
              ("operatore", "Ciao Ludovica, sono Sara 💛 Ti va bene martedì alle 16?",
               t(6, 0)),
              ("cliente", "Perfetto, confermo martedì alle 16!", t(6, 30)),
              ("operatore", "Fantastico, ti aspettiamo! A martedì 😊", t(6, 32))],
             esigenza="Pulizia viso, cliente già fissata",
             ai_summary=(
                 "Nome cliente: Ludovica Costa\n"
                 "Servizio richiesto: Pulizia Viso Profonda\n"
                 "Sede: Milano Centro\n"
                 "Livello di interesse: Molto Calda\n"
                 "Appuntamento: Martedì ore 16:00 (confermato dallo staff)"))

    # ---- 1 NON INTERESSATA ----
    add_lead("Francesca", "Moretti", "+39 336 5566778", "franci.m@email.it",
             svc["Medicina Estetica Viso"], "Verona",
             "Viso Glow", "Reel Pelle Luminosa",
             "non_interessata", "non_qualificata", 8, None, False, 0,
             [("cliente", "Avevo cliccato per sbaglio, non sono interessata",
               t(8, 0)),
              ("ai", "Nessun problema 😊 Resto a disposizione se cambierai idea. "
                     "Ti auguro una splendida giornata! 💛", t(8, 1))],
             esigenza="Click accidentale")

    # ---- 1 PERSA / NON RISPONDE ----
    add_lead("Ilaria", "Barbieri", "+39 337 9988776", "ilaria.b@email.it",
             svc["Trattamento Corpo Rimodellante"], "Milano Centro",
             "Corpo Estate 2026", "Carosello Rimodellante",
             "persa", "non_qualificata", 10, None, True, 0,
             [("cliente", "Info trattamento", t(10, 0)),
              ("ai", "Ciao Ilaria! 😊 Qual è il tuo obiettivo principale?", t(10, 2)),
              ("ai", "Ciao! Sono ancora qui se vuoi qualche informazione 😊",
               t(9, 0)),
              ("ai", "Ultimo messaggio da parte mia 😊 Resto a disposizione!",
               t(7, 0))],
             esigenza="Non ha più risposto dopo i follow-up")

    await db.leads.insert_many(leads)
    await db.conversations.insert_many(conversations)
    if messages:
        await db.messages.insert_many(messages)

    # -------------------------------------------------- STATUS HISTORY (base)
    for l in leads:
        history.append({
            "id": str(uuid.uuid4()), "lead_id": l["id"],
            "from_status": None, "to_status": "nuovo_lead",
            "changed_by": "ai", "created_at": l["data_acquisizione"],
        })
        if l["stato_pipeline"] != "nuovo_lead":
            history.append({
                "id": str(uuid.uuid4()), "lead_id": l["id"],
                "from_status": "nuovo_lead", "to_status": l["stato_pipeline"],
                "changed_by": "ai" if l["stato_pipeline"] in
                ("ai_conversazione", "in_attesa", "attesa_chiamata", "da_fissare") else "staff",
                "created_at": l["ultimo_contatto"],
            })
    await db.lead_status_history.insert_many(history)

    # ---------------------------------------------------------- NOTIFICATIONS
    for l in [l1, l2]:
        notifications.append({
            "id": str(uuid.uuid4()), "tipo": "cliente_da_fissare",
            "lead_id": l["id"], "lead_nome": f"{l['nome']} {l['cognome']}",
            "text": "Cliente pronta da fissare! Passata dall'AI allo staff.",
            "read": False, "created_at": l["handoff_at"],
        })
        handoffs.append({
            "id": str(uuid.uuid4()), "lead_id": l["id"],
            "conversation_id": c1 if l is l1 else c2,
            "motivo": "prenotazione", "summary": l["ai_summary"],
            "gestito_da": None, "created_at": l["handoff_at"],
        })
    notifications.append({
        "id": str(uuid.uuid4()), "tipo": "nuova_chat",
        "lead_id": leads[0]["id"], "lead_nome": "Martina Rossi",
        "text": "Nuovo lead da Meta: Martina Rossi",
        "read": False, "created_at": leads[0]["data_acquisizione"],
    })
    await db.notifications.insert_many(notifications)
    await db.ai_handoffs.insert_many(handoffs)

    # ---------------------------------------------- FOLLOWUP (programmati demo)
    for l in leads:
        if l["stato_pipeline"] in ("nuovo_lead", "ai_conversazione", "in_attesa"):
            followups.append({
                "id": str(uuid.uuid4()), "lead_id": l["id"],
                "label": "Follow-up 1", "delay": "2 ore",
                "status": "programmato", "created_at": iso(N),
                "updated_at": iso(N),
            })
    if followups:
        await db.followups.insert_many(followups)

    print(f"[SEED] SUPER GIRL: {len(leads)} lead, {len(messages)} messaggi creati.")
