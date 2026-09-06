"""Fase 3 tests: AI reale (GPT-5.4), Object Storage, Service image,
Primo messaggio con foto, WhatsApp config editabile, Webhook, Integrations status."""
import os
import io
import time
import uuid
import pytest
import requests

BASE_URL = os.environ["EXPO_PUBLIC_BACKEND_URL"].rstrip("/")
WA_VERIFY_TOKEN = "sg_wa_verify_3pKmZ9xQ7vLt2bRf5wYa8cE1nH4sJ6dG"


# 1x1 JPEG bytes (minimal valid)
JPEG_BYTES = bytes.fromhex(
    "ffd8ffe000104a46494600010100000100010000ffdb004300080606"
    "070605080707070909080a0c140d0c0b0b0c1912130f141d1a1f1e1d"
    "1a1c1c20242e2720222c231c1c2837292c30313434341f27393d3832"
    "3c2e333432ffc0000b080001000101011100ffc4001f000001050101"
    "0101010100000000000000000102030405060708090a0bffc400b510"
    "0002010303020403050504040000017d01020300041105122131410613"
    "516107227114328191a1082342b1c11552d1f02433627282090a1617"
    "1819"
) + b"\xff\xd9"


class TestUploadRBAC:
    def test_operator_upload_forbidden(self, api_client, operator_headers):
        h = {"Authorization": operator_headers["Authorization"]}
        r = api_client.post(f"{BASE_URL}/api/upload", headers=h,
                            files={"file": ("t.jpg", JPEG_BYTES, "image/jpeg")})
        assert r.status_code == 403


class TestUploadAndServe:
    def test_upload_and_serve(self, admin_headers):
        # use a fresh session (avoid session-level Content-Type: application/json)
        h = {"Authorization": admin_headers["Authorization"]}
        r = requests.post(f"{BASE_URL}/api/upload", headers=h,
                          files={"file": ("test.jpg", JPEG_BYTES, "image/jpeg")})
        assert r.status_code == 200, r.text
        d = r.json()
        assert "path" in d and d["url"].startswith("/api/files/")
        pytest.upload_url = d["url"]
        pytest.upload_path = d["path"]

        # serve
        r2 = requests.get(f"{BASE_URL}{d['url']}")
        assert r2.status_code == 200
        assert r2.headers.get("content-type", "").startswith("image/")
        assert len(r2.content) > 0


class TestServicesAndImage:
    def test_five_services_present(self, api_client, admin_headers):
        r = api_client.get(f"{BASE_URL}/api/services", headers=admin_headers)
        assert r.status_code == 200
        svcs = r.json()
        names = {s["nome"] for s in svcs}
        for n in ["Bomba", "Model Leg", "Lifting Colombiano", "Fire Cupping", "Bambolona"]:
            assert n in names, f"missing service {n}"
        # immagine field exists
        assert all("immagine" in s for s in svcs)

    def test_patch_service_immagine(self, api_client, admin_headers):
        svcs = api_client.get(f"{BASE_URL}/api/services",
                              headers=admin_headers).json()
        bomba = next(s for s in svcs if s["nome"] == "Bomba")
        img_url = getattr(pytest, "upload_url", "/api/files/dummy/path.jpg")
        body = {**{k: bomba.get(k, "") for k in
                   ["nome", "descrizione", "prezzo", "promozione", "info", "faq"]},
                "immagine": img_url}
        r = api_client.patch(f"{BASE_URL}/api/services/{bomba['id']}",
                             headers=admin_headers, json=body)
        assert r.status_code == 200
        assert r.json()["immagine"] == img_url


class TestFirstMessageWithPhoto:
    def test_simulate_bomba_creates_image_then_text(self, api_client, admin_headers):
        payload = {"nome": f"TEST_Foto_{uuid.uuid4().hex[:6]}",
                   "cognome": "Test", "telefono": "+390000000001",
                   "servizio": "Bomba", "sede": "Milano Centro",
                   "campagna": "TEST_Fase3", "inserzione": "Foto"}
        r = api_client.post(f"{BASE_URL}/api/integrations/meta/simulate",
                            headers=admin_headers, json=payload)
        assert r.status_code == 200, r.text
        cid = r.json()["conversation_id"]
        conv = api_client.get(f"{BASE_URL}/api/conversations/{cid}",
                              headers=admin_headers).json()
        msgs = conv["messages"]
        assert len(msgs) >= 2
        # first is image, second is greeting text
        assert msgs[0].get("type") == "image"
        assert msgs[0].get("media_url")
        assert msgs[1].get("type", "text") == "text"
        # greeting must contain Andrea + J'adore Mimì + lead name
        assert "Andrea" in msgs[1]["text"] and "J'adore Mim" in msgs[1]["text"]


