"""Fase 2 - Meta Lead Ads integration tests (webhook verify, webhook POST,
status, integrations, simulate flow, idempotency, RBAC)."""
import os
import time
import uuid
import pytest
import requests

BASE_URL = os.environ["EXPO_PUBLIC_BACKEND_URL"].rstrip("/")
VERIFY_TOKEN = "sg_meta_verify_7bxq2f9K4mLp8dRt3wZv6yA1cE5nH0sJ"


# ---------- WEBHOOK VERIFY (GET) ----------
class TestMetaWebhookVerify:
    def test_verify_ok(self, api_client):
        r = api_client.get(
            f"{BASE_URL}/api/integrations/meta/webhook",
            params={"hub.mode": "subscribe",
                    "hub.verify_token": VERIFY_TOKEN,
                    "hub.challenge": "XYZ"})
        assert r.status_code == 200, r.text
        assert r.text == "XYZ"

    def test_verify_wrong_token_403(self, api_client):
        r = api_client.get(
            f"{BASE_URL}/api/integrations/meta/webhook",
            params={"hub.mode": "subscribe",
                    "hub.verify_token": "WRONG_TOKEN",
                    "hub.challenge": "XYZ"})
        assert r.status_code == 403

    def test_verify_missing_mode_403(self, api_client):
        r = api_client.get(
            f"{BASE_URL}/api/integrations/meta/webhook",
            params={"hub.verify_token": VERIFY_TOKEN,
                    "hub.challenge": "XYZ"})
        assert r.status_code == 403


# ---------- WEBHOOK POST ----------
class TestMetaWebhookPost:
    def test_object_not_page_returns_ok(self, api_client):
        r = api_client.post(
            f"{BASE_URL}/api/integrations/meta/webhook",
            json={"object": "instagram", "entry": []})
        assert r.status_code == 200
        assert r.json() == {"ok": True}

    def test_missing_signature_no_crash_placeholder_secret(self, api_client):
        # APP_SECRET is placeholder -> signature check skipped -> 200 ok,
        # meta_configured()=false -> retrieve_and_ingest NOT called.
        unique = f"webhook-{uuid.uuid4()}"
        r = api_client.post(
            f"{BASE_URL}/api/integrations/meta/webhook",
            json={
                "object": "page",
                "entry": [{"changes": [
                    {"field": "leadgen",
                     "value": {"leadgen_id": unique}}
                ]}]
            })
        assert r.status_code == 200
        assert r.json() == {"ok": True}
        # verify no lead exists with that leadgen_id (webhook should not
        # ingest while meta_configured() is False)
        hdr = {"Authorization": f"Bearer {_admin_token()}"}
        leads = api_client.get(f"{BASE_URL}/api/leads", headers=hdr).json()
        assert not any(l.get("leadgen_id") == unique for l in leads)


# ---------- STATUS + INTEGRATIONS ----------
class TestMetaStatus:
    def test_admin_status(self, api_client, admin_headers):
        r = api_client.get(f"{BASE_URL}/api/integrations/meta/status",
                           headers=admin_headers)
        assert r.status_code == 200
        d = r.json()
        assert d["configured"] is False
        assert d["verify_token"] == VERIFY_TOKEN
        assert d["subscribe_field"] == "leadgen"
        assert d["webhook_path"] == "/api/integrations/meta/webhook"

    def test_operator_status_no_verify_token(self, api_client, operator_headers):
        r = api_client.get(f"{BASE_URL}/api/integrations/meta/status",
                           headers=operator_headers)
        assert r.status_code == 200
        d = r.json()
        assert d["configured"] is False
        assert d["verify_token"] is None

    def test_integrations_meta_non_attivo(self, api_client, admin_headers):
        r = api_client.get(f"{BASE_URL}/api/integrations", headers=admin_headers)
        assert r.status_code == 200
        meta = r.json()["meta"]
        assert meta["status"] == "non_attivo"
        assert meta["configured"] is False


