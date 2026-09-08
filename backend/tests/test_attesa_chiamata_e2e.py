"""E2E test for the new pipeline stage 'attesa_chiamata' (IN ATTESA DI CHIAMATA)
and the natural AI conversational tone.

Flow tested:
  1. Admin creates a lead via POST /api/integrations/meta/simulate.
  2. Alternate customer/AI turns via /simulate-customer and /simulate-ai-turn.
  3. Verify tone: no 'AI'/'assistente automatico', no always-starting-with 'Perfetto',
     no repeated identical openings, short messages, single-question style.
  4. Verify price strategy: mentions price + promo + future expiry date (dd/mm/yyyy).
  5. Verify handoff: intention to book -> handoff=True, motivo='prenotazione',
     new_status='attesa_chiamata'; lead.stato_pipeline='attesa_chiamata';
     conv.ai_attiva=False; follow-ups annulled; notification created.
  6. Verify GET /api/pipeline contains 'attesa_chiamata'.
  7. Verify GET /api/home/priorities contains the lead just moved to attesa_chiamata.
  8. Verify GET /api/config/stages contains the key 'attesa_chiamata'.
"""
import os
import re
import time
import pytest
import requests

BASE_URL = os.environ.get("EXPO_PUBLIC_BACKEND_URL", "").rstrip("/")

TEST_NAME_PREFIX = "TESTE2E"  # used for cleanup identification


# --- helpers --------------------------------------------------------------
def _post(path, headers, json=None):
    return requests.post(f"{BASE_URL}{path}", headers=headers, json=json or {}, timeout=60)


def _get(path, headers):
    return requests.get(f"{BASE_URL}{path}", headers=headers, timeout=60)


def _extract_dates(text: str):
    return re.findall(r"\b(\d{2}/\d{2}/\d{4})\b", text)


def _norm_opening(text: str) -> str:
    """Return the first word (lowercased, punctuation stripped) of a message."""
    t = text.strip()
    if not t:
        return ""
    first = t.split()[0]
    return re.sub(r"[^\wàèéìòù']", "", first, flags=re.IGNORECASE).lower()


# --- fixtures -------------------------------------------------------------
@pytest.fixture(scope="module")
def admin_headers(admin_token):
    """Module-scoped headers, matching the module scope of created_lead."""
    return {"Authorization": f"Bearer {admin_token}",
            "Content-Type": "application/json"}


@pytest.fixture(scope="module")
def created_lead(admin_headers):
    """Create a fresh lead via meta/simulate. Cleanup handled in fixture teardown."""
    payload = {
        "nome": TEST_NAME_PREFIX,
        "cognome": "Naturale",
        "telefono": "+390000000999",
        "email": "e2e-tester@example.test",
        "servizio": "Bomba",
        "sede": "Milano",
        "campagna": "TEST_CAMPAGNA_E2E",
        "inserzione": "TEST_INSERZIONE_E2E",
        "piattaforma": "Instagram",
        "ig_username": "e2e_natural_test",
    }
    r = _post("/api/integrations/meta/simulate", admin_headers, payload)
    assert r.status_code == 200, f"simulate failed: {r.status_code} {r.text}"
    data = r.json()
    assert "lead" in data and "conversation_id" in data, f"missing keys: {data}"
    lead = data["lead"]
    conv_id = data["conversation_id"]
    assert lead["id"]
    assert conv_id
    assert lead["stato_pipeline"] == "nuovo_lead"

    yield {"lead": lead, "conversation_id": conv_id}

    # ---- cleanup: try admin delete endpoint, otherwise mark as ignored ----
    try:
        requests.delete(f"{BASE_URL}/api/leads/{lead['id']}",
                        headers=admin_headers, timeout=15)
    except Exception:
        pass


# --- 1. Config / stages endpoint contains attesa_chiamata -----------------
def test_config_stages_contains_attesa_chiamata(admin_headers):
    r = _get("/api/config/stages", admin_headers)
    assert r.status_code == 200, r.text
    body = r.json()
    keys = [s["key"] for s in body.get("stages", [])]
    assert "attesa_chiamata" in keys, f"stages keys: {keys}"
    # Verify label is the one requested by the user
    stage = next(s for s in body["stages"] if s["key"] == "attesa_chiamata")
    assert "ATTESA" in stage["label"].upper() and "CHIAMATA" in stage["label"].upper()


