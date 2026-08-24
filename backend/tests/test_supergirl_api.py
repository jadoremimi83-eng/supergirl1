"""Comprehensive backend tests for SUPER GIRL Fase 1 Demo."""
import os
import time
import pytest
import requests

BASE_URL = os.environ["EXPO_PUBLIC_BACKEND_URL"].rstrip("/")


# ---------- AUTH ----------
class TestAuth:
    def test_admin_login(self, api_client):
        r = api_client.post(f"{BASE_URL}/api/auth/login",
                            json={"email": "admin@supergirl.app",
                                  "password": "Admin123!"})
        assert r.status_code == 200
        d = r.json()
        assert "access_token" in d and d["user"]["role"] == "admin"

    def test_operator_login(self, api_client):
        r = api_client.post(f"{BASE_URL}/api/auth/login",
                            json={"email": "operatore@supergirl.app",
                                  "password": "Operatore123!"})
        assert r.status_code == 200
        assert r.json()["user"]["role"] == "operator"

    def test_wrong_password_401(self, api_client):
        r = api_client.post(f"{BASE_URL}/api/auth/login",
                            json={"email": "admin@supergirl.app",
                                  "password": "wrong"})
        assert r.status_code == 401

    def test_me_endpoint(self, api_client, admin_headers):
        r = api_client.get(f"{BASE_URL}/api/auth/me", headers=admin_headers)
        assert r.status_code == 200
        assert r.json()["email"] == "admin@supergirl.app"


# ---------- SEED ----------
class TestSeed:
    def test_13_leads_seeded(self, api_client, admin_headers):
        r = api_client.get(f"{BASE_URL}/api/leads", headers=admin_headers)
        assert r.status_code == 200
        leads = r.json()
        assert len(leads) >= 13, f"expected >=13 leads, got {len(leads)}"

    def test_pipeline_8_stages(self, api_client, admin_headers):
        r = api_client.get(f"{BASE_URL}/api/pipeline", headers=admin_headers)
        assert r.status_code == 200
        stages = r.json()
        assert len(stages) == 8
        keys = [s["key"] for s in stages]
        assert "da_fissare" in keys and "nuovo_lead" in keys

    def test_seed_collections(self, api_client, admin_headers):
        for ep in ["/api/services", "/api/locations", "/api/campaigns",
                   "/api/team", "/api/knowledge-base"]:
            r = api_client.get(f"{BASE_URL}{ep}", headers=admin_headers)
            assert r.status_code == 200, f"{ep} failed"


# ---------- CONVERSATIONS ----------
class TestConversations:
    def test_list_all(self, api_client, admin_headers):
        r = api_client.get(f"{BASE_URL}/api/conversations", headers=admin_headers)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_filters(self, api_client, admin_headers):
        for f in ["ai", "operatore", "da_fissare", "non_lette"]:
            r = api_client.get(f"{BASE_URL}/api/conversations?filter={f}",
                               headers=admin_headers)
            assert r.status_code == 200

    def test_get_conversation_detail(self, api_client, admin_headers):
        convs = api_client.get(f"{BASE_URL}/api/conversations",
                               headers=admin_headers).json()
        cid = convs[0]["id"]
        r = api_client.get(f"{BASE_URL}/api/conversations/{cid}",
                           headers=admin_headers)
        assert r.status_code == 200
        d = r.json()
        assert "conversation" in d and "lead" in d and "messages" in d


# ---------- AI QUALIFY (no handoff) ----------
class TestAIQualify:
    def test_qualify_no_handoff(self, api_client, admin_headers):
        # use the LAST ai_attiva conversation (different from other tests)
        convs = api_client.get(f"{BASE_URL}/api/conversations?filter=ai",
                               headers=admin_headers).json()
        assert convs, "no AI-active conversation available"
        cid = convs[-1]["id"]
        r1 = api_client.post(
            f"{BASE_URL}/api/conversations/{cid}/simulate-customer",
            headers=admin_headers, json={"text": "Vorrei info sul prezzo"})
        assert r1.status_code == 200
        r2 = api_client.post(
            f"{BASE_URL}/api/conversations/{cid}/simulate-ai-turn",
            headers=admin_headers, json={})
        assert r2.status_code == 200
        d = r2.json()
        assert d["handoff"] is False
        assert d["new_status"] == "in_attesa"
        assert "message" in d