# ---------- SIMULATE (main Fase 2 flow) ----------
class TestMetaSimulate:
    def test_simulate_creates_full_flow(self, api_client, admin_headers):
        payload = {
            "nome": "TEST_Marta", "cognome": "Rossi",
            "telefono": "+390000000000", "email": "TEST_marta@example.com",
            "servizio": "TEST_ServizioX", "sede": "TEST_SedeX",
            "campagna": "TEST_CampagnaFase2", "inserzione": "TEST_Creative1",
            "piattaforma": "Instagram", "ig_username": "test_marta_ig",
        }
        r = api_client.post(f"{BASE_URL}/api/integrations/meta/simulate",
                            headers=admin_headers, json=payload)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d.get("duplicate") is False
        lead = d["lead"]
        conv_id = d["conversation_id"]
        assert lead["stato_pipeline"] == "nuovo_lead"
        assert lead["origine"] == "meta"
        assert lead["nome"] == "TEST_Marta"
        assert lead["campagna"] == "TEST_CampagnaFase2"
        assert lead["piattaforma"] == "Instagram"

        # conversation created with ai_attiva=true and AI greeting message
        conv = api_client.get(f"{BASE_URL}/api/conversations/{conv_id}",
                              headers=admin_headers).json()
        assert conv["conversation"]["ai_attiva"] is True
        assert conv["conversation"]["stato"] == "nuovo_lead"
        assert len(conv["messages"]) >= 1
        first = conv["messages"][0]
        assert first["sender"] == "ai"
        assert "TEST_Marta" in first["text"]

        # lead appears in /leads?stato=nuovo_lead
        r2 = api_client.get(f"{BASE_URL}/api/leads?stato=nuovo_lead",
                            headers=admin_headers)
        assert r2.status_code == 200
        assert any(l["id"] == lead["id"] for l in r2.json())

        # lead appears in pipeline column nuovo_lead
        pipe = api_client.get(f"{BASE_URL}/api/pipeline",
                              headers=admin_headers).json()
        nuovo_col = next(s for s in pipe if s["key"] == "nuovo_lead")
        assert any(l["id"] == lead["id"] for l in nuovo_col["leads"])

        # campaign auto-created / associated
        camps = api_client.get(f"{BASE_URL}/api/campaigns",
                               headers=admin_headers).json()
        camp = next((c for c in camps if c["nome"] == "TEST_CampagnaFase2"),
                    None)
        assert camp is not None
        assert "TEST_Creative1" in (camp.get("inserzioni") or [])

        # notification nuova_chat created
        notifs = api_client.get(f"{BASE_URL}/api/notifications",
                                headers=admin_headers).json()["notifications"]
        assert any(n["tipo"] == "nuova_chat" and n.get("lead_id") == lead["id"]
                   for n in notifs)

    def test_idempotency_same_leadgen_id(self, api_client, admin_headers):
        leadgen_id = f"TEST_leadgen_{uuid.uuid4()}"
        payload = {"nome": "TEST_Idempo", "leadgen_id": leadgen_id,
                   "campagna": "TEST_CampIdemp"}
        r1 = api_client.post(f"{BASE_URL}/api/integrations/meta/simulate",
                             headers=admin_headers, json=payload)
        assert r1.status_code == 200
        assert r1.json()["duplicate"] is False
        first_lead_id = r1.json()["lead"]["id"]

        r2 = api_client.post(f"{BASE_URL}/api/integrations/meta/simulate",
                             headers=admin_headers, json=payload)
        assert r2.status_code == 200
        d2 = r2.json()
        assert d2["duplicate"] is True
        assert d2["lead"]["id"] == first_lead_id

    def test_rbac_operator_cannot_simulate(self, api_client, operator_headers):
        r = api_client.post(f"{BASE_URL}/api/integrations/meta/simulate",
                            headers=operator_headers,
                            json={"nome": "TEST_Blocked"})
        assert r.status_code == 403


# ---------- REGRESSIONE FASE 1 ----------
class TestFase1Regression:
    def test_admin_login(self, api_client):
        r = api_client.post(f"{BASE_URL}/api/auth/login",
                            json={"email": "admin@supergirl.app",
                                  "password": "Admin123!"})
        assert r.status_code == 200

    def test_operator_login(self, api_client):
        r = api_client.post(f"{BASE_URL}/api/auth/login",
                            json={"email": "operatore@supergirl.app",
                                  "password": "Operatore123!"})
        assert r.status_code == 200

    def test_home_priorities(self, api_client, admin_headers):
        r = api_client.get(f"{BASE_URL}/api/home/priorities",
                           headers=admin_headers)
        assert r.status_code == 200
        assert "da_fissare" in r.json()

    def test_ai_handoff_still_works(self, api_client, admin_headers):
        convs = api_client.get(f"{BASE_URL}/api/conversations?filter=ai",
                               headers=admin_headers).json()
        # pick middle to avoid clashes with parallel simulate tests picking
        # newly-created (front-of-list) conversations
        ai_convs = [c for c in convs if c.get("ai_attiva")]
        if not ai_convs:
            pytest.skip("no ai_attiva conversation available")
        cid = ai_convs[len(ai_convs) // 2]["id"]
        api_client.post(
            f"{BASE_URL}/api/conversations/{cid}/simulate-customer",
            headers=admin_headers,
            json={"text": "Vorrei prenotare un appuntamento"})
        r = api_client.post(
            f"{BASE_URL}/api/conversations/{cid}/simulate-ai-turn",
            headers=admin_headers, json={})
        assert r.status_code == 200
        d = r.json()
        assert d["handoff"] is True
        assert d["new_status"] == "da_fissare"

    def test_analytics(self, api_client, admin_headers):
        r = api_client.get(f"{BASE_URL}/api/analytics?period=30d",
                           headers=admin_headers)
        assert r.status_code == 200
        for k in ("nuovi_lead", "funnel", "by_campaign"):
            assert k in r.json()


# ---------- helper (module-level) ----------
def _admin_token():
    r = requests.post(f"{BASE_URL}/api/auth/login",
                      json={"email": "admin@supergirl.app",
                            "password": "Admin123!"})
    r.raise_for_status()
    return r.json()["access_token"]
