"""SUPER GIRL — CRM conversazionale (Fase 1: Demo).

Backend FastAPI + MongoDB. Tutta la logica AI e le transizioni di stato vivono
qui, dietro funzioni controllate, così la Fase 4 (AI reale) potrà sostituire
l'implementazione interna senza toccare frontend o schema.
"""
import os
import uuid
import hmac
import hashlib
import logging
from pathlib import Path
from datetime import datetime, timedelta, timezone
from typing import List, Optional

import jwt
import bcrypt
import httpx
from fastapi import FastAPI, APIRouter, Depends, HTTPException, status, Query, Request
from fastapi.responses import PlainTextResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
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
GRAPH = f"https://graph.facebook.com/{META_API_VERSION}"


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
    {"key": "da_fissare", "label": "DA FISSARE APPUNTAMENTO", "order": 5,
     "desc": "Il cliente vuole prenotare e deve essere contattato dallo staff."},
    {"key": "appuntamento_fissato", "label": "APPUNTAMENTO FISSATO", "order": 6,
     "desc": "Lo staff ha fissato manualmente l'appuntamento."},
    {"key": "non_interessata", "label": "NON INTERESSATA", "order": 7,
     "desc": "Cliente che dichiara di non essere interessata."},
    {"key": "persa", "label": "PERSA / NON RISPONDE", "order": 8,
     "desc": "Cliente che non risponde dopo i follow-up previsti."},
]
STAGE_LABELS = {s["key"]: s["label"] for s in PIPELINE_STAGES}

TEMPERATURES = [
    {"key": "molto_calda", "label": "Molto Calda"},
    {"key": "interessata", "label": "Interessata"},
    {"key": "da_coltivare", "label": "Da Coltivare"},
    {"key": "non_qualificata", "label": "Non Qualificata"},
]


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
                "Che bello! 😊 Ti metto subito in contatto con una nostra "
                "specialista che ti ricontatterà a brevissimo per fissare "
                "l'appuntamento nel giorno che preferisci. A prestissimo! 💛")
    if any(k in low for k in HUMAN_KEYWORDS):
        return ("richiesta_operatore",
                "Certo! Passo subito la conversazione a una nostra collega che "
                "ti ricontatterà personalmente. 💛")
    if any(k in low for k in ANGER_KEYWORDS):
        return ("situazione_delicata",
                "Mi dispiace molto. Faccio intervenire subito una nostra "
                "responsabile che si prenderà cura di te. 💛")
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
    new_status = "da_fissare"
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
    clean_msg = {k: v for k, v in msg.items() if k != "_id"}
    return clean_msg, summary


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
        query["stato"] = "da_fissare"
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

    # Rileva handoff
    if last_customer:
        motivo, ai_message = detect_handoff(last_customer["text"])
        if motivo:
            reply, summary = await do_handoff(lead, conv, motivo, ai_message)
            return {"message": reply, "handoff": True, "motivo": motivo,
                    "summary": summary, "new_status": "da_fissare"}

    # Altrimenti: prosegue la qualificazione (una domanda alla volta)
    ai_turns = len([m for m in msgs if m["sender"] == "ai"])
    reply_text = AI_QUALIFY_STEPS[min(ai_turns, len(AI_QUALIFY_STEPS) - 1)]
    msg = {
        "id": str(uuid.uuid4()),
        "conversation_id": conv_id,
        "sender": "ai",
        "text": reply_text,
        "created_at": iso(now_utc()),
        "read": True,
    }
    await db.messages.insert_one(msg)
    # aggiorna stato: AI in conversazione -> in attesa cliente + scalda il lead
    new_status = "in_attesa"
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
                     user: dict = Depends(current_user)):
    query: dict = {}
    if stato:
        query["stato_pipeline"] = stato
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