# ---------- AI HANDOFF (core) ----------
class TestAIHandoff:
    def test_full_handoff_flow(self, api_client, admin_headers):
        convs = api_client.get(f"{BASE_URL}/api/conversations?filter=ai",
                               headers=admin_headers).json()
        # pick middle AI-active conv to avoid clashes with other tests
        ai_convs = [c for c in convs if c.get("ai_attiva")]
        assert ai_convs, "no ai_attiva conversation available"
        target = ai_convs[len(ai_convs) // 2]
        cid = target["id"]
        lead_id = target["lead_id"]

        r1 = api_client.post(
            f"{BASE_URL}/api/conversations/{cid}/simulate-customer",
            headers=admin_headers,
            json={"text": "Vorrei prenotare un appuntamento"})
        assert r1.status_code == 200
        r2 = api_client.post(
            f"{BASE_URL}/api/conversations/{cid}/simulate-ai-turn",
            headers=admin_headers, json={})
        assert r2.status_code == 200, r2.text
        d = r2.json()
        assert d["handoff"] is True
        assert d["motivo"] == "prenotazione"
        assert d["new_status"] == "da_fissare"
        assert d.get("summary") and "Nome cliente" in d["summary"]

        # verify lead state
        lead = api_client.get(f"{BASE_URL}/api/leads/{lead_id}",
                              headers=admin_headers).json()["lead"]
        assert lead["stato_pipeline"] == "da_fissare"
        assert lead.get("ai_summary")

        # verify conversation: ai_attiva=false
        conv = api_client.get(f"{BASE_URL}/api/conversations/{cid}",
                              headers=admin_headers).json()["conversation"]
        assert conv["ai_attiva"] is False

        # verify notification
        notifs = api_client.get(f"{BASE_URL}/api/notifications",
                                headers=admin_headers).json()["notifications"]
        assert any(n["tipo"] == "cliente_da_fissare" and n["lead_id"] == lead_id
                   for n in notifs)


# ---------- TAKE / REACTIVATE ----------
class TestTakeReactivate:
    def test_take_and_reactivate(self, api_client, admin_headers):
        convs = api_client.get(f"{BASE_URL}/api/conversations?filter=ai",
                               headers=admin_headers).json()
        assert convs
        cid = convs[0]["id"]
        r = api_client.post(f"{BASE_URL}/api/conversations/{cid}/take",
                            headers=admin_headers, json={})
        assert r.status_code == 200
        assert r.json()["ai_attiva"] is False

        r2 = api_client.post(
            f"{BASE_URL}/api/conversations/{cid}/reactivate-ai",
            headers=admin_headers, json={})
        assert r2.status_code == 200
        assert r2.json()["ai_attiva"] is True

    def test_operator_send_message(self, api_client, operator_headers):
        convs = api_client.get(f"{BASE_URL}/api/conversations",
                               headers=operator_headers).json()
        assert convs
        cid = convs[0]["id"]
        r = api_client.post(f"{BASE_URL}/api/conversations/{cid}/messages",
                            headers=operator_headers,
                            json={"text": "TEST_ Messaggio operatore"})
        assert r.status_code == 200
        assert r.json()["sender"] == "operatore"


# ---------- LEADS ----------
class TestLeads:
    def test_search(self, api_client, admin_headers):
        leads = api_client.get(f"{BASE_URL}/api/leads",
                               headers=admin_headers).json()
        name = leads[0]["nome"][:3]
        r = api_client.get(f"{BASE_URL}/api/leads?search={name}",
                           headers=admin_headers)
        assert r.status_code == 200
        assert len(r.json()) >= 1

    def test_patch_lead(self, api_client, admin_headers):
        leads = api_client.get(f"{BASE_URL}/api/leads",
                               headers=admin_headers).json()
        lid = leads[0]["id"]
        r = api_client.patch(f"{BASE_URL}/api/leads/{lid}",
                             headers=admin_headers,
                             json={"note_staff": "TEST_ nota",
                                   "temperature": "molto_calda"})
        assert r.status_code == 200
        assert r.json()["note_staff"] == "TEST_ nota"
        assert r.json()["temperature"] == "molto_calda"

    def test_change_status_creates_history_and_notif(self, api_client,
                                                     admin_headers):
        # pick a lead not in da_fissare
        leads = api_client.get(f"{BASE_URL}/api/leads",
                               headers=admin_headers).json()
        target = next((l for l in leads if l["stato_pipeline"] != "da_fissare"),
                      None)
        assert target
        r = api_client.post(f"{BASE_URL}/api/leads/{target['id']}/status",
                            headers=admin_headers,
                            json={"stato": "da_fissare"})
        assert r.status_code == 200
        assert r.json()["stato_pipeline"] == "da_fissare"

        # history
        d = api_client.get(f"{BASE_URL}/api/leads/{target['id']}",
                           headers=admin_headers).json()
        assert any(h["to_status"] == "da_fissare" for h in d["history"])


# ---------- HOME PRIORITIES ----------
class TestHome:
    def test_priorities(self, api_client, admin_headers):
        r = api_client.get(f"{BASE_URL}/api/home/priorities",
                           headers=admin_headers)
        assert r.status_code == 200
        d = r.json()
        assert "da_fissare" in d and "total_leads" in d
        if d["da_fissare"]:
            first = d["da_fissare"][0]
            # required enrichment fields
            for k in ["foto_profilo", "ig_username", "piattaforma"]:
                assert k in first


# ---------- ANALYTICS ----------
class TestAnalytics:
    def test_analytics_30d(self, api_client, admin_headers):
        r = api_client.get(f"{BASE_URL}/api/analytics?period=30d",
                           headers=admin_headers)
        assert r.status_code == 200
        d = r.json()
        for k in ["nuovi_lead", "funnel", "pct_lead_appuntamento",
                  "by_campaign"]:
            assert k in d

    def test_filters(self, api_client, admin_headers):
        r = api_client.get(f"{BASE_URL}/api/analytics/filters",
                           headers=admin_headers)
        assert r.status_code == 200
        d = r.json()
        for k in ["sedi", "servizi", "campagne", "piattaforme"]:
            assert k in d

    def test_analytics_filter_by_dim(self, api_client, admin_headers):
        f = api_client.get(f"{BASE_URL}/api/analytics/filters",
                           headers=admin_headers).json()
        if f["sedi"]:
            r = api_client.get(
                f"{BASE_URL}/api/analytics?period=30d&sede={f['sedi'][0]}",
                headers=admin_headers)
            assert r.status_code == 200


# ---------- ALTRO / RBAC ----------
class TestAltroRBAC:
    def test_integrations_stati(self, api_client, admin_headers):
        r = api_client.get(f"{BASE_URL}/api/integrations",
                           headers=admin_headers)
        assert r.status_code == 200
        d = r.json()
        for k in ["meta", "whatsapp", "ai"]:
            assert d[k]["status"] == "non_attivo"

    def test_campaigns_have_lead_count(self, api_client, admin_headers):
        r = api_client.get(f"{BASE_URL}/api/campaigns", headers=admin_headers)
        assert r.status_code == 200
        assert all("lead_count" in c for c in r.json())

    def test_rbac_operator_cannot_create_service(self, api_client,
                                                  operator_headers):
        r = api_client.post(f"{BASE_URL}/api/services",
                            headers=operator_headers,
                            json={"nome": "TEST_ blocked"})
        assert r.status_code == 403

    def test_rbac_operator_cannot_create_location(self, api_client,
                                                   operator_headers):
        r = api_client.post(f"{BASE_URL}/api/locations",
                            headers=operator_headers,
                            json={"nome": "TEST_ blocked"})
        assert r.status_code == 403

    def test_rbac_admin_can_create_and_delete_service(self, api_client,
                                                      admin_headers):
        r = api_client.post(f"{BASE_URL}/api/services",
                            headers=admin_headers,
                            json={"nome": "TEST_ svc"})
        assert r.status_code == 200
        sid = r.json()["id"]
        r2 = api_client.delete(f"{BASE_URL}/api/services/{sid}",
                               headers=admin_headers)
        assert r2.status_code == 200

    def test_notifications(self, api_client, admin_headers):
        r = api_client.get(f"{BASE_URL}/api/notifications",
                           headers=admin_headers)
        assert r.status_code == 200
        d = r.json()
        assert "notifications" in d and "unread" in d
