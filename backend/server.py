"""SUPER GIRL — CRM conversazionale (Fase 1: Demo).

Backend FastAPI + MongoDB. Tutta la logica AI e le transizioni di stato vivono
qui, dietro funzioni controllate, così la Fase 4 (AI reale) potrà sostituire
l'implementazione interna senza toccare frontend o schema.
"""
import os
import re
import json
import uuid
import hmac
import hashlib
import logging
import asyncio
import requests
from pathlib import Path
from datetime import datetime, timedelta, timezone
try:
    from zoneinfo import ZoneInfo
    ROME_TZ = ZoneInfo("Europe/Rome")
except Exception:
    ROME_TZ = timezone(timedelta(hours=2))
from typing import List, Optional

import jwt
import bcrypt
import httpx
from fastapi import (FastAPI, APIRouter, Depends, HTTPException, status, Query,
                     Request, UploadFile, File)
from fastapi.responses import PlainTextResponse, Response, HTMLResponse
from fastapi.concurrency import run_in_threadpool
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from emergentintegrations.llm.chat import LlmChat, UserMessage
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

mongo_url = os.environ["MONGO_URL"]
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ["DB_NAME"]]

JWT_SECRET = os.environ["JWT_SECRET"]
JWT_ALGORITHM = os.environ.get("JWT_ALGORITHM", "HS256")
TOKEN_MINUTES = int(os.environ.get("ACCESS_TOKEN_MINUTES", "10080"))

# --- Meta Lead Ads (Fase 2) --- secrets solo lato server ---
META_APP_ID = os.environ.get("META_APP_ID", "REPLACE_ME")
META_APP_SECRET = os.environ.get("META_APP_SECRET", "REPLACE_ME")
META_PAGE_ACCESS_TOKEN = os.environ.get("META_PAGE_ACCESS_TOKEN", "REPLACE_ME")
META_PAGE_ID = os.environ.get("META_PAGE_ID", "REPLACE_ME")
META_VERIFY_TOKEN = os.environ.get("META_VERIFY_TOKEN", "")
META_API_VERSION = os.environ.get("META_API_VERSION", "v21.0")
# Regola di importazione: SOLO i moduli Meta il cui nome inizia con questo prefisso.
SG_FORM_PREFIX = os.environ.get("META_FORM_PREFIX", "SG -")
# Prefisso SG- (accetta "SG-", "SG -", case-insensitive) per moduli, campagne e annunci.
SG_PREFIX_RE = re.compile(r"^\s*SG\s*-", re.IGNORECASE)


def sg_prefixed(name) -> bool:
    return bool(name and SG_PREFIX_RE.match(str(name)))
GRAPH = f"https://graph.facebook.com/{META_API_VERSION}"

# --- AI reale (Emergent universal key) ---
EMERGENT_LLM_KEY = os.environ.get("EMERGENT_LLM_KEY", "")
AI_MODEL = os.environ.get("AI_MODEL", "gpt-5.4")
AI_PROVIDER = os.environ.get("AI_PROVIDER", "openai")
BRAND_NAME = "J'adore Mimì"
ASSISTANT_NAME = "Andrea"

# --- Object Storage (immagini trattamenti) ---
STORAGE_BASE = (os.environ.get("INTEGRATION_PROXY_URL") or "").strip() or "https://integrations.emergentagent.com"
STORAGE_URL = STORAGE_BASE.rstrip("/") + "/objstore/api/v1/storage"
_storage_key = None


def meta_configured() -> bool:
    vals = [META_APP_ID, META_APP_SECRET, META_PAGE_ACCESS_TOKEN, META_PAGE_ID]
    return all(v and v != "REPLACE_ME" for v in vals)

app = FastAPI(title="SUPER GIRL API")
api = APIRouter(prefix="/api")
security = HTTPBearer(auto_error=True)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("supergirl")


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Costanti di dominio
# ---------------------------------------------------------------------------
PIPELINE_STAGES = [
    {"key": "nuovo_lead", "label": "NUOVO LEAD", "order": 1,
     "desc": "Lead appena arrivato da Meta."},
    {"key": "ai_conversazione", "label": "AI IN CONVERSAZIONE", "order": 2,
     "desc": "SUPER GIRL sta conversando con il cliente."},
    {"key": "in_attesa", "label": "IN ATTESA CLIENTE", "order": 3,
     "desc": "L'AI ha risposto e aspetta la risposta del cliente."},
    {"key": "interessata", "label": "INTERESSATA", "order": 4,
     "desc": "Il cliente mostra interesse concreto."},
    {"key": "attesa_chiamata", "label": "IN ATTESA DI CHIAMATA", "order": 5,
     "desc": "La cliente vuole prenotare: lo staff deve richiamarla per fissare."},
    {"key": "da_fissare", "label": "DA FISSARE APPUNTAMENTO", "order": 6,
     "desc": "Il cliente vuole prenotare e deve essere contattato dallo staff."},
    {"key": "appuntamento_fissato", "label": "APPUNTAMENTO FISSATO", "order": 7,
     "desc": "Lo staff ha fissato manualmente l'appuntamento."},
    {"key": "chiamata_corso_fissata", "label": "CHIAMATA CORSO FISSATA", "order": 8,
     "desc": "Chiamata per un corso fissata da Andrea (Academy Manager)."},
    {"key": "non_interessata", "label": "NON INTERESSATA", "order": 9,
     "desc": "Cliente che dichiara di non essere interessata."},
    {"key": "persa", "label": "PERSA / NON RISPONDE", "order": 10,
     "desc": "Cliente che non risponde dopo i follow-up previsti."},
]
STAGE_LABELS = {s["key"]: s["label"] for s in PIPELINE_STAGES}

TEMPERATURES = [
    {"key": "molto_calda", "label": "Molto Calda"},
    {"key": "interessata", "label": "Interessata"},
    {"key": "da_coltivare", "label": "Da Coltivare"},
    {"key": "non_qualificata", "label": "Non Qualificata"},
]

# --- Prenotazione chiamate CORSI (Modulo B) ---
# Finestra chiamate: Martedì(1)–Sabato(5) [lun=0], 09:00–18:00, slot da 30 min.
CALL_SLOT_MINUTES = 30
CALL_DAYS = {1, 2, 3, 4, 5}
CALL_START_HOUR = 9
CALL_END_HOUR = 18  # ultimo slot che inizia alle 17:30
CONFIRM_WORDS = [
    "sì", "si", "va bene", "ok", "okay", "perfetto", "confermo", "confermato",
    "d'accordo", "daccordo", "certo", "va benissimo", "per me va bene", "ci sono",
    "andata", "va bene così", "mi va bene", "🆗", "👍",
]

# --- Flusso TRATTAMENTI su WhatsApp (script approvato) ---
# Prezzi ufficiali: nome trattamento -> (label, prezzo pieno €, promo metà €)
TREATMENT_PRICES = {
    "model leg": ("Model Leg", 180, 90),
    "bomba": ("Bomba", 300, 150),
    "colombiano": ("Colombiano", 160, 80),
    "bambolina": ("Bambolina", 300, 150),
}
PRICE_WORDS = ["quanto costa", "prezzo", "costo", "quanto viene", "quanto mi viene",
               "quanto è", "tariffa", "quanto costerebbe", "costi"]
BOOKING_WORDS = ["fissare", "appuntamento", "prenotare", "prenotazione", "fissiamo",
                 "posso venire", "quando posso", "prenoto", "vorrei venire", "fisso"]
# Temi medici/delicati: SEMPRE passaggio alla chiamata (mai risposte mediche)
MEDICAL_WORDS = ["gravidanza", "incinta", "allattamento", "patologia", "malattia",
                 "controindicazioni", "controindicazione", "farmaci", "farmaco", "diabete",
                 "allergia", "allergica", "anestesia", "cicatrici", "cicatrice"]
CANT_TALK_WORDS = ["non posso parlare", "non posso ora", "sono al lavoro", "richiamami",
                   "richiamatemi", "più tardi", "sono occupata", "adesso no", "ora no",
                   "non ho tempo", "in un altro momento", "chiamami"]
INFO_PRECISA = ("Su questo preferisco darti un'informazione precisa. "
                "Ti richiamo a breve e ti spieghiamo tutto.")


# ---------------------------------------------------------------------------
# Auth models & helpers
# ---------------------------------------------------------------------------
class LoginInput(BaseModel):
    email: str
    password: str


def hash_password(pw: str) -> str:
    return bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()