@api.patch("/leads/{lead_id}")
async def update_lead(lead_id: str, body: LeadUpdate,
                      user: dict = Depends(current_user)):
    lead = await db.leads.find_one({"id": lead_id}, {"_id": 0})
    if not lead:
        raise HTTPException(404, "Cliente non trovato")
    updates = {k: v for k, v in body.dict().items() if v is not None}
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
    if body.stato == "da_fissare":
        updates["handoff_at"] = iso(now_utc())
    await db.leads.update_one({"id": lead_id}, {"$set": updates})
    await db.conversations.update_one({"lead_id": lead_id},
                                      {"$set": {"stato": body.stato}})
    if from_status != body.stato:
        await record_status_change(lead, from_status, body.stato, "staff")
        if body.stato == "da_fissare":
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
        {"stato_pipeline": "da_fissare"}, {"_id": 0}).to_list(200)

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
            "conversation_id": conv["id"] if conv else None,
        })
    total = await db.leads.count_documents({})
    return {"da_fissare": out, "total_leads": total, "count": len(out)}


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

    interessate = count("interessata") + count("da_fissare") + count("appuntamento_fissato")
    da_fissare = count("da_fissare")
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
        if l["stato_pipeline"] == "da_fissare":
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
    rules = await db.followup_rules.find_one({}, {"_id": 0})
    return rules or {}


class FollowupRules(BaseModel):
    enabled: bool = True
    steps: list = []


@api.patch("/followups")
async def update_followup_rules(body: FollowupRules,
                                user: dict = Depends(require_admin)):
    await db.followup_rules.update_one({}, {"$set": body.dict()}, upsert=True)
    return await db.followup_rules.find_one({}, {"_id": 0})


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
    return {
        "meta": {"name": "Meta Lead Ads", "status": meta_status, "phase": "Fase 2",
                 "configured": meta_configured()},
        "whatsapp": {"name": "WhatsApp Business Cloud API", "status": "non_attivo",
                     "phase": "Fase 3", "configured": False},
        "ai": {"name": "AI Provider", "status": "non_attivo", "phase": "Fase 4",
               "configured": False},
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
        "leadgen_id": leadgen_id, "origine": "meta",
    }
    await db.leads.insert_one(lead)

    greeting = (
        f"Ciao {nome}! 😊 Grazie per aver risposto alla nostra pubblicità"
        + (f" \"{campagna}\"" if campagna else "")
        + ". Sono l'assistente di SUPER GIRL. Posso farti qualche domanda per "
          "aiutarti al meglio?"
    )
    await db.conversations.insert_one({
        "id": cid, "lead_id": lid, "ai_attiva": True, "stato": "nuovo_lead",
        "unread": 0, "operatore": None, "last_message": greeting,
        "last_message_at": now,
    })
    await db.messages.insert_one({
        "id": str(uuid.uuid4()), "conversation_id": cid, "sender": "ai",
        "text": greeting, "created_at": now, "read": True,
    })
    await db.lead_status_history.insert_one({
        "id": str(uuid.uuid4()), "lead_id": lid, "from_status": None,
        "to_status": "nuovo_lead", "changed_by": "meta", "created_at": now,
    })
    await db.followups.insert_one({
        "id": str(uuid.uuid4()), "lead_id": lid, "label": "Follow-up 1",
        "delay": "2 ore", "status": "programmato", "created_at": now,
        "updated_at": now,
    })
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


async def retrieve_and_ingest(leadgen_id: str, event: dict):
    """Recupera i dati completi del lead da Graph API e li ingesta."""
    lead = await graph_get(
        leadgen_id,
        "id,created_time,form_id,ad_id,adset_id,campaign_id,field_data")
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
    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            if change.get("field") != "leadgen":
                continue
            value = change.get("value", {})
            leadgen_id = value.get("leadgen_id")
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
    }


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
    return {"app": "SUPER GIRL API", "status": "ok"}


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


@app.on_event("shutdown")
async def shutdown():
    client.close()