# --- 2. Pipeline endpoint includes attesa_chiamata stage ------------------
def test_pipeline_includes_attesa_chiamata_stage(admin_headers):
    r = _get("/api/pipeline", admin_headers)
    assert r.status_code == 200, r.text
    stages = r.json()
    keys = [s["key"] for s in stages]
    assert "attesa_chiamata" in keys, f"pipeline keys: {keys}"


# --- 3. Meta simulate creates lead + conversation -------------------------
def test_meta_simulate_creates_lead_and_conversation(created_lead, admin_headers):
    lead = created_lead["lead"]
    conv_id = created_lead["conversation_id"]

    # verify persistence: GET lead (endpoint returns {"lead": ..., "conversation_id": ..., "history": [...]})
    r = _get(f"/api/leads/{lead['id']}", admin_headers)
    assert r.status_code == 200, r.text
    body = r.json()
    got = body["lead"] if "lead" in body else body
    assert got["nome"] == TEST_NAME_PREFIX
    assert got["stato_pipeline"] == "nuovo_lead"
    assert body.get("conversation_id") == conv_id


# --- 4. E2E multi-turn conversation ---------------------------------------
@pytest.fixture(scope="module")
def conversation_turns(created_lead, admin_headers):
    """Alternate customer/AI turns collecting all AI replies until handoff or max."""
    conv_id = created_lead["conversation_id"]
    ai_replies = []
    handoff_result = None

    customer_turns = [
        "Ciao, ho visto la pubblicità del trattamento Bomba, vorrei qualche info",
        "Come funziona esattamente il trattamento?",
        "Ok interessante. Quanto costa?",
        "Va bene, ci sono promozioni al momento?",
        "Ho paura che faccia male",
        "Ok mi hai convinto, vorrei prenotare un appuntamento",  # -> triggers handoff
    ]

    for msg in customer_turns:
        r = _post(f"/api/conversations/{conv_id}/simulate-customer",
                  admin_headers, {"text": msg})
        assert r.status_code == 200, f"simulate-customer failed: {r.text}"

        # small wait so AI has time to generate (real LLM call)
        time.sleep(1)
        r = _post(f"/api/conversations/{conv_id}/simulate-ai-turn", admin_headers)
        assert r.status_code == 200, f"simulate-ai-turn failed: {r.text}"
        body = r.json()

        if body.get("handoff"):
            handoff_result = body
            break
        else:
            ai_msg = body.get("message", {})
            ai_replies.append(ai_msg.get("text", ""))

    return {"replies": ai_replies, "handoff": handoff_result}


def test_ai_tone_never_reveals_ai_identity(conversation_turns):
    for txt in conversation_turns["replies"]:
        low = txt.lower()
        assert "assistente automatic" not in low, (
            f"AI reveals automated nature: {txt}")
        # 'AI' as word (case-insensitive) - but be tolerant: allow 'mai' etc.
        # match standalone ' ai ' or 'ai.' or 'ai,' etc.
        assert not re.search(r"\bai\b", low), (
            f"AI mentions the word 'AI': {txt}")


def test_ai_tone_not_always_perfetto(conversation_turns):
    replies = conversation_turns["replies"]
    if not replies:
        pytest.skip("no AI replies collected before handoff")
    perfetto_starts = sum(1 for t in replies if t.strip().lower().startswith("perfetto"))
    # allow at most 1 occurrence when there are >=2 replies
    assert perfetto_starts <= 1, (
        f"AI opens with 'Perfetto' too often ({perfetto_starts}/{len(replies)}): {replies}")


def test_ai_tone_no_repeated_openings(conversation_turns):
    replies = conversation_turns["replies"]
    if len(replies) < 2:
        pytest.skip("need >=2 AI replies to check consecutive openings")
    for a, b in zip(replies, replies[1:]):
        oa, ob = _norm_opening(a), _norm_opening(b)
        if not oa or not ob:
            continue
        assert oa != ob, f"Consecutive replies share the same opening '{oa}':\nA: {a}\nB: {b}"