class TestRealAIReply:
    def test_ai_pricing_reply_bomba(self, api_client, admin_headers):
        payload = {"nome": f"TEST_AI_{uuid.uuid4().hex[:6]}",
                   "cognome": "Test", "telefono": "+390000000002",
                   "servizio": "Bomba", "sede": "Milano Centro",
                   "campagna": "TEST_Fase3AI"}
        r = api_client.post(f"{BASE_URL}/api/integrations/meta/simulate",
                            headers=admin_headers, json=payload)
        assert r.status_code == 200
        cid = r.json()["conversation_id"]
        # customer asks about price
        r1 = api_client.post(
            f"{BASE_URL}/api/conversations/{cid}/simulate-customer",
            headers=admin_headers, json={"text": "Ciao quanto costa la Bomba?"})
        assert r1.status_code == 200
        r2 = api_client.post(
            f"{BASE_URL}/api/conversations/{cid}/simulate-ai-turn",
            headers=admin_headers, json={})
        assert r2.status_code == 200, r2.text
        d = r2.json()
        assert d["handoff"] is False
        text = d["message"]["text"]
        assert text and len(text) > 5
        # response should be in Italian (heuristic)
        assert any(w in text.lower() for w in
                   ["ciao", "prezzo", "seduta", "trattamento", "€", "bomba",
                    "posso", "consiglio", "vorresti", "obiettivo", "sedute",
                    "pacchetto"])


class TestAIHandoffStillWorks:
    def test_handoff_prenotazione(self, api_client, admin_headers):
        payload = {"nome": f"TEST_HO_{uuid.uuid4().hex[:6]}",
                   "servizio": "Bomba", "sede": "Milano Centro",
                   "telefono": "+390000000003"}
        r = api_client.post(f"{BASE_URL}/api/integrations/meta/simulate",
                            headers=admin_headers, json=payload)
        cid = r.json()["conversation_id"]
        lid = r.json()["lead"]["id"]
        api_client.post(f"{BASE_URL}/api/conversations/{cid}/simulate-customer",
                        headers=admin_headers,
                        json={"text": "ok voglio prenotare un appuntamento"})
        r2 = api_client.post(
            f"{BASE_URL}/api/conversations/{cid}/simulate-ai-turn",
            headers=admin_headers, json={})
        assert r2.status_code == 200
        d = r2.json()
        assert d["handoff"] is True
        assert d["new_status"] == "da_fissare"
        # notification
        notifs = api_client.get(f"{BASE_URL}/api/notifications",
                                headers=admin_headers).json()["notifications"]
        assert any(n["tipo"] == "cliente_da_fissare" and n["lead_id"] == lid
                   for n in notifs)


class TestWhatsAppConfig:
    def test_get_initial_config(self, api_client, admin_headers):
        r = api_client.get(f"{BASE_URL}/api/integrations/whatsapp/config",
                           headers=admin_headers)
        assert r.status_code == 200
        d = r.json()
        assert "verify_token" in d and d["verify_token"]
        # token_masked can be None initially OR set from env; configured reflects it
        assert "configured" in d and "token_masked" in d

    def test_operator_forbidden(self, api_client, operator_headers):
        r = api_client.get(f"{BASE_URL}/api/integrations/whatsapp/config",
                           headers=operator_headers)
        assert r.status_code == 403
        r2 = api_client.patch(f"{BASE_URL}/api/integrations/whatsapp/config",
                              headers=operator_headers,
                              json={"numero": "+390000"})
        assert r2.status_code == 403

    def test_patch_sets_configured_and_masked(self, api_client, admin_headers):
        payload = {"numero": "+393331234567",
                   "phone_number_id": "TEST_PNID_123",
                   "token": "EAAJTESTTOKENABCDEF1234"}
        r = api_client.patch(f"{BASE_URL}/api/integrations/whatsapp/config",
                             headers=admin_headers, json=payload)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["configured"] is True
        assert d["numero"] == "+393331234567"
        assert d["token_masked"] and d["token_masked"].startswith("••••")
        assert d["token_masked"].endswith("1234")


class TestWhatsAppWebhook:
    def test_verify_ok(self, api_client):
        r = api_client.get(
            f"{BASE_URL}/api/integrations/whatsapp/webhook",
            params={"hub.mode": "subscribe",
                    "hub.verify_token": WA_VERIFY_TOKEN,
                    "hub.challenge": "ZZZ"})
        assert r.status_code == 200
        assert r.text == "ZZZ"

    def test_verify_wrong_token_403(self, api_client):
        r = api_client.get(
            f"{BASE_URL}/api/integrations/whatsapp/webhook",
            params={"hub.mode": "subscribe",
                    "hub.verify_token": "WRONG", "hub.challenge": "X"})
        assert r.status_code == 403

    def test_post_generic_object(self, api_client):
        r = api_client.post(
            f"{BASE_URL}/api/integrations/whatsapp/webhook",
            json={"object": "whatsapp_business_account", "entry": []})
        assert r.status_code == 200
        assert r.json() == {"ok": True}


class TestIntegrationsStatus:
    def test_status(self, api_client, admin_headers):
        r = api_client.get(f"{BASE_URL}/api/integrations",
                           headers=admin_headers)
        assert r.status_code == 200
        d = r.json()
        assert d["ai"]["configured"] is True
        # whatsapp configured now true (test_patch_sets_configured_and_masked runs first)
        assert d["whatsapp"]["configured"] is True
        assert d["meta"]["configured"] is False


class TestRegressionFase12:
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

    def test_priorities(self, api_client, admin_headers):
        r = api_client.get(f"{BASE_URL}/api/home/priorities",
                           headers=admin_headers)
        assert r.status_code == 200

    def test_pipeline_8(self, api_client, admin_headers):
        r = api_client.get(f"{BASE_URL}/api/pipeline",
                           headers=admin_headers)
        assert r.status_code == 200
        assert len(r.json()) == 8

    def test_analytics(self, api_client, admin_headers):
        r = api_client.get(f"{BASE_URL}/api/analytics?period=30d",
                           headers=admin_headers)
        assert r.status_code == 200