def verify_password(pw: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(pw.encode(), hashed.encode())
    except Exception:
        return False


def create_token(user: dict) -> str:
    payload = {
        "sub": user["id"],
        "role": user["role"],
        "iat": now_utc(),
        "exp": now_utc() + timedelta(minutes=TOKEN_MINUTES),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def public_user(u: dict) -> dict:
    return {
        "id": u["id"], "email": u["email"], "name": u.get("name"),
        "role": u["role"], "avatar_color": u.get("avatar_color"),
    }


async def current_user(cred: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    unauthorized = HTTPException(status_code=401, detail="Credenziali non valide")
    try:
        payload = jwt.decode(cred.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.PyJWTError:
        raise unauthorized
    user = await db.users.find_one({"id": payload.get("sub")}, {"_id": 0})
    if not user:
        raise unauthorized
    return user


def require_admin(user: dict = Depends(current_user)) -> dict:
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Riservato agli Admin")
    return user


# ---------------------------------------------------------------------------
# Auth routes
# ---------------------------------------------------------------------------
@api.post("/auth/login")
async def login(body: LoginInput):
    user = await db.users.find_one({"email": body.email.strip().lower()})
    if not user or not verify_password(body.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Email o password non corretti")
    return {"access_token": create_token(user), "token_type": "bearer",
            "user": public_user(user)}


@api.get("/auth/me")
async def me(user: dict = Depends(current_user)):
    return public_user(user)


# ---------------------------------------------------------------------------
# AI simulata — motore conversazionale e handoff (Fase 1)
# ---------------------------------------------------------------------------
BOOKING_KEYWORDS = [
    "prenot", "appuntamento", "fissare", "fissiamo", "prendere un appuntamento",
    "quando posso venire", "quando posso passare", "disponibil", "prossima settimana",
    "questa settimana", "vorrei venire", "posso venire", "prenotare",
]
HUMAN_KEYWORDS = [
    "operatore", "parlare con una persona", "parlare con qualcuno", "un umano",
    "chiamatemi", "chiamami", "telefonatemi", "voglio parlare con",
]
ANGER_KEYWORDS = ["arrabbiat", "vergogna", "truffa", "denuncia", "pessim", "inaccettabile"]

# Domande di qualificazione (una alla volta, tono WhatsApp, breve)
AI_QUALIFY_STEPS = [
    "Perfetto! Per aiutarti al meglio, posso chiederti qual è l'obiettivo principale che vorresti raggiungere? 😊",
    "Capisco benissimo. C'è una zona in particolare su cui vorresti lavorare?",
    "Ottimo. Preferisci la nostra sede di Milano Centro o quella di Roma Prati?",
    "Grazie mille! Hai già avuto esperienze con trattamenti simili in passato?",
    "Perfetto, ti trovo davvero motivata! Ti piacerebbe ricevere maggiori dettagli o organizzare una prima visita conoscitiva?",
]


def detect_handoff(text: str):
    """Ritorna (motivo, messaggio_ai) se serve handoff, altrimenti (None, None)."""
    low = text.lower()
    if any(k in low for k in BOOKING_KEYWORDS):
        return ("prenotazione",
                "Va bene, allora controllo le disponibilità e ti richiamo "
                "io a breve per fissare insieme l'appuntamento nel giorno che "
                "preferisci.")
    if any(k in low for k in HUMAN_KEYWORDS):
        return ("richiesta_operatore",
                "Ok, passo subito la conversazione a una nostra collega che "
                "ti ricontatterà personalmente.")
    if any(k in low for k in ANGER_KEYWORDS):
        return ("situazione_delicata",
                "Mi dispiace molto. Faccio intervenire subito una nostra "
                "responsabile che si prenderà cura di te.")
    return (None, None)


def build_ai_summary(lead: dict, messages: List[dict], motivo: str) -> str:
    """Costruisce un riassunto strutturato per l'operatore."""
    cliente_msgs = [m["text"] for m in messages if m["sender"] == "cliente"]
    domande = [m for m in cliente_msgs if "?" in m]
    ultima = cliente_msgs[-1] if cliente_msgs else "—"
    motivo_label = {
        "prenotazione": "La cliente ha manifestato l'intenzione concreta di prenotare.",
        "richiesta_operatore": "La cliente ha chiesto esplicitamente di parlare con una persona.",
        "situazione_delicata": "Situazione delicata: meglio l'intervento umano.",
        "info_da_verificare": "L'AI non aveva un'informazione certa: richiamare la cliente con i dettagli richiesti.",
        "info_medica": "Domanda su tema medico/delicato: da gestire a voce con la cliente.",
        "manuale": "Presa in carico manualmente dallo staff.",
    }.get(motivo, "Passaggio allo staff.")
    temp_label = {t["key"]: t["label"] for t in TEMPERATURES}.get(
        lead.get("temperature"), "—")
    return (
        f"Nome cliente: {lead['nome']} {lead['cognome']}\n"
        f"Servizio richiesto: {lead.get('servizio', '—')}\n"
        f"Sede: {lead.get('sede', '—')}\n"
        f"Livello di interesse: {temp_label}\n"
        f"Esigenza principale: {lead.get('esigenza', 'Informazioni sul trattamento di interesse')}\n"
        f"Domande effettuate: {(' | '.join(domande) if domande else 'Nessuna domanda esplicita')}\n"
        f"Eventuali obiezioni: {lead.get('obiezioni', 'Nessuna rilevata')}\n"
        f"Ultima richiesta della cliente: {ultima}\n"
        f"Motivo del passaggio allo staff: {motivo_label}"
    )


async def cancel_followups(lead_id: str):
    await db.followups.update_many(
        {"lead_id": lead_id, "status": "programmato"},
        {"$set": {"status": "annullato", "updated_at": iso(now_utc())}},
    )


async def create_notification(tipo: str, lead: dict, extra: str = ""):
    notif = {
        "id": str(uuid.uuid4()),
        "tipo": tipo,  # cliente_da_fissare | ai_intervento | nuova_chat | nuovo_messaggio
        "lead_id": lead["id"],
        "lead_nome": f"{lead['nome']} {lead['cognome']}",
        "text": extra,
        "read": False,
        "created_at": iso(now_utc()),
    }
    await db.notifications.insert_one(notif)


# --- Push notifications (Emergent managed relay) ---
PUSH_BASE_URL = "https://integrations.emergentagent.com"
PUSH_KEY = os.environ.get("EMERGENT_PUSH_KEY", "placeholder")
_push_client = httpx.AsyncClient(
    base_url=PUSH_BASE_URL, headers={"X-Push-Key": PUSH_KEY}, timeout=10.0)


class RegisterPushBody(BaseModel):
    user_id: str
    platform: str
    device_token: str


@api.post("/register-push", status_code=201)
async def register_push(body: RegisterPushBody):
    resp = await _push_client.post("/api/v1/push/users/register", json=body.dict())
    if resp.status_code == 401:
        raise HTTPException(500, "EMERGENT_PUSH_KEY missing or invalid")
    if resp.status_code >= 500:
        raise HTTPException(502, "Push provider unavailable")
    resp.raise_for_status()
    return {"status": "registered"}


async def send_push(recipients: list, data: dict, idempotency_key: str = None) -> None:
    if not recipients:
        return
    if "title" not in data or "message" not in data:
        raise ValueError("data must include title and message")
    payload = {"recipients": recipients[:100], "data": data}
    if idempotency_key:
        payload["$idempotency_key"] = idempotency_key
    resp = await _push_client.post("/api/v1/push/trigger", json=payload)
    resp.raise_for_status()


async def notify_staff_push(title: str, message: str, action_url: str):
    """Invia una push a tutto lo staff (admin+operatori). Non bloccante."""
    try:
        staff = await db.users.find({}, {"_id": 0, "id": 1}).to_list(200)
        ids = [u["id"] for u in staff if u.get("id")]
        await send_push(ids, {"title": title, "message": message, "action_url": action_url})
    except Exception as e:
        logger.warning(f"Push failed (non-blocking): {e}")


async def record_status_change(lead: dict, from_status: str, to_status: str,
                               changed_by: str):
    await db.lead_status_history.insert_one({
        "id": str(uuid.uuid4()),
        "lead_id": lead["id"],
        "from_status": from_status,
        "to_status": to_status,
        "changed_by": changed_by,  # ai | staff
        "created_at": iso(now_utc()),
    })


async def do_handoff(lead: dict, conv: dict, motivo: str, ai_message: str):
    """Esegue l'handoff completo AI -> operatore in transazione logica."""
    msg = {
        "id": str(uuid.uuid4()),
        "conversation_id": conv["id"],
        "sender": "ai",
        "text": ai_message,
        "created_at": iso(now_utc()),
        "read": True,
    }
    await db.messages.insert_one(msg)

    from_status = lead["stato_pipeline"]
    new_status = "attesa_chiamata" if motivo in (
        "prenotazione", "info_da_verificare", "info_medica") else "da_fissare"
    await cancel_followups(lead["id"])
    summary = None
    # ricostruisci messaggi aggiornati per il riassunto
    all_msgs = await db.messages.find(
        {"conversation_id": conv["id"]}, {"_id": 0}).sort("created_at", 1).to_list(500)
    summary = build_ai_summary(lead, all_msgs, motivo)

    await db.leads.update_one({"id": lead["id"]}, {"$set": {
        "stato_pipeline": new_status,
        "ai_summary": summary,
        "handoff_at": iso(now_utc()),
        "ultimo_contatto": iso(now_utc()),
        "temperature": "molto_calda" if motivo == "prenotazione" else lead.get("temperature"),
    }})
    await db.conversations.update_one({"id": conv["id"]}, {"$set": {
        "ai_attiva": False,
        "stato": new_status,
        "last_message": ai_message,
        "last_message_at": iso(now_utc()),
    }})
    await record_status_change(lead, from_status, new_status, "ai")
    await db.ai_handoffs.insert_one({
        "id": str(uuid.uuid4()),
        "lead_id": lead["id"],
        "conversation_id": conv["id"],
        "motivo": motivo,
        "summary": summary,
        "gestito_da": None,
        "created_at": iso(now_utc()),
    })
    tipo = "cliente_da_fissare" if motivo == "prenotazione" else "ai_intervento"
    await create_notification(tipo, lead, ai_message)
    if motivo in ("prenotazione", "info_da_verificare", "info_medica"):
        nome = f"{lead['nome']} {lead['cognome']}".strip()
        extra = ""
        if lead.get("servizio"):
            extra += f" · {lead['servizio']}"
        if lead.get("sede"):
            extra += f" · {lead['sede']}"
        push_title = {
            "prenotazione": "Nuovo appuntamento da fissare 💎",
            "info_da_verificare": "Lead da richiamare",
            "info_medica": "Lead da richiamare (tema medico)",
        }[motivo]
        push_body = {
            "prenotazione": f"{nome} vuole fissare un appuntamento{extra}",
            "info_da_verificare": f"{nome} attende un richiamo con le info richieste{extra}",
            "info_medica": f"{nome} ha una domanda su un tema medico: richiamare a voce{extra}",
        }[motivo]
        await notify_staff_push(push_title, push_body, f"/conversation/{conv['id']}")
    clean_msg = {k: v for k, v in msg.items() if k != "_id"}
    return clean_msg, summary, new_status


# ---------------------------------------------------------------------------
# CHAT / Conversations
# ---------------------------------------------------------------------------
async def enrich_conversation(conv: dict) -> dict:
    lead = await db.leads.find_one({"id": conv["lead_id"]}, {"_id": 0})
    return {
        **conv,
        "lead_nome": f"{lead['nome']} {lead['cognome']}" if lead else "—",
        "temperature": lead.get("temperature") if lead else None,
        "servizio": lead.get("servizio") if lead else None,
        "sede": lead.get("sede") if lead else None,
        "foto_profilo": lead.get("foto_profilo") if lead else None,
        "ig_username": lead.get("ig_username") if lead else None,
        "piattaforma": lead.get("piattaforma") if lead else None,
    }


@api.get("/conversations")
async def list_conversations(filter: str = "tutte", user: dict = Depends(current_user)):
    query: dict = {}
    if filter == "ai":
        query["ai_attiva"] = True
    elif filter == "operatore":
        query["ai_attiva"] = False
    elif filter == "da_fissare":
        query["stato"] = {"$in": ["attesa_chiamata", "da_fissare"]}
    elif filter == "non_lette":
        query["unread"] = {"$gt": 0}
    convs = await db.conversations.find(query, {"_id": 0}).sort(
        "last_message_at", -1).to_list(500)
    return [await enrich_conversation(c) for c in convs]


@api.get("/conversations/{conv_id}")
async def get_conversation(conv_id: str, user: dict = Depends(current_user)):
    conv = await db.conversations.find_one({"id": conv_id}, {"_id": 0})
    if not conv:
        raise HTTPException(404, "Conversazione non trovata")
    lead = await db.leads.find_one({"id": conv["lead_id"]}, {"_id": 0})
    msgs = await db.messages.find(
        {"conversation_id": conv_id}, {"_id": 0}).sort("created_at", 1).to_list(500)
    # segna come letta
    await db.conversations.update_one({"id": conv_id}, {"$set": {"unread": 0}})
    return {"conversation": await enrich_conversation(conv), "lead": lead,
            "messages": msgs}


class MessageInput(BaseModel):
    text: str


@api.post("/conversations/{conv_id}/messages")
async def send_message(conv_id: str, body: MessageInput,
                       user: dict = Depends(current_user)):
    conv = await db.conversations.find_one({"id": conv_id}, {"_id": 0})
    if not conv:
        raise HTTPException(404, "Conversazione non trovata")
    msg = {
        "id": str(uuid.uuid4()),
        "conversation_id": conv_id,
        "sender": "operatore",
        "text": body.text.strip(),
        "created_at": iso(now_utc()),
        "read": True,
    }
    await db.messages.insert_one(msg)
    await db.conversations.update_one({"id": conv_id}, {"$set": {
        "last_message": body.text.strip(), "last_message_at": iso(now_utc()),
    }})
    await db.leads.update_one({"id": conv["lead_id"]},
                             {"$set": {"ultimo_contatto": iso(now_utc())}})
    return {k: v for k, v in msg.items() if k != "_id"}


@api.post("/conversations/{conv_id}/take")
async def take_conversation(conv_id: str, user: dict = Depends(current_user)):
    """PRENDI CONVERSAZIONE: AI OFF, presa in carico dallo staff."""
    conv = await db.conversations.find_one({"id": conv_id}, {"_id": 0})
    if not conv:
        raise HTTPException(404, "Conversazione non trovata")
    lead = await db.leads.find_one({"id": conv["lead_id"]}, {"_id": 0})
    await cancel_followups(conv["lead_id"])
    await db.conversations.update_one({"id": conv_id}, {"$set": {
        "ai_attiva": False, "operatore": user["name"],
    }})
    await db.leads.update_one({"id": conv["lead_id"]},
                             {"$set": {"operatore_assegnato": user["name"]}})
    return {"ok": True, "ai_attiva": False, "operatore": user["name"]}


@api.post("/conversations/{conv_id}/reactivate-ai")
async def reactivate_ai(conv_id: str, user: dict = Depends(current_user)):
    """RIATTIVA AI: AI ON."""
    conv = await db.conversations.find_one({"id": conv_id}, {"_id": 0})
    if not conv:
        raise HTTPException(404, "Conversazione non trovata")
    await db.conversations.update_one({"id": conv_id}, {"$set": {"ai_attiva": True}})
    return {"ok": True, "ai_attiva": True}


@api.post("/conversations/{conv_id}/simulate-customer")
async def simulate_customer(conv_id: str, body: MessageInput,
                            user: dict = Depends(current_user)):
    """Simula un messaggio in arrivo dal cliente (demo)."""
    conv = await db.conversations.find_one({"id": conv_id}, {"_id": 0})
    if not conv:
        raise HTTPException(404, "Conversazione non trovata")
    lead = await db.leads.find_one({"id": conv["lead_id"]}, {"_id": 0})
    msg = {
        "id": str(uuid.uuid4()),
        "conversation_id": conv_id,
        "sender": "cliente",
        "text": body.text.strip(),
        "created_at": iso(now_utc()),
        "read": True,
    }
    await db.messages.insert_one(msg)
    # il cliente ha risposto -> annulla i follow-up programmati
    await cancel_followups(conv["lead_id"])
    await db.conversations.update_one({"id": conv_id}, {"$set": {
        "last_message": body.text.strip(), "last_message_at": iso(now_utc()),
        "unread": conv.get("unread", 0) + 1,
    }})
    await db.leads.update_one({"id": conv["lead_id"]},
                             {"$set": {"ultimo_contatto": iso(now_utc())}})
    return {k: v for k, v in msg.items() if k != "_id"}


@api.post("/conversations/{conv_id}/simulate-ai-turn")
async def simulate_ai_turn(conv_id: str, user: dict = Depends(current_user)):
    """L'AI (simulata) elabora l'ultimo messaggio del cliente e risponde.
    Se rileva intenzione di prenotare o altri trigger -> handoff automatico."""
    conv = await db.conversations.find_one({"id": conv_id}, {"_id": 0})
    if not conv:
        raise HTTPException(404, "Conversazione non trovata")
    if not conv.get("ai_attiva", True):
        raise HTTPException(400, "L'AI è disattivata per questa conversazione")
    lead = await db.leads.find_one({"id": conv["lead_id"]}, {"_id": 0})
    msgs = await db.messages.find(
        {"conversation_id": conv_id}, {"_id": 0}).sort("created_at", 1).to_list(500)
    last_customer = next((m for m in reversed(msgs) if m["sender"] == "cliente"), None)

    is_corso = (lead.get("tipo") or "trattamento") == "corso"

    # CORSO: gestione prenotazione chiamata (proposta / conferma slot)
    if is_corso and last_customer:
        handled, corso_reply, booked = await handle_corso_turn(conv, lead, last_customer["text"])
        if handled:
            cmsg = {"id": str(uuid.uuid4()), "conversation_id": conv_id, "sender": "ai",
                    "text": corso_reply, "type": "text", "created_at": iso(now_utc()),
                    "read": True}
            await db.messages.insert_one(cmsg)
            await db.conversations.update_one({"id": conv_id}, {"$set": {
                "last_message": corso_reply, "last_message_at": iso(now_utc())}})
            if not booked:
                await db.conversations.update_one({"id": conv_id}, {"$set": {"stato": "in_attesa"}})
                await db.leads.update_one({"id": lead["id"]}, {"$set": {
                    "stato_pipeline": "in_attesa", "ultimo_contatto": iso(now_utc())}})
            return {"message": {k: v for k, v in cmsg.items() if k != "_id"},
                    "handoff": booked, "motivo": "chiamata_corso" if booked else None,
                    "new_status": "chiamata_corso_fissata" if booked else "in_attesa"}

    # TRATTAMENTO: flusso deterministico approvato (prezzo / prenotazione / richiamo)
    if (not is_corso) and last_customer:
        handled, tr_reply, keep_on, _btn = await handle_trattamento_turn(
            conv, lead, last_customer["text"])
        if handled:
            tmsg = {"id": str(uuid.uuid4()), "conversation_id": conv_id, "sender": "ai",
                    "text": tr_reply, "type": "text", "created_at": iso(now_utc()),
                    "read": True}
            await db.messages.insert_one(tmsg)
            await db.conversations.update_one({"id": conv_id}, {"$set": {
                "last_message": tr_reply, "last_message_at": iso(now_utc())}})
            fresh = await db.leads.find_one({"id": lead["id"]}, {"_id": 0})
            return {"message": {k: v for k, v in tmsg.items() if k != "_id"},
                    "handoff": (not keep_on),
                    "new_status": fresh.get("stato_pipeline")}

    # Altrimenti (CORSO senza preferenza): l'AI Academy genera la prossima risposta
    reply_text = await ai_generate_reply(conv, lead)
    # L'AI non inventa: se ha emesso un token di richiamo → handoff con frase naturale
    fb_motivo, fb_phrase = detect_ai_fallback(reply_text)
    if fb_motivo:
        reply, summary, new_status = await do_handoff(lead, conv, fb_motivo, fb_phrase)
        return {"message": reply, "handoff": True, "motivo": fb_motivo,
                "summary": summary, "new_status": new_status}
    msg = {
        "id": str(uuid.uuid4()),
        "conversation_id": conv_id,
        "sender": "ai",
        "text": reply_text,
        "type": "text",
        "created_at": iso(now_utc()),
        "read": True,
    }
    await db.messages.insert_one(msg)
    # aggiorna stato: AI in conversazione -> in attesa cliente + scalda il lead
    new_status = "in_attesa"
    ai_turns = len([m for m in msgs if m["sender"] == "ai"])
    new_temp = "interessata" if ai_turns >= 2 else lead.get("temperature")
    from_status = lead["stato_pipeline"]
    await db.conversations.update_one({"id": conv_id}, {"$set": {
        "last_message": reply_text, "last_message_at": iso(now_utc()),
        "stato": new_status,
    }})
    await db.leads.update_one({"id": lead["id"]}, {"$set": {
        "stato_pipeline": new_status, "temperature": new_temp,
        "ultimo_contatto": iso(now_utc()),
    }})
    if from_status != new_status:
        await record_status_change(lead, from_status, new_status, "ai")
    return {"message": {k: v for k, v in msg.items() if k != "_id"},
            "handoff": False, "new_status": new_status}


# ---------------------------------------------------------------------------
# LEADS / Clienti
# ---------------------------------------------------------------------------
@api.get("/leads")
async def list_leads(search: Optional[str] = None, stato: Optional[str] = None,
                     sede: Optional[str] = None, servizio: Optional[str] = None,
                     temperature: Optional[str] = None,
                     user: dict = Depends(current_user)):
    query: dict = {}
    if stato:
        query["stato_pipeline"] = stato
    if sede:
        query["sede"] = sede
    if servizio:
        query["servizio"] = servizio
    if temperature:
        query["temperature"] = temperature
    if search:
        s = search.strip()
        query["$or"] = [
            {"nome": {"$regex": s, "$options": "i"}},
            {"cognome": {"$regex": s, "$options": "i"}},
            {"telefono": {"$regex": s, "$options": "i"}},
        ]
    leads = await db.leads.find(query, {"_id": 0}).sort(
        "ultimo_contatto", -1).to_list(500)
    return leads


@api.get("/segments")
async def lead_segments(user: dict = Depends(current_user)):
    """Valori distinti + conteggi per segmentare le clienti."""
    leads = await db.leads.find({}, {"_id": 0}).to_list(2000)

    def counts(field: str):
        out: dict = {}
        for l in leads:
            v = l.get(field)
            if v:
                out[v] = out.get(v, 0) + 1
        return [{"value": k, "count": v} for k, v in
                sorted(out.items(), key=lambda x: -x[1])]

    return {
        "total": len(leads),
        "sede": counts("sede"),
        "servizio": counts("servizio"),
        "stato_pipeline": counts("stato_pipeline"),
        "temperature": counts("temperature"),
    }


@api.get("/leads/{lead_id}")
async def get_lead(lead_id: str, user: dict = Depends(current_user)):
    lead = await db.leads.find_one({"id": lead_id}, {"_id": 0})
    if not lead:
        raise HTTPException(404, "Cliente non trovato")
    conv = await db.conversations.find_one({"lead_id": lead_id}, {"_id": 0})
    history = await db.lead_status_history.find(
        {"lead_id": lead_id}, {"_id": 0}).sort("created_at", -1).to_list(100)
    return {"lead": lead, "conversation_id": conv["id"] if conv else None,
            "history": history}


class LeadUpdate(BaseModel):
    note_staff: Optional[str] = None
    temperature: Optional[str] = None
    operatore_assegnato: Optional[str] = None
    email: Optional[str] = None
    tipo: Optional[str] = None  # corso | trattamento


@api.patch("/leads/{lead_id}")
async def update_lead(lead_id: str, body: LeadUpdate,
                      user: dict = Depends(current_user)):
    lead = await db.leads.find_one({"id": lead_id}, {"_id": 0})
    if not lead:
        raise HTTPException(404, "Cliente non trovato")
    updates = {k: v for k, v in body.dict().items() if v is not None}
    if "tipo" in updates and updates["tipo"] not in ("corso", "trattamento"):
        raise HTTPException(400, "tipo non valido")
    if updates:
        await db.leads.update_one({"id": lead_id}, {"$set": updates})
    return await db.leads.find_one({"id": lead_id}, {"_id": 0})


class StatusChange(BaseModel):
    stato: str


@api.post("/leads/{lead_id}/status")
async def change_status(lead_id: str, body: StatusChange,
                        user: dict = Depends(current_user)):
    lead = await db.leads.find_one({"id": lead_id}, {"_id": 0})
    if not lead:
        raise HTTPException(404, "Cliente non trovato")
    if body.stato not in STAGE_LABELS:
        raise HTTPException(400, "Stato non valido")
    from_status = lead["stato_pipeline"]
    updates = {"stato_pipeline": body.stato}
    if body.stato in ("attesa_chiamata", "da_fissare"):
        updates["handoff_at"] = iso(now_utc())
    await db.leads.update_one({"id": lead_id}, {"$set": updates})
    await db.conversations.update_one({"lead_id": lead_id},
                                      {"$set": {"stato": body.stato}})
    if from_status != body.stato:
        await record_status_change(lead, from_status, body.stato, "staff")
        if body.stato in ("attesa_chiamata", "da_fissare"):
            lead2 = await db.leads.find_one({"id": lead_id}, {"_id": 0})
            await create_notification("cliente_da_fissare", lead2,
                                      "Spostata manualmente in Da Fissare.")
    return await db.leads.find_one({"id": lead_id}, {"_id": 0})


# ---------------------------------------------------------------------------
# PIPELINE
# ---------------------------------------------------------------------------
@api.get("/pipeline")
async def get_pipeline(user: dict = Depends(current_user)):
    leads = await db.leads.find({}, {"_id": 0}).to_list(500)
    result = []
    for stage in PIPELINE_STAGES:
        stage_leads = [l for l in leads if l["stato_pipeline"] == stage["key"]]
        stage_leads.sort(key=lambda x: x.get("ultimo_contatto", ""), reverse=True)
        result.append({**stage, "count": len(stage_leads), "leads": stage_leads})
    return result


# ---------------------------------------------------------------------------
# HOME — Priorità operative (DA FISSARE ADESSO)
# ---------------------------------------------------------------------------
TEMP_PRIORITY = {"molto_calda": 0, "interessata": 1, "da_coltivare": 2,
                 "non_qualificata": 3}


@api.get("/home/priorities")
async def home_priorities(user: dict = Depends(current_user)):
    leads = await db.leads.find(
        {"stato_pipeline": {"$in": ["attesa_chiamata", "da_fissare"]}}, {"_id": 0}).to_list(200)

    def sort_key(l):
        return (TEMP_PRIORITY.get(l.get("temperature"), 9),
                l.get("handoff_at", l.get("ultimo_contatto", "")))

    leads.sort(key=sort_key)
    out = []
    for l in leads:
        conv = await db.conversations.find_one({"lead_id": l["id"]}, {"_id": 0})
        wait_from = l.get("handoff_at") or l.get("ultimo_contatto")
        out.append({
            "id": l["id"], "nome": l["nome"], "cognome": l["cognome"],
            "telefono": l["telefono"], "servizio": l.get("servizio"),
            "sede": l.get("sede"), "temperature": l.get("temperature"),
            "waiting_since": wait_from,
            "foto_profilo": l.get("foto_profilo"),
            "ig_username": l.get("ig_username"),
            "piattaforma": l.get("piattaforma"),
            "campagna": l.get("campagna"),
            "orario_preferito_richiamo": l.get("orario_preferito_richiamo"),
            "conversation_id": conv["id"] if conv else None,
        })
    # Separazione contatti CORSO in base al tipo esplicito del lead (corso|trattamento)
    def is_corso(l):
        return (l.get("tipo") or "trattamento") == "corso"
    corso = [o for o, l in zip(out, leads) if is_corso(l)]
    trattamenti = [o for o, l in zip(out, leads) if not is_corso(l)]
    total = await db.leads.count_documents({})
    return {"da_fissare": trattamenti, "corso_da_chiamare": corso,
            "total_leads": total, "count": len(out)}


# ---------------------------------------------------------------------------
# ANALYTICS
# ---------------------------------------------------------------------------
@api.get("/analytics")
async def analytics(period: str = "30d", sede: Optional[str] = None,
                    servizio: Optional[str] = None, campagna: Optional[str] = None,
                    inserzione: Optional[str] = None, piattaforma: Optional[str] = None,
                    start: Optional[str] = None, end: Optional[str] = None,
                    user: dict = Depends(current_user)):
    now = now_utc()
    if period == "oggi":
        since = now.replace(hour=0, minute=0, second=0, microsecond=0)
        until = now
    elif period == "7d":
        since, until = now - timedelta(days=7), now
    elif period == "30d":
        since, until = now - timedelta(days=30), now
    elif period == "custom" and start and end:
        since = datetime.fromisoformat(start)
        until = datetime.fromisoformat(end)
    else:
        since, until = now - timedelta(days=30), now

    query: dict = {}
    if sede:
        query["sede"] = sede
    if servizio:
        query["servizio"] = servizio
    if campagna:
        query["campagna"] = campagna
    if inserzione:
        query["inserzione"] = inserzione
    if piattaforma:
        query["piattaforma"] = piattaforma
    leads = await db.leads.find(query, {"_id": 0}).to_list(1000)

    def in_period(l):
        try:
            d = datetime.fromisoformat(l["data_acquisizione"])
        except Exception:
            return True
        return since <= d <= until

    leads = [l for l in leads if in_period(l)]
    total = len(leads)

    def count(stat):
        return sum(1 for l in leads if l["stato_pipeline"] == stat)

    # conversazioni AI: lead che hanno almeno una conversazione con AI attiva o sono passati per AI
    conv_ids = [l["id"] for l in leads]
    ai_convs = await db.conversations.count_documents(
        {"lead_id": {"$in": conv_ids}}) if conv_ids else 0
    risposte = 0
    for l in leads:
        cnt = await db.messages.count_documents({
            "conversation_id": {"$in": [
                c["id"] for c in await db.conversations.find(
                    {"lead_id": l["id"]}, {"_id": 0, "id": 1}).to_list(5)]},
            "sender": "cliente",
        }) if True else 0
        if cnt > 0:
            risposte += 1

    interessate = count("interessata") + count("attesa_chiamata") + count("da_fissare") + count("appuntamento_fissato")
    da_fissare = count("attesa_chiamata") + count("da_fissare")
    appuntamenti = count("appuntamento_fissato")
    non_interessate = count("non_interessata")
    persi = count("persa")

    def pct(n):
        return round((n / total) * 100, 1) if total else 0.0

    # breakdown per campagna
    camp_map: dict = {}
    for l in leads:
        c = l.get("campagna", "—")
        camp_map.setdefault(c, {"campagna": c, "lead": 0, "da_fissare": 0,
                                "appuntamenti": 0})
        camp_map[c]["lead"] += 1
        if l["stato_pipeline"] in ("attesa_chiamata", "da_fissare"):
            camp_map[c]["da_fissare"] += 1
        if l["stato_pipeline"] == "appuntamento_fissato":
            camp_map[c]["appuntamenti"] += 1

    return {
        "period": period,
        "nuovi_lead": total,
        "conversazioni_ai": ai_convs,
        "risposte": risposte,
        "interessate": interessate,
        "da_fissare": da_fissare,
        "appuntamenti": appuntamenti,
        "non_interessate": non_interessate,
        "persi": persi,
        "pct_lead_interessata": pct(interessate),
        "pct_lead_appuntamento": pct(appuntamenti + da_fissare),
        "funnel": [
            {"label": "Lead", "value": total},
            {"label": "Conversazione", "value": risposte},
            {"label": "Interessata", "value": interessate},
            {"label": "Da fissare", "value": da_fissare + appuntamenti},
            {"label": "Appuntamento", "value": appuntamenti},
        ],
        "by_campaign": list(camp_map.values()),
    }


@api.get("/analytics/filters")
async def analytics_filters(user: dict = Depends(current_user)):
    sedi = await db.locations.distinct("nome")
    servizi = await db.services.distinct("nome")
    campagne = await db.campaigns.distinct("nome")
    inserzioni = await db.leads.distinct("inserzione")
    piattaforme = await db.leads.distinct("piattaforma")
    return {"sedi": sedi, "servizi": servizi, "campagne": campagne,
            "inserzioni": [i for i in inserzioni if i],
            "piattaforme": [p for p in piattaforme if p]}


# ---------------------------------------------------------------------------
# ALTRO — Servizi, Sedi, Campagne, Team, Knowledge Base, Follow-up, Impostazioni
# ---------------------------------------------------------------------------
class ServiceInput(BaseModel):
    nome: str
    descrizione: str = ""
    prezzo: str = ""
    promozione: str = ""
    info: str = ""
    faq: str = ""
    immagine: str = ""


@api.get("/services")
async def list_services(user: dict = Depends(current_user)):
    return await db.services.find({}, {"_id": 0}).to_list(200)


@api.post("/services")
async def create_service(body: ServiceInput, user: dict = Depends(require_admin)):
    doc = {"id": str(uuid.uuid4()), **body.dict()}
    await db.services.insert_one(doc)
    return {k: v for k, v in doc.items() if k != "_id"}


@api.patch("/services/{sid}")
async def update_service(sid: str, body: ServiceInput,
                         user: dict = Depends(require_admin)):
    await db.services.update_one({"id": sid}, {"$set": body.dict()})
    return await db.services.find_one({"id": sid}, {"_id": 0})


@api.delete("/services/{sid}")
async def delete_service(sid: str, user: dict = Depends(require_admin)):
    await db.services.delete_one({"id": sid})
    return {"ok": True}


class LocationInput(BaseModel):
    nome: str
    indirizzo: str = ""
    telefono: str = ""
    orari: str = ""
    info: str = ""


@api.get("/locations")
async def list_locations(user: dict = Depends(current_user)):
    return await db.locations.find({}, {"_id": 0}).to_list(200)


@api.post("/locations")
async def create_location(body: LocationInput, user: dict = Depends(require_admin)):
    doc = {"id": str(uuid.uuid4()), **body.dict()}
    await db.locations.insert_one(doc)
    return {k: v for k, v in doc.items() if k != "_id"}


@api.patch("/locations/{lid}")
async def update_location(lid: str, body: LocationInput,
                          user: dict = Depends(require_admin)):
    await db.locations.update_one({"id": lid}, {"$set": body.dict()})
    return await db.locations.find_one({"id": lid}, {"_id": 0})


@api.delete("/locations/{lid}")
async def delete_location(lid: str, user: dict = Depends(require_admin)):
    await db.locations.delete_one({"id": lid})
    return {"ok": True}


@api.get("/campaigns")
async def list_campaigns(user: dict = Depends(current_user)):
    camps = await db.campaigns.find({}, {"_id": 0}).to_list(200)
    for c in camps:
        c["lead_count"] = await db.leads.count_documents({"campagna": c["nome"]})
        c.setdefault("tipo", "trattamento")
    return camps


@api.get("/team")
async def list_team(user: dict = Depends(current_user)):
    users = await db.users.find({}, {"_id": 0, "password_hash": 0}).to_list(200)
    return users


class TeamInput(BaseModel):
    name: str
    email: str
    role: str = "operator"
    password: str = "Operatore123!"


@api.post("/team")
async def create_team(body: TeamInput, user: dict = Depends(require_admin)):
    exists = await db.users.find_one({"email": body.email.strip().lower()})
    if exists:
        raise HTTPException(400, "Email già registrata")
    doc = {
        "id": str(uuid.uuid4()),
        "name": body.name,
        "email": body.email.strip().lower(),
        "role": body.role,
        "password_hash": hash_password(body.password),
        "avatar_color": "#D4AF37" if body.role == "admin" else "#B68D40",
    }
    await db.users.insert_one(doc)
    return public_user(doc)


@api.get("/knowledge-base")
async def get_kb(user: dict = Depends(current_user)):
    kb = await db.knowledge_base.find_one({}, {"_id": 0})
    return kb or {}


class KBInput(BaseModel):
    azienda: Optional[str] = None
    servizi: Optional[str] = None
    prezzi: Optional[str] = None
    promozioni: Optional[str] = None
    sedi: Optional[str] = None
    orari: Optional[str] = None
    faq: Optional[str] = None
    obiezioni: Optional[str] = None
    pagamenti: Optional[str] = None
    tono_di_voce: Optional[str] = None
    info_commerciali: Optional[str] = None
    istruzioni: Optional[str] = None
    non_comunicare: Optional[str] = None


@api.patch("/knowledge-base")
async def update_kb(body: KBInput, user: dict = Depends(require_admin)):
    updates = {k: v for k, v in body.dict().items() if v is not None}
    await db.knowledge_base.update_one({}, {"$set": updates}, upsert=True)
    return await db.knowledge_base.find_one({}, {"_id": 0})


@api.get("/followups")
async def get_followup_rules(user: dict = Depends(current_user)):
    return await get_followup_rules_doc()


class FollowupRules(BaseModel):
    enabled: bool = True
    quiet_start: Optional[int] = None
    quiet_end: Optional[int] = None
    steps: list = []
    message_options: Optional[list] = None


@api.patch("/followups")
async def update_followup_rules(body: FollowupRules,
                                user: dict = Depends(require_admin)):
    updates = {k: v for k, v in body.dict().items() if v is not None}
    await db.followup_rules.update_one({}, {"$set": updates}, upsert=True)
    return await get_followup_rules_doc()


@api.get("/settings")
async def get_settings(user: dict = Depends(current_user)):
    s = await db.settings.find_one({}, {"_id": 0})
    return s or {}


@api.patch("/settings")
async def update_settings(body: dict, user: dict = Depends(require_admin)):
    await db.settings.update_one({}, {"$set": body}, upsert=True)
    return await db.settings.find_one({}, {"_id": 0})


@api.get("/integrations")
async def get_integrations(user: dict = Depends(current_user)):
    meta_status = "configurato" if meta_configured() else "non_attivo"
    wa_cfg = await get_wa_config()
    wa_ok = wa_is_configured(wa_cfg)
    return {
        "meta": {"name": "Meta Lead Ads", "status": meta_status, "phase": "Fase 2",
                 "configured": meta_configured()},
        "whatsapp": {"name": "WhatsApp Business Cloud API",
                     "status": "configurato" if wa_ok else "non_attivo",
                     "phase": "Fase 3", "configured": wa_ok},
        "ai": {"name": "AI Provider (GPT-5.4)", "status": "configurato",
               "phase": "Fase 4", "configured": True},
    }


# ---------------------------------------------------------------------------
# META LEAD ADS (Fase 2) — ingestione lead + webhook + simulatore
# ---------------------------------------------------------------------------
async def ensure_campaign(nome: Optional[str], inserzione: Optional[str],
                          servizio: Optional[str]):
    if not nome:
        return
    camp = await db.campaigns.find_one({"nome": nome})
    if not camp:
        await db.campaigns.insert_one({
            "id": str(uuid.uuid4()), "nome": nome,
            "inserzioni": [inserzione] if inserzione else [],
            "servizio": servizio or "",
        })
    elif inserzione and inserzione not in (camp.get("inserzioni") or []):
        await db.campaigns.update_one({"id": camp["id"]},
                                      {"$push": {"inserzioni": inserzione}})


async def ingest_meta_lead(data: dict) -> dict:
    """Flusso Fase 2: creazione lead -> associazione campagna/inserzione ->
    creazione conversazione -> avvio workflow WhatsApp (messaggio iniziale
    simulato, WhatsApp reale in Fase 3) -> notifica staff.
    Idempotente su leadgen_id se presente."""
    leadgen_id = data.get("leadgen_id")
    if leadgen_id:
        existing = await db.leads.find_one({"leadgen_id": leadgen_id}, {"_id": 0})
        if existing:
            conv = await db.conversations.find_one({"lead_id": existing["id"]}, {"_id": 0})
            return {"lead": existing, "conversation_id": conv["id"] if conv else None,
                    "duplicate": True}

    lid = str(uuid.uuid4())
    cid = str(uuid.uuid4())
    now = iso(now_utc())
    nome = (data.get("nome") or "Lead").strip()
    cognome = (data.get("cognome") or "").strip()
    campagna = data.get("campagna")
    inserzione = data.get("inserzione")
    servizio = data.get("servizio")

    await ensure_campaign(campagna, inserzione, servizio)
    camp_doc = await db.campaigns.find_one({"nome": campagna}, {"_id": 0}) if campagna else None
    tipo = (camp_doc or {}).get("tipo") or "trattamento"

    lead = {
        "id": lid, "nome": nome, "cognome": cognome,
        "telefono": data.get("telefono", ""), "email": data.get("email", ""),
        "servizio": servizio or "", "sede": data.get("sede", ""),
        "campagna": campagna or "", "inserzione": inserzione or "",
        "piattaforma": data.get("piattaforma") or "Instagram",
        "ig_username": data.get("ig_username"),
        "ig_display_name": data.get("ig_display_name"),
        "foto_profilo": data.get("foto_profilo"),
        "data_acquisizione": now, "ultimo_contatto": now,
        "stato_pipeline": "nuovo_lead", "temperature": "da_coltivare",
        "operatore_assegnato": None, "esigenza": "", "obiezioni": "",
        "note_staff": "", "ai_summary": None, "handoff_at": None,
        "leadgen_id": leadgen_id, "origine": "meta", "tipo": tipo,
        "form_id": data.get("form_id"), "form_name": data.get("form_name"),
    }
    await db.leads.insert_one(lead)

    svc_doc = await db.services.find_one({"nome": servizio}, {"_id": 0}) if servizio else None
    image_rel = (svc_doc or {}).get("immagine")

    if tipo == "corso":
        greeting = (
            f"Ciao {nome}, sono {ASSISTANT_NAME}, l'Academy Manager di {BRAND_NAME}.\n"
            f"Ho visto che ti interessa il nostro corso {servizio or ''}. "
            f"Posso farti due domande veloci per capire come aiutarti al meglio?"
        )
        image_rel = None  # per i corsi niente foto trattamento
    else:
        greeting = (
            f"Ciao {nome}, sono {ASSISTANT_NAME} di {BRAND_NAME} 😊\n"
            f"Ho visto che ti interessa il trattamento {servizio or 'estetico'}. "
            f"Dimmi, qual è la cosa che vorresti migliorare? Così ti spiego come "
            f"possiamo aiutarti."
        )
    await db.conversations.insert_one({
        "id": cid, "lead_id": lid, "ai_attiva": True, "stato": "nuovo_lead",
        "unread": 0, "operatore": None, "last_message": greeting,
        "last_message_at": now,
    })
    # Foto prima/dopo del trattamento (solo all'inizio)
    if image_rel:
        await db.messages.insert_one({
            "id": str(uuid.uuid4()), "conversation_id": cid, "sender": "ai",
            "text": f"Trattamento {servizio}", "type": "image", "media_url": image_rel,
            "created_at": now, "read": True,
        })
    await db.messages.insert_one({
        "id": str(uuid.uuid4()), "conversation_id": cid, "sender": "ai",
        "text": greeting, "type": "text", "created_at": now, "read": True,
    })
    # Invio WhatsApp reale (se configurato): template con immagine
    try:
        await whatsapp_send_template(lead.get("telefono", ""), nome,
                                     servizio or "trattamento", image_rel)
    except Exception as e:  # noqa
        logger.error(f"WA send on ingest failed: {e}")
    await db.lead_status_history.insert_one({
        "id": str(uuid.uuid4()), "lead_id": lid, "from_status": None,
        "to_status": "nuovo_lead", "changed_by": "meta", "created_at": now,
    })
    await schedule_followups(lead)
    await create_notification("nuova_chat", lead,
                              f"Nuovo lead da Meta ({campagna or 'campagna'})")
    lead_clean = await db.leads.find_one({"id": lid}, {"_id": 0})
    return {"lead": lead_clean, "conversation_id": cid, "duplicate": False}


async def graph_get(node: str, fields: str) -> dict:
    async with httpx.AsyncClient(timeout=15) as c:
        r = await c.get(f"{GRAPH}/{node}",
                        params={"fields": fields, "access_token": META_PAGE_ACCESS_TOKEN})
    if r.is_error:
        raise RuntimeError(f"Graph error {r.status_code}: {r.text}")
    return r.json()


def _field_map(field_data: list) -> dict:
    return {x["name"]: (x.get("values") or [None])[0]
            for x in field_data if x.get("name")}


async def get_form_name(form_id: str, lead_obj: dict) -> Optional[str]:
    """Nome del modulo Meta: dal nodo lead (form{name}) o, in fallback, dal form_id."""
    name = ((lead_obj.get("form") or {}) or {}).get("name")
    if name:
        return name
    if form_id:
        try:
            return (await graph_get(form_id, "id,name")).get("name")
        except Exception:  # noqa
            return None
    return None


def form_name_allowed(name: Optional[str]) -> bool:
    """Regola: importa SOLO i moduli il cui nome inizia con 'SG -' (o 'SG-').
    Fail-closed: se il nome non è disponibile, NON importare (protegge i moduli dell'agenzia)."""
    return sg_prefixed(name)


async def retrieve_and_ingest(leadgen_id: str, event: dict):
    """Recupera i dati completi del lead da Graph API e li ingesta.
    Applica la regola SG_FORM_PREFIX: solo i moduli il cui nome inizia con 'SG -'."""
    lead = await graph_get(
        leadgen_id,
        "id,created_time,form_id,ad_id,adset_id,campaign_id,field_data,form{id,name,status}")
    form_id = ((lead.get("form") or {}) or {}).get("id") or lead.get("form_id") or event.get("form_id")
    form_name = await get_form_name(form_id, lead)
    # >>> REGOLA SOLO-BACKEND: ignora tutto ciò che non inizia con 'SG -' <<<
    if not form_name_allowed(form_name):
        logger.info(
            f"Meta lead IGNORATO: modulo '{form_name}' (form_id={form_id}) non inizia con "
            f"'{SG_FORM_PREFIX}'. Nessun lead importato in Super Girl.")
        return {"skipped": True, "reason": "form_prefix", "form_name": form_name,
                "form_id": form_id}
    values = _field_map(lead.get("field_data", []))
    full = values.get("full_name") or ""
    parts = full.split(" ", 1)
    nome, cognome = (parts[0], parts[1] if len(parts) > 1 else "")
    campagna, inserzione, platform = None, None, "Facebook"
    ad_id = lead.get("ad_id") or event.get("ad_id")
    if ad_id:
        try:
            ad = await graph_get(ad_id, "id,name,campaign{id,name},creative{id,name,instagram_actor_id}")
            campagna = (ad.get("campaign") or {}).get("name")
            inserzione = ad.get("name")
            if (ad.get("creative") or {}).get("instagram_actor_id"):
                platform = "Instagram"
        except RuntimeError:
            pass
    return await ingest_meta_lead({
        "leadgen_id": lead.get("id", leadgen_id),
        "form_id": form_id, "form_name": form_name,
        "nome": nome, "cognome": cognome,
        "telefono": values.get("phone_number") or values.get("phone"),
        "email": values.get("email"),
        "campagna": campagna, "inserzione": inserzione, "piattaforma": platform,
    })


@api.get("/integrations/meta/webhook", response_class=PlainTextResponse)
async def meta_verify(request: Request):
    params = request.query_params
    mode = params.get("hub.mode")
    token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge")
    if mode == "subscribe" and META_VERIFY_TOKEN and hmac.compare_digest(
            token or "", META_VERIFY_TOKEN):
        return challenge or ""
    raise HTTPException(status_code=403, detail="Verifica webhook fallita")


@api.post("/integrations/meta/webhook")
async def meta_webhook(request: Request):
    raw = await request.body()
    sig = request.headers.get("x-hub-signature-256")
    if META_APP_SECRET and META_APP_SECRET != "REPLACE_ME":
        expected = "sha256=" + hmac.new(
            META_APP_SECRET.encode(), raw, hashlib.sha256).hexdigest()
        if not sig or not hmac.compare_digest(expected, sig):
            raise HTTPException(status_code=403, detail="Firma non valida")
    payload = await request.json()
    if payload.get("object") != "page":
        return {"ok": True}
    filter_mode = await get_meta_filter_mode()
    enabled_forms = await meta_enabled_form_ids() if filter_mode == "whitelist" else None
    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            if change.get("field") != "leadgen":
                continue
            value = change.get("value", {})
            leadgen_id = value.get("leadgen_id")
            form_id = value.get("form_id")
            # Auto-scoperta: registra il modulo così l'admin può attivarlo dall'app
            if form_id:
                await db.meta_forms.update_one(
                    {"form_id": form_id},
                    {"$setOnInsert": {"form_id": form_id, "enabled": False, "name": None},
                     "$set": {"last_seen": iso(now_utc())}}, upsert=True)
            # Filtro per modulo: in modalità whitelist acquisisce SOLO i moduli attivati
            if filter_mode == "whitelist" and (not form_id or form_id not in enabled_forms):
                logger.info(f"Meta lead ignorato (modulo {form_id} non attivo in Super Girl)")
                continue
            if leadgen_id and meta_configured():
                try:
                    await retrieve_and_ingest(leadgen_id, value)
                except Exception as e:  # noqa
                    logger.error(f"Meta ingest error: {e}")
    return {"ok": True}


@api.get("/integrations/meta/status")
async def meta_status(user: dict = Depends(current_user)):
    return {
        "configured": meta_configured(),
        "app_id_set": META_APP_ID != "REPLACE_ME",
        "app_secret_set": META_APP_SECRET != "REPLACE_ME",
        "page_token_set": META_PAGE_ACCESS_TOKEN != "REPLACE_ME",
        "page_id_set": META_PAGE_ID != "REPLACE_ME",
        # verify token mostrato solo all'admin per la configurazione su Meta
        "verify_token": META_VERIFY_TOKEN if user["role"] == "admin" else None,
        "webhook_path": "/api/integrations/meta/webhook",
        "subscribe_field": "leadgen",
        "api_version": META_API_VERSION,
        "filter_mode": await get_meta_filter_mode(),
        "enabled_forms": await db.meta_forms.count_documents({"enabled": True}),
    }


# --- Filtro moduli (form_id): whitelist gestibile dall'app --------------------
async def get_meta_filter_mode() -> str:
    """'all' = acquisisci tutti i moduli; 'whitelist' = solo i moduli attivati."""
    doc = await db.meta_settings.find_one({"id": "meta"}, {"_id": 0})
    return (doc or {}).get("filter_mode", "all")


async def meta_enabled_form_ids() -> set:
    docs = await db.meta_forms.find({"enabled": True}, {"_id": 0, "form_id": 1}).to_list(500)
    return {d["form_id"] for d in docs}


class FilterModeInput(BaseModel):
    mode: str  # "all" | "whitelist"


class FormToggle(BaseModel):
    enabled: bool
    name: Optional[str] = None


@api.get("/integrations/meta/forms")
async def list_meta_forms(user: dict = Depends(require_admin)):
    """Elenca i moduli lead della Pagina (Graph API) con lo stato di attivazione."""
    mode = await get_meta_filter_mode()
    if not meta_configured():
        return {"configured": False, "filter_mode": mode, "forms": [],
                "error": "Integrazione Meta non ancora configurata."}
    try:
        data = await graph_get(
            META_PAGE_ID,
            "leadgen_forms.limit(200){id,name,status,locale,leads_count}")
        raw = (data.get("leadgen_forms") or {}).get("data", [])
    except Exception as e:  # noqa
        saved = await db.meta_forms.find({}, {"_id": 0}).to_list(500)
        return {"configured": True, "filter_mode": mode, "forms": saved,
                "error": str(e)[:200]}
    saved = {d["form_id"]: d for d in
             await db.meta_forms.find({}, {"_id": 0}).to_list(500)}
    out = []
    for f in raw:
        fid = f.get("id")
        enabled = bool(saved.get(fid, {}).get("enabled", False))
        await db.meta_forms.update_one(
            {"form_id": fid},
            {"$set": {"form_id": fid, "name": f.get("name"),
                      "status": f.get("status"), "leads_count": f.get("leads_count")},
             "$setOnInsert": {"enabled": False}}, upsert=True)
        out.append({"form_id": fid, "name": f.get("name"),
                    "status": f.get("status"), "leads_count": f.get("leads_count"),
                    "enabled": enabled})
    return {"configured": True, "filter_mode": mode, "forms": out, "error": None}


@api.post("/integrations/meta/forms/{form_id}")
async def toggle_meta_form(form_id: str, body: FormToggle,
                           user: dict = Depends(require_admin)):
    await db.meta_forms.update_one(
        {"form_id": form_id},
        {"$set": {"form_id": form_id, "enabled": body.enabled,
                  **({"name": body.name} if body.name else {})}}, upsert=True)
    return {"ok": True, "form_id": form_id, "enabled": body.enabled}


@api.post("/integrations/meta/filter-mode")
async def set_meta_filter_mode(body: FilterModeInput,
                               user: dict = Depends(require_admin)):
    mode = body.mode if body.mode in ("all", "whitelist") else "all"
    await db.meta_settings.update_one({"id": "meta"},
                                      {"$set": {"id": "meta", "filter_mode": mode}},
                                      upsert=True)
    return {"ok": True, "filter_mode": mode}


class SimLeadInput(BaseModel):
    nome: str
    cognome: str = ""
    telefono: str = ""
    email: str = ""
    servizio: str = ""
    sede: str = ""
    campagna: str = ""
    inserzione: str = ""
    piattaforma: str = "Instagram"
    ig_username: Optional[str] = None
    ig_display_name: Optional[str] = None
    foto_profilo: Optional[str] = None
    leadgen_id: Optional[str] = None


@api.post("/integrations/meta/simulate")
async def meta_simulate(body: SimLeadInput, user: dict = Depends(require_admin)):
    """Simula la ricezione di un lead da Meta (test Fase 2, senza API reali)."""
    res = await ingest_meta_lead(body.dict())
    return res


# ---------------------------------------------------------------------------
# AI REALE (GPT-5.4 via Emergent) — assistente commerciale J'adore Mimì
# ---------------------------------------------------------------------------
async def get_corso_config() -> dict:
    return await db.integration_config.find_one({"key": "corsi"}, {"_id": 0}) or {}


async def build_corso_system_prompt(lead: dict) -> str:
    """Prompt Academy Manager per i lead di tipo CORSO."""
    kb = await db.knowledge_base.find_one({}, {"_id": 0}) or {}
    corso = await get_corso_config()
    prezzi = (corso.get("prezzi") or "").strip()
    corso_nome = lead.get("servizio") or "corso"
    prezzi_rule = (
        f"PREZZI CORSI (uso interno): {prezzi}\n"
        f"REGOLA PREZZI: NON comunicare MAI i prezzi nel primo messaggio e non anticiparli tu. "
        f"Se la cliente li chiede esplicitamente puoi indicarli con i valori ESATTI qui sopra "
        f"(mai inventare), ma riporta sempre il discorso al fissare la chiamata per spiegarle tutto "
        f"con calma. Se non hai i prezzi nel sistema, di' che li vede insieme in chiamata.\n"
        if prezzi else
        f"PREZZI CORSI: non hai prezzi nel sistema. NON inventare cifre: di' che vedete tutto "
        f"insieme in chiamata.\n")
    return (
        f"Sei {ASSISTANT_NAME}, l'Academy Manager di {BRAND_NAME}. Ti occupi dei CORSI di formazione "
        f"(academy). Parli in italiano, tono caldo, professionale e concreto, stile WhatsApp: messaggi "
        f"BREVI e naturali, una domanda alla volta. Non rivelare mai di essere un assistente automatico.\n\n"
        f"OBIETTIVO: qualificare la persona interessata al corso e PORTARLA A FISSARE UNA CHIAMATA "
        f"conoscitiva con l'academy. NON vendi il corso in chat: spieghi l'essenziale e proponi la chiamata.\n"
        f"QUALIFICA (in modo naturale, non come questionario): capisci se è del settore/estetista o "
        f"principiante, cosa la interessa del corso ({corso_nome}), la sua città/zona.\n"
        f"FISSARE LA CHIAMATA: NON mostrare MAI slot o orari prefissati e NON far credere di avere "
        f"un'agenda con orari liberi. Chiedi tu alla persona QUANDO preferisce essere richiamata "
        f"(giorno e fascia oraria). Le chiamate sono possibili da martedì a sabato, dalle 9 alle 18. "
        f"Quando ti dà una preferenza, il sistema fisserà lo slot: tu limitati a chiedere la preferenza "
        f"e a confermare con entusiasmo. Non proporre orari specifici di tua iniziativa.\n"
        f"REGOLA ANTI-INVENZIONE: usa SOLO le informazioni della KNOWLEDGE BASE qui sotto. Se non sai "
        f"qualcosa rispondi SOLO con il token [[RICHIAMO]]; se è un tema medico/delicato usa SOLO "
        f"[[RICHIAMO_MEDICO]].\n"
        f"REGOLA EMOJI: vietato qualsiasi cuore; altre emoji solo di rado.\n"
        f"{prezzi_rule}\n"
        f"CONTESTO LEAD: nome={lead.get('nome')}, corso d'interesse={corso_nome}, "
        f"sede/zona={lead.get('sede') or 'NON INDICATA'}, campagna={lead.get('campagna')}.\n\n"
        f"KNOWLEDGE BASE:\nAzienda: {kb.get('azienda','')}\nCorsi/Servizi: {kb.get('servizi','')}\n"
        f"Sedi: {kb.get('sedi','')}\nFAQ: {kb.get('faq','')}\nObiezioni: {kb.get('obiezioni','')}\n"
    )


async def build_ai_system_prompt(lead: dict) -> str:
    if (lead.get("tipo") or "trattamento") == "corso":
        return await build_corso_system_prompt(lead)
    kb = await db.knowledge_base.find_one({}, {"_id": 0}) or {}
    servizio = lead.get("servizio") or "trattamento estetico"
    svc = await db.services.find_one({"nome": servizio}, {"_id": 0}) or {}
    try:
        base = lead.get("data_acquisizione")
        start = datetime.fromisoformat(base) if base else now_utc()
    except Exception:
        start = now_utc()
    promo_days = int((kb or {}).get("promo_giorni", 10) or 10)
    promo_end = (start + timedelta(days=promo_days)).astimezone(ROME_TZ).strftime("%d/%m/%Y")
    has_price = bool((svc.get("prezzo") or "").strip())
    has_promo = bool((svc.get("promozione") or "").strip())
    if not has_price:
        prezzo_rule = (
            f"PREZZO NON DISPONIBILE: per il trattamento '{servizio}' NON hai prezzi nel sistema. "
            f"NON inventare MAI cifre: se la cliente chiede il prezzo, di' con naturalezza che verifichi "
            f"il dettaglio aggiornato e che lo staff la ricontatta con tutte le info.\n")
    elif has_promo:
        prezzo_rule = (
            f"STRATEGIA PREZZO: quando la cliente chiede il prezzo, indica il listino e la promozione con "
            f"i valori ESATTI dei DETTAGLI TRATTAMENTO qui sotto, e OGNI VOLTA che citi una promozione DEVI "
            f"aggiungere la scadenza: 'valida fino al {promo_end}, fino a esaurimento posti'. "
            f"NON usare prezzi/promo di memoria: la fonte è solo i DETTAGLI TRATTAMENTO / KNOWLEDGE BASE.\n")
    else:
        prezzo_rule = (
            f"STRATEGIA PREZZO: indica il prezzo con i valori ESATTI dei DETTAGLI TRATTAMENTO qui sotto. "
            f"NON usare prezzi di memoria e NON inventare promozioni inesistenti.\n")
    return (
        f"Sei {ASSISTANT_NAME}, assistente commerciale del centro estetico {BRAND_NAME}. "
        f"Parli in italiano, con tono caldo, femminile, empatico e professionale, in stile WhatsApp: "
        f"messaggi BREVI, naturali, mai muri di testo, una domanda alla volta.\n\n"
        f"OBIETTIVO PRINCIPALE: portare gentilmente la cliente fino all'INTERESSE concreto a prenotare. "
        f"NON sei un questionario: conversi in modo umano, vendita conversazionale non aggressiva. "
        f"Capisci il bisogno, rispondi alle domande, gestisci dubbi/obiezioni, valorizzi i benefici.\n"
        f"IMPORTANTISSIMO — GESTIONE APPUNTAMENTO: NON chiedere MAI il giorno, NON proporre date o orari, "
        f"NON far credere di avere un'agenda. Quando la cliente vuole procedere/prenotare, chiudi la parte "
        f"automatica con una frase naturale tipo: 'Controllo le disponibilità e ti richiamo per fissare "
        f"l'appuntamento.' Poi fermati (allo staff il resto).\n"
        f"STILE NATURALE (fondamentale — devi sembrare una persona vera, un'estetista/consulente donna "
        f"che lavora da anni con clienti e ha confidenza nel consigliare): tono caldo, confidenziale e "
        f"professionale ma MAI formale, freddo, perfettino o robotico.\n"
        f"REGOLA EMOJI: VIETATO usare qualsiasi cuore (❤️ 💕 💛 🩷 💗 💖 ecc.), MAI, in nessun messaggio. "
        f"Altre emoji (es. 😊) solo di rado, una ogni tanto e solo quando risulta naturale — NON in ogni "
        f"messaggio, mai sequenze o doppie emoji.\n"
        f"APERTURE VARIE: è VIETATO iniziare in modo automatico con 'Certo', 'Certamente', 'Perfetto', "
        f"'Assolutamente'. Puoi usarle RARAMENTE ma non come formula fissa. Varia molto l'inizio: a volte "
        f"rispondi DIRETTAMENTE senza formula; altre volte usa aperture naturali come 'Ok', 'Sì, guarda…', "
        f"'Allora…', 'Ti spiego', 'Guarda…', 'Sì, questo è proprio uno dei trattamenti più richiesti', "
        f"'Ti dico subito come funziona', 'Capito', 'Guarda, in questo caso farei così…'.\n"
        f"CONFIDENZA: ogni tanto (non sempre) puoi usare parole come 'guarda', 'ti spiego', 'secondo me', "
        f"'in questo caso', e occasionalmente 'tesoro' o 'cara' — ma ALTERNATE, non in ogni messaggio. "
        f"IMPORTANTE: NON chiamare 'tesoro'/'cara' una cliente al primo messaggio; diventa più confidenziale "
        f"solo col proseguire della conversazione, quando il tono lo permette, così resti spontanea e non costruita.\n"
        f"ANTI-SCHEMA: NON seguire mai sempre lo stesso schema (es. 'Apertura! + spiegazione + domanda finale' "
        f"oppure 'Perfetto! + spiegazione + emoji'). Varia l'apertura, la lunghezza delle frasi, il modo di "
        f"spiegare, il modo di fare domande (a volte non fare domande), l'eventuale uso di emoji e il modo di "
        f"concludere. Guarda i messaggi precedenti: se hai già spiegato una cosa NON ripeterla quasi identica "
        f"poco dopo.\n"
        f"LUNGHEZZA: su WhatsApp preferisci messaggi brevi e naturali. Se la cliente fa una domanda semplice, "
        f"rispondi in modo semplice e breve. Usa risposte più lunghe SOLO quando devi davvero spiegare un "
        f"trattamento, una promozione o qualcosa di importante.\n"
        f"ESEMPIO DI TONO (due modi diversi di rispondere alla stessa domanda 'funziona sulla cellulite?', "
        f"NON copiarli alla lettera, servono solo a farti capire lo stile): "
        f"1) 'Sì, guarda, è proprio uno dei motivi per cui lo facciamo tanto. Lavora bene sulla cellulite e "
        f"sulla compattezza della pelle. Poi dipende da come parti tu, perché ogni corpo risponde diversamente.' "
        f"2) 'Sì 😊 soprattutto se il problema è cellulite e pelle poco compatta. In quel caso è uno dei "
        f"trattamenti che valuterei.'\n"
        f"Non rivelare mai di essere un assistente automatico o un'AI.\n"
        f"{prezzo_rule}"
        f"Quando indichi un prezzo, prima capisci l'obiettivo della cliente, poi proponi la soluzione.\n\n"
        f"REGOLA ANTI-INVENZIONE (FONDAMENTALE E NON NEGOZIABILE): puoi usare SOLO le informazioni presenti "
        f"nei DETTAGLI TRATTAMENTO e nella KNOWLEDGE BASE qui sotto. NON inventare MAI prezzi, promozioni, "
        f"risultati, tempi, numero di sedute, dettagli tecnici o qualsiasi dato non scritto qui. Se la cliente "
        f"chiede qualcosa che NON trovi in queste informazioni, oppure la domanda è troppo specifica per "
        f"rispondere con certezza, NON tirare a indovinare e NON dare risposte generiche: rispondi ESATTAMENTE "
        f"e SOLO con il token [[RICHIAMO]] (esattamente così, senza aggiungere altro testo, né saluti né emoji). "
        f"Il sistema lo sostituirà con la frase giusta e farà richiamare la cliente dallo staff.\n"
        f"REGOLA TEMI MEDICI/DELICATI (NON NEGOZIABILE): se la cliente chiede di controindicazioni, "
        f"gravidanza o allattamento, patologie, farmaci, interventi, condizioni mediche/sanitarie o qualsiasi "
        f"tema medico delicato, NON dare MAI indicazioni mediche e NON rassicurare: rispondi ESATTAMENTE e SOLO "
        f"con il token [[RICHIAMO_MEDICO]] (esattamente così, senza altro testo). Il sistema farà richiamare la "
        f"cliente a voce dallo staff.\n\n"
        f"CONTESTO LEAD: nome={lead.get('nome')}, trattamento d'interesse={servizio}, "
        f"sede={lead.get('sede') or 'NON INDICATA'}, campagna={lead.get('campagna')}.\n"
        f"SEDI DISPONIBILI: Milano e Verona. Se la sede del lead è NON INDICATA, a un certo "
        f"punto chiedi esplicitamente: 'Ti interessa la sede di Milano o quella di Verona?'. "
        f"Se invece è già indicata, non richiederla.\n"
        f"DETTAGLI TRATTAMENTO: {svc.get('descrizione','')} Prezzo: {svc.get('prezzo','')}. "
        f"Promozione: {svc.get('promozione','')}. Info: {svc.get('info','')}.\n\n"
        f"KNOWLEDGE BASE:\n"
        f"Azienda: {kb.get('azienda','')}\nPrezzi: {kb.get('prezzi','')}\n"
        f"Promozioni: {kb.get('promozioni','')}\nSedi: {kb.get('sedi','')}\n"
        f"Orari: {kb.get('orari','')}\nFAQ: {kb.get('faq','')}\n"
        f"Obiezioni: {kb.get('obiezioni','')}\nPagamenti: {kb.get('pagamenti','')}\n"
        f"Da NON comunicare: {kb.get('non_comunicare','')}\n"
    )


import re

HEART_RE = re.compile(
    "[" 
    "\u2764\u2665\u2763"           # ❤ ♥ ❣
    "\U0001F495-\U0001F49F"        # 💕💖💗💘💙💚💛💜💝💞💟
    "\U0001F493\U0001F494"         # 💓 💔
    "\U0001FA75-\U0001FA77"        # 🩵 🩶 🩷
    "\U0001F9E1\U0001F5A4\U0001F90D\U0001F90E"  # 🧡 🖤 🤍 🤎
    "]\ufe0f?"
)


def strip_hearts(text: str) -> str:
    """Garanzia hard: rimuove qualsiasi cuore dalle risposte AI (regola non negoziabile)."""
    if not text:
        return text
    cleaned = HEART_RE.sub("", text)
    # ripulisci eventuali doppi spazi lasciati dalla rimozione
    return re.sub(r"[ \t]{2,}", " ", cleaned).strip()


# --- Fallback "richiamo" (Modulo A): l'AI non inventa mai ---
FALLBACK_GENERALE = ("Ok cara, ti richiamo a breve così ti do le disponibilità rimaste "
                     "e scegliamo l'orario migliore per te!")
FALLBACK_MEDICO = "Guarda, ti richiamo subito così ti spiego tutto a voce!"


def detect_ai_fallback(reply: str):
    """Se l'AI ha emesso un token di richiamo, ritorna (motivo, frase_naturale).
    Serve a garantire che l'assistente non inventi mai: quando non ha
    un'informazione certa o il tema è medico, passa la cliente allo staff."""
    if not reply:
        return (None, None)
    up = reply.upper()
    if "[[RICHIAMO_MEDICO]]" in up:
        return ("info_medica", FALLBACK_MEDICO)
    if "[[RICHIAMO]]" in up:
        return ("info_da_verificare", FALLBACK_GENERALE)
    return (None, None)


async def ai_generate_reply(conv: dict, lead: dict) -> str:
    """Genera la prossima risposta commerciale dell'AI dato lo storico chat."""
    msgs = await db.messages.find(
        {"conversation_id": conv["id"]}, {"_id": 0}).sort("created_at", 1).to_list(60)
    transcript = "\n".join(
        f"[{'Cliente' if m['sender']=='cliente' else ASSISTANT_NAME}]: {m['text']}"
        for m in msgs if m.get("type", "text") == "text")
    system = await build_ai_system_prompt(lead)
    prompt = (
        f"Conversazione WhatsApp finora:\n{transcript}\n\n"
        f"Scrivi SOLO il prossimo messaggio di {ASSISTANT_NAME} alla cliente. "
        f"Rispetta lo STILE NATURALE: varia l'apertura (NON iniziare sempre con Certo/Perfetto/"
        f"Assolutamente), niente cuori, emoji solo di rado. Se la domanda è semplice rispondi breve; "
        f"fai al massimo UNA domanda e non sempre; non ripetere cose già dette. "
        f"Se non hai un'informazione certa nella Knowledge Base usa il token [[RICHIAMO]]; "
        f"se è un tema medico/delicato usa il token [[RICHIAMO_MEDICO]] (non inventare mai)."
    )
    try:
        chat = LlmChat(api_key=EMERGENT_LLM_KEY, session_id=conv["id"],
                       system_message=system).with_model(AI_PROVIDER, AI_MODEL)
        reply = await chat.send_message(UserMessage(text=prompt))
        return strip_hearts((reply or "").strip()) or "Dimmi pure, come posso aiutarti?"
    except Exception as e:  # noqa
        logger.error(f"AI error: {e}")
        return ("Grazie del messaggio! Qual è il risultato principale che vorresti ottenere?")


class KbTestMsg(BaseModel):
    sender: str  # "cliente" | "ai"
    text: str


class KbTestInput(BaseModel):
    servizio: Optional[str] = None
    sede: Optional[str] = "Milano"
    messages: list[KbTestMsg] = []


@api.post("/kb/test")
async def kb_test(body: KbTestInput, user: dict = Depends(require_admin)):
    """Simulazione 'Test Andrea': risponde con la KB corrente, SENZA scrivere nulla nel DB."""
    lead = {
        "nome": "Cliente", "cognome": "Test", "servizio": body.servizio or "",
        "sede": body.sede or "Milano", "stato_pipeline": "ai_conversazione",
        "data_acquisizione": iso(now_utc()), "temperatura": "calda", "provenienza": "test",
    }
    system = await build_ai_system_prompt(lead)
    transcript = "\n".join(
        f"[{'Cliente' if m.sender == 'cliente' else ASSISTANT_NAME}]: {m.text}"
        for m in body.messages)
    prompt = (
        f"Conversazione WhatsApp finora:\n{transcript}\n\n"
        f"Scrivi SOLO il prossimo messaggio di {ASSISTANT_NAME} alla cliente, "
        f"rispettando le regole: usa SOLO informazioni della Knowledge Base, non inventare mai. "
        f"Se non hai un'informazione certa usa il token [[RICHIAMO]]; se è un tema medico/delicato "
        f"usa il token [[RICHIAMO_MEDICO]] (come da regole del sistema).")
    try:
        chat = LlmChat(api_key=EMERGENT_LLM_KEY, session_id=f"kbtest-{user['id']}",
                       system_message=system).with_model(AI_PROVIDER, AI_MODEL)
        reply = await chat.send_message(UserMessage(text=prompt))
        reply = strip_hearts((reply or "").strip())
        fb_motivo, fb_phrase = detect_ai_fallback(reply)
        if fb_motivo:
            label = ("IN ATTESA DI CHIAMATA (tema medico)" if fb_motivo == "info_medica"
                     else "IN ATTESA DI CHIAMATA")
            return {"reply": fb_phrase, "fallback": True, "motivo": fb_motivo,
                    "note": f"Andrea non ha inventato: la cliente verrebbe spostata in «{label}» "
                            f"con notifica all'operatrice."}
        return {"reply": reply}
    except Exception as e:  # noqa
        return {"reply": "", "error": str(e)[:200]}


# ---------------------------------------------------------------------------
# MODULO B — Prenotazione chiamate CORSI (Academy Manager)
# ---------------------------------------------------------------------------
def _ceil_30(dt_local: datetime) -> datetime:
    """Arrotonda al prossimo slot da 30 minuti (in avanti)."""
    dt = dt_local.replace(second=0, microsecond=0)
    if dt.minute == 0 or dt.minute == 30:
        return dt
    if dt.minute < 30:
        return dt.replace(minute=30)
    return (dt + timedelta(hours=1)).replace(minute=0)


def next_window_start(dt_local: datetime) -> datetime:
    """Primo inizio-slot valido (Mar–Sab, 09:00–18:00, griglia 30 min) >= dt_local."""
    dt = _ceil_30(dt_local)
    for _ in range(0, 14 * 48):
        if dt.weekday() in CALL_DAYS and CALL_START_HOUR <= dt.hour < CALL_END_HOUR:
            return dt
        if dt.weekday() not in CALL_DAYS or dt.hour >= CALL_END_HOUR:
            dt = (dt + timedelta(days=1)).replace(
                hour=CALL_START_HOUR, minute=0, second=0, microsecond=0)
        else:  # troppo presto nello stesso giorno valido
            dt = dt.replace(hour=CALL_START_HOUR, minute=0, second=0, microsecond=0)
    return dt


async def slot_is_free(start_utc: datetime) -> bool:
    end_utc = start_utc + timedelta(minutes=CALL_SLOT_MINUTES)
    taken = await db.call_slots.find(
        {"status": "fissata"}, {"_id": 0, "start": 1, "end": 1}).to_list(500)
    for s in taken:
        try:
            ss = datetime.fromisoformat(s["start"])
            se = datetime.fromisoformat(s["end"])
        except Exception:
            continue
        if start_utc < se and ss < end_utc:  # overlap
            return False
    return True


async def find_nearest_free_slot(preferred_local: datetime):
    """Ritorna (slot_local, exact_bool) o (None, False) se niente entro ~2 settimane."""
    requested = next_window_start(preferred_local)
    cur = requested
    for _ in range(0, 14 * 20):
        start_utc = cur.astimezone(timezone.utc)
        if await slot_is_free(start_utc):
            return cur, (cur == requested)
        cur = next_window_start(cur + timedelta(minutes=CALL_SLOT_MINUTES))
    return None, False


def is_confirmation(text: str) -> bool:
    low = (text or "").strip().lower()
    if not low:
        return False
    return any(w in low for w in CONFIRM_WORDS)


async def extract_call_datetime(text: str):
    """Usa l'LLM per estrarre giorno+ora preferiti dal messaggio della cliente.
    Ritorna un datetime aware (Rome) oppure None."""
    now_local = now_utc().astimezone(ROME_TZ)
    system = (
        "Estrai da un messaggio (italiano) la preferenza di giorno e ora per una CHIAMATA. "
        "Rispondi SOLO con JSON valido, nessun altro testo. Formato: "
        '{"datetime": "YYYY-MM-DDTHH:MM"} oppure {"datetime": null}. '
        f"Adesso è {now_local.strftime('%Y-%m-%d %H:%M')} ({now_local.strftime('%A')}). "
        "Interpreta 'domani', 'dopodomani', i giorni della settimana e le date relative a questo istante. "
        "Se indica solo una fascia: mattina=10:00, pomeriggio=15:00, sera=17:00. "
        "Se manca l'ora ma c'è il giorno, usa 10:00. "
        "Se NON è indicato alcun giorno/data (solo un orario vago o nessuna preferenza), usa datetime=null."
    )
    try:
        chat = LlmChat(api_key=EMERGENT_LLM_KEY, session_id=f"extract-{uuid.uuid4()}",
                       system_message=system).with_model(AI_PROVIDER, AI_MODEL)
        raw = await chat.send_message(UserMessage(text=text or ""))
        raw = (raw or "").strip()
        mobj = re.search(r"\{.*\}", raw, re.DOTALL)
        if not mobj:
            return None
        data = json.loads(mobj.group(0))
        val = data.get("datetime")
        if not val:
            return None
        dt = datetime.fromisoformat(val)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=ROME_TZ)
        return dt.astimezone(ROME_TZ)
    except Exception as e:  # noqa
        logger.warning(f"extract_call_datetime failed: {e}")
        return None


def _fmt_slot(dt_local: datetime) -> str:
    giorni = ["lunedì", "martedì", "mercoledì", "giovedì", "venerdì", "sabato", "domenica"]
    return f"{giorni[dt_local.weekday()]} {dt_local.strftime('%d/%m')} alle {dt_local.strftime('%H:%M')}"


async def finalize_course_call(lead: dict, conv: dict, slot_iso: str) -> str:
    """Fissa definitivamente la chiamata corso e sposta il lead in
    'chiamata_corso_fissata'. Ritorna il messaggio di conferma naturale."""
    start_utc = datetime.fromisoformat(slot_iso).astimezone(timezone.utc)
    end_utc = start_utc + timedelta(minutes=CALL_SLOT_MINUTES)
    slot_local = start_utc.astimezone(ROME_TZ)
    await db.call_slots.insert_one({
        "id": str(uuid.uuid4()), "lead_id": lead["id"], "conversation_id": conv["id"],
        "nome": lead.get("nome", ""), "cognome": lead.get("cognome", ""),
        "telefono": lead.get("telefono", ""), "servizio": lead.get("servizio", ""),
        "sede": lead.get("sede", ""), "start": iso(start_utc), "end": iso(end_utc),
        "status": "fissata", "reminded": False, "created_at": iso(now_utc()),
    })
    from_status = lead["stato_pipeline"]
    await cancel_followups(lead["id"])
    await db.leads.update_one({"id": lead["id"]}, {"$set": {
        "stato_pipeline": "chiamata_corso_fissata", "temperature": "molto_calda",
        "call_slot_at": iso(start_utc), "handoff_at": iso(now_utc()),
        "ultimo_contatto": iso(now_utc()),
    }})
    await db.conversations.update_one({"id": conv["id"]}, {"$set": {
        "ai_attiva": False, "stato": "chiamata_corso_fissata",
        "corso_proposed_slot": None,
    }})
    await record_status_change(lead, from_status, "chiamata_corso_fissata", "ai")
    await create_notification("chiamata_corso", lead,
                              f"Chiamata corso fissata per {_fmt_slot(slot_local)}")
    nome = f"{lead['nome']} {lead['cognome']}".strip()
    await notify_staff_push(
        "Chiamata corso fissata",
        f"{nome} · {_fmt_slot(slot_local)}",
        f"/conversation/{conv['id']}")
    return (f"Perfetto, allora ti chiamo {_fmt_slot(slot_local)}. "
            f"Ci sentiamo lì e ti spiego tutto con calma, a presto!")


async def handle_corso_turn(conv: dict, lead: dict, text: str):
    """Gestisce un turno per un lead CORSO.
    Ritorna (handled, reply_text, booked)."""
    proposed = conv.get("corso_proposed_slot")
    # 1) conferma di uno slot proposto
    if proposed and is_confirmation(text):
        msg = await finalize_course_call(lead, conv, proposed)
        return True, msg, True
    # 2) estrai preferenza giorno/ora
    dt_pref = await extract_call_datetime(text)
    if dt_pref:
        slot_local, exact = await find_nearest_free_slot(dt_pref)
        if not slot_local:
            return (True, "Guarda, nei prossimi giorni ho l'agenda piena per le chiamate. "
                          "Ti va se ti ricontatto io appena si libera uno spazio?", False)
        await db.conversations.update_one({"id": conv["id"]}, {"$set": {
            "corso_proposed_slot": iso(slot_local.astimezone(timezone.utc))}})
        if exact:
            msg = (f"Benissimo, allora ti chiamo {_fmt_slot(slot_local)}. "
                   f"Ti confermo? Così blocco lo spazio per te.")
        else:
            msg = (f"In quel momento sono già presa, ma il primo spazio libero è "
                   f"{_fmt_slot(slot_local)}. Ti va bene? Così te lo blocco.")
        return True, msg, False
    # 3) nessuna preferenza: lascia rispondere l'AI (qualifica + chiede giorno/ora)
    return False, None, False


# ---------------------------------------------------------------------------
# MODULO B — Flusso TRATTAMENTI su WhatsApp (script approvato, deterministico)
# ---------------------------------------------------------------------------
def match_treatment(lead: dict):
    """Riconosce il trattamento dalla campagna/servizio/inserzione. Ritorna
    (label, prezzo, promo) oppure None."""
    blob = " ".join(str(lead.get(k) or "") for k in
                    ("servizio", "campagna", "inserzione", "form_name")).lower()
    for key, val in TREATMENT_PRICES.items():
        if key in blob:
            return val
    return None


def promo_phrase(lead: dict, label: str, prezzo: int, promo: int) -> str:
    """Frase promo approvata, con scadenza = data primo contatto + 10 giorni."""
    try:
        base = datetime.fromisoformat(lead.get("data_acquisizione"))
    except Exception:
        base = now_utc()
    deadline = (base + timedelta(days=10)).astimezone(ROME_TZ).strftime("%d/%m/%Y")
    return (f"Il trattamento {label} costa €{prezzo}, ma è in promozione a metà prezzo, "
            f"ovvero €{promo}, fino al {deadline} e fino a esaurimento posti disponibili. "
            f"Ti richiamo a breve per comunicarti le disponibilità rimaste.")


async def _tratt_to_richiamare(lead: dict, conv: dict, notify_body: str):
    """Sposta il contatto in 'Contatti da richiamare' (attesa_chiamata) e spegne l'AI."""
    from_status = lead["stato_pipeline"]
    await cancel_followups(lead["id"])
    await db.leads.update_one({"id": lead["id"]}, {"$set": {
        "stato_pipeline": "attesa_chiamata", "temperature": "molto_calda",
        "handoff_at": iso(now_utc()), "ultimo_contatto": iso(now_utc())}})
    await db.conversations.update_one({"id": conv["id"]}, {"$set": {
        "ai_attiva": False, "stato": "attesa_chiamata"}})
    if from_status != "attesa_chiamata":
        await record_status_change(lead, from_status, "attesa_chiamata", "ai")
    await create_notification("ai_intervento", lead, notify_body)
    nome = f"{lead['nome']} {lead.get('cognome','')}".strip()
    extra = f" · {lead['servizio']}" if lead.get("servizio") else ""
    await notify_staff_push("Contatto da richiamare", f"{nome}{extra}",
                            f"/conversation/{conv['id']}")


async def ai_answer_from_scheda(conv: dict, lead: dict) -> str:
    """Risposta di Andrea basata ESCLUSIVAMENTE sulla scheda del trattamento
    (descrizione, info, faq) + info generali della Knowledge Base. Se l'informazione
    non c'è emette [[RICHIAMO]]; per temi medici [[RICHIAMO_MEDICO]]."""
    svc = await db.services.find_one({"nome": lead.get("servizio")}, {"_id": 0}) if lead.get("servizio") else None
    kb = await db.knowledge_base.find_one({}, {"_id": 0}) or {}
    msgs = await db.messages.find(
        {"conversation_id": conv["id"]}, {"_id": 0}).sort("created_at", 1).to_list(500)
    recent = msgs[-12:]
    transcript = "\n".join(
        f"{'Cliente' if m['sender'] == 'cliente' else ASSISTANT_NAME}: {m['text']}"
        for m in recent)
    if svc:
        scheda = (f"TRATTAMENTO: {svc.get('nome','')}\n"
                  f"Descrizione: {svc.get('descrizione','')}\n"
                  f"Info: {svc.get('info','')}\n"
                  f"FAQ: {svc.get('faq','')}")
    else:
        scheda = "Nessuna scheda disponibile per questo trattamento."
    system = (
        f"Sei {ASSISTANT_NAME} di {BRAND_NAME}, assistente su WhatsApp. Rispondi in italiano, "
        f"tono caldo e naturale, messaggio BREVE (stile WhatsApp), una sola risposta, niente cuori.\n"
        f"REGOLA ANTI-INVENZIONE (FONDAMENTALE): rispondi USANDO SOLO le informazioni nella SCHEDA "
        f"TRATTAMENTO e nelle INFO GENERALI qui sotto. Se la risposta NON è presente in queste "
        f"informazioni, NON inventare e NON tirare a indovinare: rispondi ESATTAMENTE e SOLO con il "
        f"token [[RICHIAMO]] (senza altro testo).\n"
        f"REGOLA TEMI MEDICI: per controindicazioni, gravidanza/allattamento, patologie, farmaci o "
        f"qualsiasi tema medico, rispondi ESATTAMENTE e SOLO con [[RICHIAMO_MEDICO]].\n"
        f"NON parlare di prezzi (li gestisce un altro flusso): se chiedono il prezzo usa [[RICHIAMO]].\n\n"
        f"SCHEDA TRATTAMENTO:\n{scheda}\n\n"
        f"INFO GENERALI:\nAzienda: {kb.get('azienda','')}\nSedi: {kb.get('sedi','')}\n"
        f"Orari: {kb.get('orari','')}\nFAQ generali: {kb.get('faq','')}\n")
    try:
        chat = LlmChat(api_key=EMERGENT_LLM_KEY, session_id=conv["id"],
                       system_message=system).with_model(AI_PROVIDER, AI_MODEL)
        prompt = (f"Conversazione WhatsApp finora:\n{transcript}\n\n"
                  f"Scrivi SOLO il prossimo messaggio di {ASSISTANT_NAME} alla cliente.")
        reply = await chat.send_message(UserMessage(text=prompt))
        return strip_hearts((reply or "").strip())
    except Exception as e:  # noqa
        logger.warning(f"ai_answer_from_scheda failed: {e}")
        return "[[RICHIAMO]]"


async def handle_trattamento_turn(conv: dict, lead: dict, text: str):
    """Gestisce un turno per un lead TRATTAMENTO.
    - prezzo → frase promo approvata → richiamata
    - prenotazione → 'informazione precisa' → richiamata
    - temi medici → 'informazione precisa' → richiamata
    - non può parlare → chiede orario preferito e lo salva
    - primo contatto → mostra le 2 domande preimpostate
    - altre domande sul trattamento → risposta basata sulla SCHEDA (mai inventare;
      se l'info non c'è → richiamata)
    Ritorna (handled, reply, keep_ai_on, needs_buttons). handled è sempre True."""
    low = (text or "").lower()

    # 0) stavamo aspettando l'orario preferito di richiamo
    if conv.get("awaiting_richiamo_time"):
        orario = (text or "").strip()
        await db.leads.update_one({"id": lead["id"]}, {"$set": {
            "orario_preferito_richiamo": orario}})
        await db.conversations.update_one({"id": conv["id"]}, {"$set": {
            "awaiting_richiamo_time": False}})
        await _tratt_to_richiamare(lead, conv, f"Da richiamare — orario preferito: {orario}")
        return True, f"Perfetto, allora ti richiamo io {orario}. A prestissimo!", False, False

    # 1) prezzo → frase promo approvata
    if any(w in low for w in PRICE_WORDS):
        t = match_treatment(lead)
        reply = promo_phrase(lead, *t) if t else INFO_PRECISA
        await _tratt_to_richiamare(lead, conv, "Ha chiesto il prezzo: da richiamare")
        return True, reply, False, False

    # 2) vuole prenotare → frase "informazione precisa"
    if any(w in low for w in BOOKING_WORDS):
        await _tratt_to_richiamare(lead, conv, "Vuole fissare un appuntamento: da richiamare")
        return True, INFO_PRECISA, False, False

    # 3) temi medici/delicati → sempre alla chiamata
    if any(w in low for w in MEDICAL_WORDS):
        await _tratt_to_richiamare(lead, conv, "Domanda su tema medico: da richiamare")
        return True, INFO_PRECISA, False, False

    # 4) non può parlare ora → chiedi orario preferito
    if any(w in low for w in CANT_TALK_WORDS):
        await db.conversations.update_one({"id": conv["id"]}, {"$set": {
            "awaiting_richiamo_time": True}})
        await db.leads.update_one({"id": lead["id"]}, {"$set": {
            "stato_pipeline": "attesa_chiamata", "ultimo_contatto": iso(now_utc())}})
        return True, "Certo, nessun problema! A che ora preferisci che ti richiami?", True, False

    # 5) primo contatto → presenta le due domande preimpostate
    if not conv.get("tratt_menu_shown"):
        await db.conversations.update_one({"id": conv["id"]}, {"$set": {"tratt_menu_shown": True}})
        reply = (f"Ciao {lead.get('nome','')}! Sono {ASSISTANT_NAME} di {BRAND_NAME}. "
                 f"Come posso aiutarti? Puoi chiedermi:\n"
                 f"• Quanto costa il trattamento?\n• Posso fissare un appuntamento?")
        return True, reply, True, True

    # 6) altra domanda sul trattamento → risposta basata SOLO sulla scheda
    reply = await ai_answer_from_scheda(conv, lead)
    fb_motivo, _ = detect_ai_fallback(reply)
    if fb_motivo:
        await _tratt_to_richiamare(lead, conv, "Info non presente nella scheda: da richiamare")
        return True, INFO_PRECISA, False, False
    await db.leads.update_one({"id": lead["id"]}, {"$set": {
        "stato_pipeline": "ai_conversazione", "ultimo_contatto": iso(now_utc())}})
    return True, reply, True, False


# --- Reminder chiamate corso: avviso + push 1 ora prima ---
async def call_reminder_worker():
    while True:
        try:
            now = now_utc()
            soon = now + timedelta(minutes=60)
            due = await db.call_slots.find(
                {"status": "fissata", "reminded": {"$ne": True},
                 "start": {"$lte": iso(soon), "$gte": iso(now)}}, {"_id": 0}).to_list(50)
            for s in due:
                lead = await db.leads.find_one({"id": s["lead_id"]}, {"_id": 0})
                if not lead:
                    continue
                slot_local = datetime.fromisoformat(s["start"]).astimezone(ROME_TZ)
                nome = f"{s.get('nome','')} {s.get('cognome','')}".strip()
                await create_notification(
                    "promemoria_chiamata_corso", lead,
                    f"Tra poco: chiamata corso con {nome} alle {slot_local.strftime('%H:%M')}")
                await notify_staff_push(
                    "Promemoria chiamata corso",
                    f"{nome} · oggi alle {slot_local.strftime('%H:%M')}",
                    f"/conversation/{s.get('conversation_id')}")
                await db.call_slots.update_one({"id": s["id"]}, {"$set": {"reminded": True}})
        except Exception as e:  # noqa
            logger.error(f"call_reminder_worker error: {e}")
        await asyncio.sleep(60)


# --- Endpoints: chiamate corso, prezzi corsi, tipo campagna ---
@api.get("/call-slots")
async def list_call_slots(user: dict = Depends(current_user)):
    slots = await db.call_slots.find(
        {"status": "fissata"}, {"_id": 0}).sort("start", 1).to_list(200)
    now = now_utc()
    out = []
    for s in slots:
        try:
            start = datetime.fromisoformat(s["start"])
        except Exception:
            continue
        mins = (start - now).total_seconds() / 60.0
        out.append({**s, "starts_in_minutes": round(mins),
                    "imminent": 0 <= mins <= 60})
    return out


class CallSlotUpdate(BaseModel):
    status: str  # fissata | annullata | completata


@api.patch("/call-slots/{slot_id}")
async def update_call_slot(slot_id: str, body: CallSlotUpdate,
                           user: dict = Depends(current_user)):
    if body.status not in ("fissata", "annullata", "completata"):
        raise HTTPException(400, "status non valido")
    slot = await db.call_slots.find_one({"id": slot_id}, {"_id": 0})
    if not slot:
        raise HTTPException(404, "Slot non trovato")
    await db.call_slots.update_one({"id": slot_id}, {"$set": {"status": body.status}})
    return await db.call_slots.find_one({"id": slot_id}, {"_id": 0})


@api.get("/course-prices")
async def get_course_prices(user: dict = Depends(require_admin)):
    corso = await get_corso_config()
    return {"prezzi": corso.get("prezzi", ""), "updated_at": corso.get("updated_at")}


class CoursePricesInput(BaseModel):
    prezzi: str = ""


@api.patch("/course-prices")
async def set_course_prices(body: CoursePricesInput, user: dict = Depends(require_admin)):
    await db.integration_config.update_one(
        {"key": "corsi"},
        {"$set": {"key": "corsi", "prezzi": body.prezzi.strip(),
                  "updated_at": iso(now_utc())}}, upsert=True)
    return {"prezzi": body.prezzi.strip()}


class CampaignTipoInput(BaseModel):
    tipo: str  # corso | trattamento


@api.patch("/campaigns/{campaign_id}")
async def update_campaign_tipo(campaign_id: str, body: CampaignTipoInput,
                               user: dict = Depends(require_admin)):
    if body.tipo not in ("corso", "trattamento"):
        raise HTTPException(400, "tipo non valido")
    camp = await db.campaigns.find_one({"id": campaign_id})
    if not camp:
        raise HTTPException(404, "Campagna non trovata")
    await db.campaigns.update_one({"id": campaign_id}, {"$set": {"tipo": body.tipo}})
    return await db.campaigns.find_one({"id": campaign_id}, {"_id": 0})




# ---------------------------------------------------------------------------
# OBJECT STORAGE — immagini prima/dopo dei trattamenti
# ---------------------------------------------------------------------------
def _init_storage():
    global _storage_key
    if _storage_key:
        return _storage_key
    r = requests.post(f"{STORAGE_URL}/init", json={"emergent_key": EMERGENT_LLM_KEY}, timeout=30)
    r.raise_for_status()
    _storage_key = r.json()["storage_key"]
    return _storage_key


def _put_object(path: str, data: bytes, ct: str):
    key = _init_storage()
    r = requests.put(f"{STORAGE_URL}/objects/{path}",
                     headers={"X-Storage-Key": key, "Content-Type": ct},
                     data=data, timeout=120)
    r.raise_for_status()
    return r.json()


def _get_object(path: str):
    key = _init_storage()
    r = requests.get(f"{STORAGE_URL}/objects/{path}",
                     headers={"X-Storage-Key": key}, timeout=60)
    r.raise_for_status()
    return r.content, r.headers.get("Content-Type", "application/octet-stream")


@api.post("/upload")
async def upload_image(file: UploadFile = File(...), user: dict = Depends(require_admin)):
    ext = (file.filename or "img.jpg").rsplit(".", 1)[-1].lower()
    if ext not in ("jpg", "jpeg", "png", "webp"):
        raise HTTPException(400, "Formato immagine non supportato")
    data = await file.read()
    if len(data) > 8 * 1024 * 1024:
        raise HTTPException(400, "Immagine troppo grande (max 8MB)")
    path = f"supergirl/uploads/{user['id']}/{uuid.uuid4()}.{ext}"
    ct = file.content_type or "image/jpeg"
    await run_in_threadpool(_put_object, path, data, ct)
    await db.uploads.insert_one({"path": path, "owner_id": user["id"],
                                 "created_at": iso(now_utc())})
    return {"path": path, "url": f"/api/files/{path}"}


@api.get("/files/{path:path}")
async def serve_file(path: str):
    try:
        content, ct = await run_in_threadpool(_get_object, path)
    except Exception:
        raise HTTPException(404, "File non trovato")
    return Response(content=content, media_type=ct,
                    headers={"Cache-Control": "public, max-age=86400"})


# ---------------------------------------------------------------------------
# WHATSAPP BUSINESS CLOUD API (Fase 3) — config in DB, editabile da Admin
# ---------------------------------------------------------------------------
WA_ENV = {
    "phone_number_id": os.environ.get("WHATSAPP_PHONE_NUMBER_ID", "REPLACE_ME"),
    "waba_id": os.environ.get("WHATSAPP_WABA_ID", "REPLACE_ME"),
    "token": os.environ.get("WHATSAPP_TOKEN", "REPLACE_ME"),
    "app_secret": os.environ.get("WHATSAPP_APP_SECRET", "REPLACE_ME"),
    "verify_token": os.environ.get("WHATSAPP_VERIFY_TOKEN", ""),
    "template_name": os.environ.get("WHATSAPP_TEMPLATE_NAME", "nuovo_lead_foto"),
    "template_language": os.environ.get("WHATSAPP_TEMPLATE_LANGUAGE", "it"),
    "numero": "",
}


async def get_wa_config() -> dict:
    cfg = await db.integration_config.find_one({"key": "whatsapp"}, {"_id": 0}) or {}
    out = {}
    for k, default in WA_ENV.items():
        val = cfg.get(k)
        out[k] = val if (val not in (None, "")) else default
    return out


def wa_is_configured(cfg: dict) -> bool:
    return all(cfg.get(k) and cfg.get(k) != "REPLACE_ME"
               for k in ("phone_number_id", "token"))


async def whatsapp_send_text(to: str, body: str):
    cfg = await get_wa_config()
    if not wa_is_configured(cfg) or not to:
        return {"skipped": True}
    url = f"https://graph.facebook.com/{META_API_VERSION}/{cfg['phone_number_id']}/messages"
    payload = {"messaging_product": "whatsapp", "recipient_type": "individual",
               "to": to, "type": "text", "text": {"preview_url": False, "body": body}}
    async with httpx.AsyncClient(timeout=20) as c:
        r = await c.post(url, headers={"Authorization": f"Bearer {cfg['token']}"}, json=payload)
    if r.is_error:
        logger.error(f"WA text error: {r.text}")
    return r.json() if not r.is_error else {"error": r.text}


async def whatsapp_send_buttons(to: str, body: str, buttons: list):
    """Invia un messaggio interattivo con quick-reply buttons (max 3, titoli <=20 char)."""
    cfg = await get_wa_config()
    if not wa_is_configured(cfg) or not to:
        return {"skipped": True}
    url = f"https://graph.facebook.com/{META_API_VERSION}/{cfg['phone_number_id']}/messages"
    payload = {
        "messaging_product": "whatsapp", "recipient_type": "individual", "to": to,
        "type": "interactive",
        "interactive": {
            "type": "button",
            "body": {"text": body[:1024]},
            "action": {"buttons": [
                {"type": "reply", "reply": {"id": b["id"], "title": b["title"][:20]}}
                for b in buttons[:3]]},
        },
    }
    async with httpx.AsyncClient(timeout=20) as c:
        r = await c.post(url, headers={"Authorization": f"Bearer {cfg['token']}"}, json=payload)
    if r.is_error:
        logger.error(f"WA buttons error: {r.text}")
    return r.json() if not r.is_error else {"error": r.text}


async def whatsapp_send_template(to: str, nome: str, servizio: str, image_link: Optional[str]):
    cfg = await get_wa_config()
    if not wa_is_configured(cfg) or not to:
        return {"skipped": True}
    components = []
    if image_link:
        if image_link.startswith("/"):
            base = (os.environ.get("PUBLIC_BASE_URL") or "").rstrip("/")
            image_link = f"{base}{image_link}" if base else image_link
        components.append({"type": "header", "parameters": [
            {"type": "image", "image": {"link": image_link}}]})
    components.append({"type": "body", "parameters": [
        {"type": "text", "text": nome},
        {"type": "text", "text": servizio}]})
    payload = {"messaging_product": "whatsapp", "recipient_type": "individual",
               "to": to, "type": "template",
               "template": {"name": cfg["template_name"],
                            "language": {"code": cfg["template_language"]},
                            "components": components}}
    url = f"https://graph.facebook.com/{META_API_VERSION}/{cfg['phone_number_id']}/messages"
    async with httpx.AsyncClient(timeout=20) as c:
        r = await c.post(url, headers={"Authorization": f"Bearer {cfg['token']}"}, json=payload)
    if r.is_error:
        logger.error(f"WA template error: {r.text}")
    return r.json() if not r.is_error else {"error": r.text}


# ---------------------------------------------------------------------------
# FOLLOW-UP AUTOMATICI (incrementale, non tocca pipeline/webhook esistenti)
# ---------------------------------------------------------------------------
FOLLOWUP_TEMPLATE_NAME = "promemoria_followup"

DEFAULT_FOLLOWUP_RULES = {
    "enabled": True,
    "quiet_start": 9,   # ora locale minima (Europe/Rome)
    "quiet_end": 19,    # ora locale massima
    "steps": [
        {"label": "Follow-up 1", "delay_hours": 4,
         "message": "Ciao {nome}, sono Andrea di J'adore Mimì. Hai avuto modo di pensare al trattamento di cui parlavamo? Se hai qualche dubbio scrivimi pure, ti rispondo io."},
        {"label": "Follow-up 2", "delay_hours": 24,
         "message": "Ciao {nome}, ci tengo a risentirti: se vuoi ti spiego meglio come funziona la prima seduta da J'adore Mimì. Ti va se ne parliamo?"},
    ],
    # Testi alternativi selezionabili dal pannello
    "message_options": [
        "Ciao {nome}, sono Andrea di J'adore Mimì. Posso aiutarti a scegliere il trattamento giusto per te?",
        "Ciao {nome}, hai ancora qualche dubbio? Scrivimi pure, ti rispondo subito io 😊",
        "Ciao {nome}, vuoi che ti spieghi meglio come possiamo aiutarti con il tuo obiettivo?",
    ],
}


async def get_followup_rules_doc() -> dict:
    doc = await db.followup_rules.find_one({}, {"_id": 0})
    if not doc or not doc.get("steps"):
        return DEFAULT_FOLLOWUP_RULES
    return {**DEFAULT_FOLLOWUP_RULES, **doc}


def _rome_adjust(dt_utc: datetime, quiet_start: int, quiet_end: int) -> datetime:
    """Sposta l'orario nella finestra locale [quiet_start, quiet_end)."""
    local = dt_utc.astimezone(ROME_TZ)
    if local.hour < quiet_start:
        local = local.replace(hour=quiet_start, minute=0, second=0, microsecond=0)
    elif local.hour >= quiet_end:
        local = (local + timedelta(days=1)).replace(
            hour=quiet_start, minute=0, second=0, microsecond=0)
    return local.astimezone(timezone.utc)


async def schedule_followups(lead: dict):
    """Programma i follow-up per un lead appena creato (idempotente per label)."""
    rules = await get_followup_rules_doc()
    if not rules.get("enabled", True):
        return
    now = now_utc()
    for step in rules.get("steps", []):
        due = _rome_adjust(now + timedelta(hours=float(step.get("delay_hours", 4))),
                           int(rules.get("quiet_start", 9)), int(rules.get("quiet_end", 19)))
        await db.followups.insert_one({
            "id": str(uuid.uuid4()), "lead_id": lead["id"],
            "label": step.get("label", "Follow-up"),
            "message": step.get("message", ""),
            "due_at": iso(due), "status": "programmato",
            "created_at": iso(now), "updated_at": iso(now),
        })


async def _send_one_followup(fu: dict):
    lead = await db.leads.find_one({"id": fu["lead_id"]}, {"_id": 0})
    if not lead:
        await db.followups.update_one({"id": fu["id"]}, {"$set": {"status": "annullato"}})
        return
    # Se la cliente è già avanzata (ha risposto / handoff / prenotata), salta
    if lead.get("stato_pipeline") in ("attesa_chiamata", "da_fissare", "prenotato", "perso", "cliente"):
        await db.followups.update_one({"id": fu["id"]}, {"$set": {"status": "annullato"}})
        return
    conv = await db.conversations.find_one({"lead_id": lead["id"]}, {"_id": 0})
    if not conv:
        await db.followups.update_one({"id": fu["id"]}, {"$set": {"status": "annullato"}})
        return
    nome = lead.get("nome", "").strip() or "ciao"
    text = (fu.get("message") or "Ciao {nome}").replace("{nome}", nome)
    tel = lead.get("telefono", "")
    # Finestra 24h: ultimo messaggio cliente
    msgs = await db.messages.find({"conversation_id": conv["id"]}, {"_id": 0}).to_list(500)
    last_cust = None
    for m in msgs:
        if m.get("sender") == "cliente":
            ts = m.get("created_at")
            if ts and (last_cust is None or ts > last_cust):
                last_cust = ts
    within_24h = False
    if last_cust:
        try:
            within_24h = (now_utc() - datetime.fromisoformat(last_cust)) < timedelta(hours=24)
        except Exception:
            within_24h = False
    try:
        if within_24h:
            await whatsapp_send_text(tel, text)
        else:
            await whatsapp_send_followup_template(tel, nome)
    except Exception as e:
        logger.error(f"followup send failed: {e}")
        return
    now = iso(now_utc())
    await db.messages.insert_one({
        "id": str(uuid.uuid4()), "conversation_id": conv["id"], "sender": "ai",
        "text": text, "type": "text", "created_at": now, "read": True,
    })
    await db.conversations.update_one({"id": conv["id"]}, {"$set": {
        "last_message": text, "last_message_at": now}})
    await db.followups.update_one({"id": fu["id"]}, {"$set": {
        "status": "inviato", "sent_at": now, "updated_at": now}})


async def whatsapp_send_followup_template(to: str, nome: str):
    cfg = await get_wa_config()
    if not wa_is_configured(cfg) or not to:
        return {"skipped": True}
    payload = {"messaging_product": "whatsapp", "recipient_type": "individual",
               "to": to, "type": "template",
               "template": {"name": FOLLOWUP_TEMPLATE_NAME,
                            "language": {"code": cfg.get("template_language", "it")},
                            "components": [{"type": "body", "parameters": [
                                {"type": "text", "text": nome}]}]}}
    url = f"https://graph.facebook.com/{META_API_VERSION}/{cfg['phone_number_id']}/messages"
    async with httpx.AsyncClient(timeout=20) as c:
        r = await c.post(url, headers={"Authorization": f"Bearer {cfg['token']}"}, json=payload)
    if r.is_error:
        logger.error(f"WA followup template error: {r.text}")
    return r.json() if not r.is_error else {"error": r.text}


async def followup_worker():
    """Loop in background: invia i follow-up dovuti, rispettando gli orari."""
    while True:
        try:
            rules = await get_followup_rules_doc()
            if rules.get("enabled", True):
                now_iso = iso(now_utc())
                local_h = now_utc().astimezone(ROME_TZ).hour
                in_hours = int(rules.get("quiet_start", 9)) <= local_h < int(rules.get("quiet_end", 19))
                if in_hours:
                    due = await db.followups.find(
                        {"status": "programmato", "due_at": {"$lte": now_iso}},
                        {"_id": 0}).to_list(50)
                    for fu in due:
                        await _send_one_followup(fu)
        except Exception as e:
            logger.error(f"followup_worker error: {e}")
        await asyncio.sleep(120)


def _mask_token(v: str) -> Optional[str]:
    if not v:
        return None
    if len(v) <= 4:
        return "•" * len(v)
    return f"{v[:2]}…{v[-2:]}"


@api.get("/integrations/whatsapp/webhook", response_class=PlainTextResponse)
async def wa_verify(request: Request):
    cfg = await get_wa_config()
    p = request.query_params
    expected = (cfg.get("verify_token") or "").strip()
    received = (p.get("hub.verify_token") or "").strip()
    if p.get("hub.mode") == "subscribe" and expected and hmac.compare_digest(received, expected):
        return p.get("hub.challenge") or ""
    raise HTTPException(status_code=403, detail="Verifica webhook fallita")


@api.post("/integrations/whatsapp/webhook")
async def wa_webhook(request: Request):
    cfg = await get_wa_config()
    raw = await request.body()
    sig = request.headers.get("x-hub-signature-256")
    secret = cfg.get("app_secret")
    if secret and secret != "REPLACE_ME":
        expected = "sha256=" + hmac.new(secret.encode(), raw, hashlib.sha256).hexdigest()
        if not sig or not hmac.compare_digest(expected, sig):
            raise HTTPException(status_code=403, detail="Firma non valida")
    try:
        payload = await request.json()
    except Exception:
        payload = {}
    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            for m in value.get("messages", []):
                # elaborazione in background: consente il "sta scrivendo…"
                # proporzionale senza bloccare la risposta 200 al webhook
                asyncio.create_task(_safe_handle_inbound(m, value))
            for s in value.get("statuses", []):
                await db.messages.update_one(
                    {"wa_id": s.get("id")},
                    {"$set": {"wa_status": s.get("status")}})
    return {"ok": True}


async def _safe_handle_inbound(m: dict, value: dict):
    try:
        await handle_inbound_wa(m, value)
    except Exception as e:  # noqa
        logger.error(f"inbound handler error: {e}")


async def ctwa_ad_info(referral: dict):
    """Per un messaggio WhatsApp arrivato da un annuncio (Click-to-WhatsApp):
    risale a nome annuncio + campagna via Graph (source_id = ad id).
    Ritorna (allowed_SG, campagna, inserzione, piattaforma)."""
    ad_id = (referral or {}).get("source_id")
    camp_name, ad_name, platform = None, None, "WhatsApp"
    if ad_id:
        try:
            ad = await graph_get(
                ad_id, "id,name,campaign{id,name},creative{id,instagram_actor_id}")
            ad_name = ad.get("name")
            camp_name = (ad.get("campaign") or {}).get("name")
            if (ad.get("creative") or {}).get("instagram_actor_id"):
                platform = "Instagram"
            else:
                platform = "Facebook"
        except Exception as e:  # noqa
            logger.warning(f"CTWA ad lookup fallito ({ad_id}): {e}")
    # Fail-closed: attiva SOLO se annuncio o campagna hanno prefisso SG-
    allowed = sg_prefixed(ad_name) or sg_prefixed(camp_name)
    return allowed, camp_name, ad_name, platform


async def create_inbound_lead(wa_from: str, value: dict, campagna: str = "WhatsApp Diretto",
                              inserzione: str = "Contatto Organico", piattaforma: str = "WhatsApp",
                              origine: str = "whatsapp_organico"):
    """Crea un lead + conversazione per un contatto WhatsApp (organico o da annuncio SG-)."""
    now = iso(now_utc())
    contacts = value.get("contacts", [])
    profile_name = ""
    if contacts:
        profile_name = (contacts[0].get("profile") or {}).get("name") or ""
    tel = wa_from if wa_from.startswith("+") else "+" + wa_from
    lid = str(uuid.uuid4())
    camp_doc = await db.campaigns.find_one({"nome": campagna}, {"_id": 0}) if campagna else None
    tipo = (camp_doc or {}).get("tipo") or "trattamento"
    lead = {
        "id": lid, "nome": profile_name or "Cliente WhatsApp", "cognome": "",
        "telefono": tel, "email": "",
        "servizio": "", "sede": "",
        "campagna": campagna, "inserzione": inserzione,
        "piattaforma": piattaforma,
        "ig_username": None, "ig_display_name": None, "foto_profilo": None,
        "data_acquisizione": now, "ultimo_contatto": now,
        "stato_pipeline": "ai_conversazione", "temperature": "da_coltivare",
        "operatore_assegnato": None, "esigenza": "", "obiezioni": "",
        "note_staff": "", "ai_summary": None, "handoff_at": None,
        "leadgen_id": None, "origine": origine, "tipo": tipo,
    }
    await db.leads.insert_one(lead)
    cid = str(uuid.uuid4())
    conv = {
        "id": cid, "lead_id": lid, "ai_attiva": True, "stato": "ai_conversazione",
        "unread": 0, "operatore": None, "last_message": "", "last_message_at": now,
    }
    await db.conversations.insert_one(conv)
    await schedule_followups(lead)
    return lead, conv


async def whatsapp_send_typing(message_id: str):
    """Mostra 'Andrea sta scrivendo…' + segna il messaggio come letto (fino a ~25s)."""
    cfg = await get_wa_config()
    if not wa_is_configured(cfg) or not message_id:
        return
    url = f"https://graph.facebook.com/{META_API_VERSION}/{cfg['phone_number_id']}/messages"
    payload = {"messaging_product": "whatsapp", "status": "read",
               "message_id": message_id, "typing_indicator": {"type": "text"}}
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.post(url, headers={"Authorization": f"Bearer {cfg['token']}"}, json=payload)
        if r.is_error:
            logger.warning(f"WA typing error: {r.text}")
    except Exception as e:
        logger.warning(f"WA typing failed: {e}")


def typing_seconds(text: str) -> float:
    """Durata realistica del 'sta scrivendo…' in base alla lunghezza del messaggio.
    Breve → pochi secondi; medio → intermedio; lungo → più secondi (cap 12s per
    restare entro la finestra ~25s del typing indicator WhatsApp)."""
    n = len(text or "")
    secs = 1.8 + n / 20.0
    return max(2.0, min(12.0, secs))


async def handle_inbound_wa(m: dict, value: dict):
    wa_from = m.get("from")
    text = (m.get("text") or {}).get("body", "")
    if not text and m.get("interactive"):
        inter = m["interactive"]
        br = inter.get("button_reply") or inter.get("list_reply") or {}
        text = br.get("title", "")
    if not wa_from:
        return
    lead = await db.leads.find_one(
        {"telefono": {"$regex": wa_from[-9:]}}, {"_id": 0})
    conv = await db.conversations.find_one({"lead_id": lead["id"]}, {"_id": 0}) if lead else None
    if not lead or not conv:
        referral = m.get("referral") or {}
        if referral.get("source_id") or referral.get("source_type") == "ad":
            # Messaggio da annuncio (Click-to-WhatsApp): separa per prefisso SG-
            allowed, camp_name, ad_name, platform = await ctwa_ad_info(referral)
            if not allowed:
                logger.info(
                    f"WhatsApp da annuncio NON-SG ignorato (ad='{ad_name}', camp='{camp_name}', "
                    f"source_id={referral.get('source_id')}). Super Girl non interviene.")
                return  # campagne dell'agenzia: nessun intervento
            lead, conv = await create_inbound_lead(
                wa_from, value, campagna=camp_name or "Click-to-WhatsApp",
                inserzione=ad_name or "Annuncio", piattaforma=platform,
                origine="whatsapp_ad")
        else:
            # Contatto organico (nessun annuncio): comportamento standard
            lead, conv = await create_inbound_lead(wa_from, value)
    await db.messages.insert_one({
        "id": str(uuid.uuid4()), "conversation_id": conv["id"], "sender": "cliente",
        "text": text, "type": "text", "created_at": iso(now_utc()), "read": False,
        "wa_id": m.get("id")})
    await cancel_followups(lead["id"])
    await db.conversations.update_one({"id": conv["id"]}, {"$set": {
        "last_message": text, "last_message_at": iso(now_utc()),
        "unread": conv.get("unread", 0) + 1}})
    if not conv.get("ai_attiva", True):
        return
    # "Andrea sta scrivendo…" subito, prima di generare/inviare la risposta
    await whatsapp_send_typing(m.get("id"))
    loop = asyncio.get_event_loop()
    t0 = loop.time()
    is_corso = (lead.get("tipo") or "trattamento") == "corso"
    # CORSO: proposta/conferma slot chiamata (Academy Manager)
    if is_corso:
        handled, corso_reply, booked = await handle_corso_turn(conv, lead, text)
        if handled:
            await asyncio.sleep(typing_seconds(corso_reply))
            await db.messages.insert_one({
                "id": str(uuid.uuid4()), "conversation_id": conv["id"], "sender": "ai",
                "text": corso_reply, "type": "text", "created_at": iso(now_utc()), "read": True})
            await db.conversations.update_one({"id": conv["id"]}, {"$set": {
                "last_message": corso_reply, "last_message_at": iso(now_utc())}})
            if not booked:
                await db.conversations.update_one({"id": conv["id"]}, {"$set": {"stato": "in_attesa"}})
                await db.leads.update_one({"id": lead["id"]}, {"$set": {
                    "stato_pipeline": "in_attesa", "ultimo_contatto": iso(now_utc())}})
            await whatsapp_send_text(wa_from, corso_reply)
            return
        # nessuna preferenza rilevata → prosegue con la risposta AI Academy sotto

    # TRATTAMENTO: flusso deterministico approvato (prezzo / prenotazione / richiamo)
    if not is_corso:
        handled, tr_reply, keep_on, need_btn = await handle_trattamento_turn(conv, lead, text)
        if handled:
            await asyncio.sleep(typing_seconds(tr_reply))
            await db.messages.insert_one({
                "id": str(uuid.uuid4()), "conversation_id": conv["id"], "sender": "ai",
                "text": tr_reply, "type": "text", "created_at": iso(now_utc()), "read": True})
            await db.conversations.update_one({"id": conv["id"]}, {"$set": {
                "last_message": tr_reply, "last_message_at": iso(now_utc())}})
            if need_btn:
                await whatsapp_send_buttons(wa_from, tr_reply, [
                    {"id": "tratt_prezzo", "title": "Quanto costa?"},
                    {"id": "tratt_appuntamento", "title": "Fissare appuntamento"}])
            else:
                await whatsapp_send_text(wa_from, tr_reply)
            return

    # (solo CORSO senza preferenza) l'AI Academy genera la risposta
    reply = await ai_generate_reply(conv, lead)
    # L'AI non inventa: token di richiamo → passa allo staff con frase naturale
    fb_motivo, fb_phrase = detect_ai_fallback(reply)
    if fb_motivo:
        await asyncio.sleep(typing_seconds(fb_phrase))
        await do_handoff(lead, conv, fb_motivo, fb_phrase)
        await whatsapp_send_text(wa_from, fb_phrase)
        return
    # il "sta scrivendo…" resta attivo per un tempo proporzionale alla
    # risposta, scontando il tempo già speso a generarla
    elapsed = loop.time() - t0
    delay = max(0.0, typing_seconds(reply) - elapsed)
    if delay > 0:
        await asyncio.sleep(delay)
    await db.messages.insert_one({
        "id": str(uuid.uuid4()), "conversation_id": conv["id"], "sender": "ai",
        "text": reply, "type": "text", "created_at": iso(now_utc()), "read": True})
    await db.conversations.update_one({"id": conv["id"]}, {"$set": {
        "last_message": reply, "last_message_at": iso(now_utc()),
        "stato": "in_attesa"}})
    await db.leads.update_one({"id": lead["id"]}, {"$set": {
        "stato_pipeline": "in_attesa", "ultimo_contatto": iso(now_utc())}})
    await whatsapp_send_text(wa_from, reply)


class WaConfigInput(BaseModel):
    numero: Optional[str] = None
    phone_number_id: Optional[str] = None
    waba_id: Optional[str] = None
    token: Optional[str] = None
    app_secret: Optional[str] = None
    verify_token: Optional[str] = None
    template_name: Optional[str] = None
    template_language: Optional[str] = None


def _mask(v: Optional[str]) -> Optional[str]:
    if not v or v == "REPLACE_ME":
        return None
    return f"••••{v[-4:]}" if len(v) > 4 else "••••"


@api.get("/integrations/whatsapp/config")
async def wa_get_config(user: dict = Depends(require_admin)):
    cfg = await get_wa_config()
    return {
        "numero": cfg.get("numero") or "",
        "phone_number_id": cfg.get("phone_number_id") if cfg.get("phone_number_id") != "REPLACE_ME" else "",
        "waba_id": cfg.get("waba_id") if cfg.get("waba_id") != "REPLACE_ME" else "",
        "template_name": cfg.get("template_name"),
        "template_language": cfg.get("template_language"),
        "verify_token": cfg.get("verify_token"),
        "token_masked": _mask(cfg.get("token")),
        "app_secret_masked": _mask(cfg.get("app_secret")),
        "configured": wa_is_configured(cfg),
        "webhook_path": "/api/integrations/whatsapp/webhook",
    }


@api.patch("/integrations/whatsapp/config")
async def wa_set_config(body: WaConfigInput, user: dict = Depends(require_admin)):
    updates = {k: v for k, v in body.dict().items() if v is not None and v != ""}
    for k in ("verify_token", "phone_number_id", "waba_id", "token", "app_secret", "template_name", "template_language", "numero"):
        if k in updates and isinstance(updates[k], str):
            updates[k] = updates[k].strip()
    if updates:
        await db.integration_config.update_one(
            {"key": "whatsapp"}, {"$set": {**updates, "key": "whatsapp"}}, upsert=True)
    return await wa_get_config(user)


@api.get("/integrations/whatsapp/status")
async def wa_status(user: dict = Depends(current_user)):
    cfg = await get_wa_config()
    return {"configured": wa_is_configured(cfg),
            "numero": cfg.get("numero") or "",
            "template_name": cfg.get("template_name")}


# ---------------------------------------------------------------------------
# ASSISTENTE AI — profilo/avatar (Andrea), sostituibile da Admin
# ---------------------------------------------------------------------------
@api.get("/assistant")
async def get_assistant(user: dict = Depends(current_user)):
    doc = await db.integration_config.find_one({"key": "assistant"}, {"_id": 0}) or {}
    return {"name": doc.get("name") or ASSISTANT_NAME,
            "avatar_url": doc.get("avatar_url")}


@api.get("/assistant/public")
async def get_assistant_public():
    """Profilo assistente accessibile senza auth (per la schermata di login)."""
    doc = await db.integration_config.find_one({"key": "assistant"}, {"_id": 0}) or {}
    return {"name": doc.get("name") or ASSISTANT_NAME,
            "avatar_url": doc.get("avatar_url")}


class AssistantInput(BaseModel):
    name: Optional[str] = None
    avatar_url: Optional[str] = None


@api.patch("/assistant")
async def set_assistant(body: AssistantInput, user: dict = Depends(require_admin)):
    updates = {k: v for k, v in body.dict().items() if v is not None}
    if updates:
        await db.integration_config.update_one(
            {"key": "assistant"}, {"$set": {**updates, "key": "assistant"}}, upsert=True)
    return await get_assistant(user)


# ---------------------------------------------------------------------------
# NOTIFICHE
# ---------------------------------------------------------------------------
@api.get("/notifications")
async def list_notifications(user: dict = Depends(current_user)):
    notifs = await db.notifications.find({}, {"_id": 0}).sort(
        "created_at", -1).to_list(200)
    unread = sum(1 for n in notifs if not n["read"])
    return {"notifications": notifs, "unread": unread}


@api.post("/notifications/{nid}/read")
async def mark_read(nid: str, user: dict = Depends(current_user)):
    await db.notifications.update_one({"id": nid}, {"$set": {"read": True}})
    return {"ok": True}


@api.post("/notifications/read-all")
async def mark_all_read(user: dict = Depends(current_user)):
    await db.notifications.update_many({}, {"$set": {"read": True}})
    return {"ok": True}


# ---------------------------------------------------------------------------
# Meta / conf statiche
# ---------------------------------------------------------------------------
@api.get("/config/stages")
async def get_stages(user: dict = Depends(current_user)):
    return {"stages": PIPELINE_STAGES, "temperatures": TEMPERATURES}


@api.get("/")
async def root():
    return {"app": "SUPER GIRL API", "status": "ok", "version": "sg-ctwa-1"}


@api.get("/privacy", response_class=HTMLResponse)
async def privacy_policy():
    html = """<!DOCTYPE html>
<html lang="it"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Privacy Policy - J'adore Mimì</title>
<style>
body{font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;max-width:820px;margin:0 auto;padding:32px 20px;color:#1a1a1a;line-height:1.65}
h1{color:#111;font-size:26px} h2{color:#222;font-size:19px;margin-top:28px}
.brand{color:#B68D40;font-weight:700} a{color:#B68D40}
.muted{color:#666;font-size:13px}
</style></head><body>
<h1>Informativa sulla Privacy - <span class="brand">J'adore Mim&igrave;</span></h1>
<p class="muted">Ultimo aggiornamento: giugno 2026</p>

<p>La presente informativa descrive come <strong>J'adore Mim&igrave;</strong> ("noi") raccoglie e utilizza i dati personali degli utenti ("tu") quando interagisci con noi tramite WhatsApp e le nostre campagne pubblicitarie su Meta (Facebook e Instagram).</p>

<h2>1. Dati che raccogliamo</h2>
<ul>
<li>Nome e cognome, numero di telefono, indirizzo email (se forniti).</li>
<li>Contenuto dei messaggi scambiati su WhatsApp con il nostro numero aziendale.</li>
<li>Informazioni sul trattamento estetico di interesse, preferenze e appuntamenti.</li>
<li>Dati provenienti dai moduli pubblicitari (Lead Ads) di Meta, quando compilati volontariamente.</li>
</ul>

<h2>2. Come utilizziamo i dati</h2>
<ul>
<li>Per risponderti e assisterti tramite il nostro assistente su WhatsApp.</li>
<li>Per fornirti informazioni sui trattamenti e gestire le prenotazioni.</li>
<li>Per finalit&agrave; di assistenza clienti e per migliorare il nostro servizio.</li>
</ul>

<h2>3. Base giuridica e consenso</h2>
<p>Trattiamo i tuoi dati sulla base del consenso che fornisci scrivendoci o compilando i nostri moduli, e per l'esecuzione delle attivit&agrave; richieste. Puoi revocare il consenso in qualsiasi momento.</p>

<h2>4. Condivisione dei dati</h2>
<p>I dati sono trattati tramite l'API ufficiale di WhatsApp Business (Meta Platforms Ireland Ltd.) esclusivamente per consentire la comunicazione. Non vendiamo i tuoi dati a terzi.</p>

<h2>5. Conservazione</h2>
<p>Conserviamo i dati per il tempo necessario a fornirti il servizio e adempiere agli obblighi di legge, dopodich&eacute; vengono cancellati o resi anonimi.</p>

<h2>6. I tuoi diritti</h2>
<p>Hai diritto di accedere, rettificare, cancellare i tuoi dati e opporti al trattamento. Per esercitarli scrivici al nostro numero WhatsApp o all'indirizzo email di contatto.</p>

<h2>7. Contatti</h2>
<p><span class="brand">J'adore Mim&igrave;</span><br>
WhatsApp: +39 393 470 6525</p>

<p class="muted">Questa informativa pu&ograve; essere aggiornata periodicamente. Continuando a interagire con noi accetti la versione pi&ugrave; recente.</p>
</body></html>"""
    return HTMLResponse(content=html)


app.include_router(api)
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup():
    from seed_data import seed_database
    await seed_database(db)
    asyncio.create_task(followup_worker())
    asyncio.create_task(call_reminder_worker())


@app.on_event("shutdown")
async def shutdown():
    client.close()