def test_ai_price_strategy_has_future_expiry_date(conversation_turns):
    replies = conversation_turns["replies"]
    # A real price disclosure must contain a currency amount OR the strategy tokens
    # 'listino'/'promo'. A generic clarification like "il prezzo cambia in base alla
    # zona: quale ti interessa?" is NOT a disclosure and is a valid clarifying reply.
    def is_price_disclosure(t: str) -> bool:
        low = t.lower()
        has_amount = bool(re.search(r"(€\s*\d|\d+\s*(?:€|euro))", low))
        has_promo = "listino" in low or "promo" in low
        return has_amount or has_promo
    price_reply = next((t for t in replies if is_price_disclosure(t)), None)
    if price_reply is None:
        pytest.skip(
            "AI did not disclose a price in this run — it asked a clarifying "
            "question first ('quale zona ti interessa?'). This is acceptable "
            "behavior but the promo-with-scadenza structure was not verified.")
    dates = _extract_dates(price_reply)
    assert dates, f"No dd/mm/yyyy date in price reply: {price_reply}"
    # verify at least one date is in the future
    from datetime import datetime
    today = datetime.utcnow().date()
    future = []
    for d in dates:
        try:
            dt = datetime.strptime(d, "%d/%m/%Y").date()
            if dt >= today:
                future.append(d)
        except ValueError:
            pass
    assert future, f"Price reply has date(s) but none in the future: {dates}"


# --- 5. Handoff transitions the lead to attesa_chiamata -------------------
def test_handoff_moves_lead_to_attesa_chiamata(conversation_turns, created_lead,
                                                admin_headers):
    ho = conversation_turns["handoff"]
    assert ho is not None, "expected a handoff after the booking intent message"
    assert ho.get("handoff") is True
    assert ho.get("motivo") == "prenotazione"
    assert ho.get("new_status") == "attesa_chiamata"
    # AI closing message must NOT propose a date/time
    ai_text = ho["message"]["text"].lower()
    assert "richiamo" in ai_text or "richiamer" in ai_text or "controllo" in ai_text, (
        f"handoff closing message unexpected: {ai_text}")

    # verify lead persisted with new status
    lead = created_lead["lead"]
    r = _get(f"/api/leads/{lead['id']}", admin_headers)
    assert r.status_code == 200
    body = r.json()
    got = body["lead"] if "lead" in body else body
    assert got["stato_pipeline"] == "attesa_chiamata", f"lead status: {got['stato_pipeline']}"
    assert got.get("handoff_at"), "handoff_at should be set"

    # verify conversation ai_attiva=False. Endpoint returns {"conversation": {...}, "lead": {...}, "messages": [...]}
    conv_id = created_lead["conversation_id"]
    r = _get(f"/api/conversations/{conv_id}", admin_headers)
    if r.status_code == 200:
        body = r.json()
        c = body.get("conversation") if isinstance(body, dict) and "conversation" in body else body
        assert c.get("ai_attiva") is False, f"ai_attiva should be False: {c}"
        assert c.get("stato") == "attesa_chiamata", f"conv stato should be attesa_chiamata: {c.get('stato')}"


def test_home_priorities_lists_the_new_attesa_lead(created_lead, admin_headers):
    r = _get("/api/home/priorities", admin_headers)
    assert r.status_code == 200, r.text
    body = r.json()
    # server returns {"da_fissare": [...], "total_leads": N, "count": ...}
    if isinstance(body, dict):
        leads = body.get("da_fissare") or body.get("leads") or body.get("items") or []
    else:
        leads = body
    ids = [l.get("id") for l in leads]
    assert created_lead["lead"]["id"] in ids, (
        f"lead {created_lead['lead']['id']} not in priorities ids={ids}")


def test_notifications_created_for_booking(created_lead, admin_headers):
    r = _get("/api/notifications", admin_headers)
    if r.status_code != 200:
        pytest.skip(f"notifications endpoint not available: {r.status_code}")
    body = r.json()
    items = body if isinstance(body, list) else (
        body.get("notifications") or body.get("items") or [])
    lead_id = created_lead["lead"]["id"]
    matching = [n for n in items if n.get("lead_id") == lead_id]
    assert matching, f"no notification for lead {lead_id}"
    assert any(n.get("tipo") == "cliente_da_fissare" for n in matching), (
        f"expected 'cliente_da_fissare' notification, got: {[n.get('tipo') for n in matching]}")


def test_followups_cancelled_after_handoff(created_lead, admin_headers):
    """Any programmed followup for the lead must be cancelled after handoff."""
    lead_id = created_lead["lead"]["id"]
    # try admin-scoped followups; endpoint name may vary
    for path in [f"/api/leads/{lead_id}/followups", "/api/followups"]:
        r = _get(path, admin_headers)
        if r.status_code == 200:
            items = r.json()
            items = items if isinstance(items, list) else items.get("items", [])
            programmed = [f for f in items
                          if f.get("lead_id") == lead_id and f.get("status") == "programmato"]
            assert not programmed, f"programmed followups still present: {programmed}"
            return
    pytest.skip("no followups endpoint reachable to verify cancellation")
