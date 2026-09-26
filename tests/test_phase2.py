from fastapi.testclient import TestClient


CATEGORY = {
    "slug": "dentists",
    "voice": {
        "tone": "peer_clinical",
        "vocab_taboo": ["guaranteed", "100% safe"],
    },
    "offer_catalog": [
        {
            "id": "den_001",
            "title": "Dental Cleaning @ ₹299",
            "value": "299",
        }
    ],
    "peer_stats": {
        "avg_rating": 4.4,
        "avg_ctr": 0.03,
    },
}

MERCHANT = {
    "merchant_id": "m_001_drmeera_dentist_delhi",
    "category_slug": "dentists",
    "identity": {
        "name": "Dr. Meera's Dental Clinic",
        "owner_first_name": "Meera",
        "city": "Delhi",
        "locality": "Lajpat Nagar",
    },
    "subscription": {
        "status": "active",
        "plan": "Pro",
        "days_remaining": 82,
    },
}

CUSTOMER = {
    "customer_id": "c_001_priya",
    "merchant_id": "m_001_drmeera_dentist_delhi",
    "identity": {
        "name": "Priya",
        "city": "Delhi",
    },
    "preferences": {
        "channel": "whatsapp",
    },
    "consent": {
        "scope": ["recall_reminders"],
    },
}

TRIGGER_RESEARCH = {
    "id": "trg_001_research_digest",
    "scope": "merchant",
    "kind": "research_digest",
    "merchant_id": "m_001_drmeera_dentist_delhi",
    "customer_id": None,
    "payload": {
        "category": "dentists",
        "top_item_id": "d_2026W17_jida_fluoride",
    },
    "urgency": 2,
    "suppression_key": "research:dentists:2026-W17",
}

TRIGGER_RECALL = {
    "id": "trg_002_recall_due",
    "scope": "customer",
    "kind": "recall_due",
    "merchant_id": "m_001_drmeera_dentist_delhi",
    "customer_id": "c_001_priya",
    "payload": {
        "service_due": "dental_cleaning",
        "available_slots": [
            {"label": "Wed 5 Nov, 6pm"},
            {"label": "Thu 6 Nov, 5pm"},
        ],
        "last_service_date": "2026-05-01",
        "due_date": "2026-11-01",
    },
    "urgency": 3,
    "suppression_key": "recall:c_001_priya:6mo",
}


def push_context(client: TestClient, scope: str, cid: str, version: int, payload: dict):
    return client.post(
        "/v1/context",
        json={
            "scope": scope,
            "context_id": cid,
            "version": version,
            "payload": payload,
            "delivered_at": "2026-04-26T09:45:00Z",
        },
    )


def test_tick_empty_triggers(client: TestClient):
    response = client.post(
        "/v1/tick",
        json={
            "now": "2026-04-26T10:00:00Z",
            "available_triggers": [],
        },
    )
    assert response.status_code == 200
    assert response.json() == {"actions": []}


def test_tick_merchant_trigger(client: TestClient):
    push_context(client, "category", "dentists", 1, CATEGORY)
    push_context(client, "merchant", "m_001_drmeera_dentist_delhi", 1, MERCHANT)
    push_context(client, "trigger", "trg_001_research_digest", 1, TRIGGER_RESEARCH)

    response = client.post(
        "/v1/tick",
        json={
            "now": "2026-04-26T10:35:00Z",
            "available_triggers": ["trg_001_research_digest"],
        },
    )
    assert response.status_code == 200

    data = response.json()
    assert len(data["actions"]) == 1

    action = data["actions"][0]
    assert action["merchant_id"] == "m_001_drmeera_dentist_delhi"
    assert action["customer_id"] is None
    assert action["send_as"] == "vera"
    assert action["trigger_id"] == "trg_001_research_digest"
    assert action["template_name"] == "research_digest"
    assert "Meera" in action["body"]
    assert action["suppression_key"] == "research:dentists:2026-W17"
    assert action["cta"] is not None and len(action["cta"]) > 0


def test_tick_suppression_prevents_duplicate_sends(client: TestClient):
    push_context(client, "category", "dentists", 1, CATEGORY)
    push_context(client, "merchant", "m_001_drmeera_dentist_delhi", 1, MERCHANT)
    push_context(client, "trigger", "trg_001_research_digest", 1, TRIGGER_RESEARCH)

    # First tick -> action returned
    res1 = client.post(
        "/v1/tick",
        json={
            "now": "2026-04-26T10:35:00Z",
            "available_triggers": ["trg_001_research_digest"],
        },
    )
    assert len(res1.json()["actions"]) == 1

    # Second tick with same trigger -> suppressed
    res2 = client.post(
        "/v1/tick",
        json={
            "now": "2026-04-26T10:36:00Z",
            "available_triggers": ["trg_001_research_digest"],
        },
    )
    assert res2.json()["actions"] == []


def test_tick_customer_trigger(client: TestClient):
    push_context(client, "category", "dentists", 1, CATEGORY)
    push_context(client, "merchant", "m_001_drmeera_dentist_delhi", 1, MERCHANT)
    push_context(client, "customer", "c_001_priya", 1, CUSTOMER)
    push_context(client, "trigger", "trg_002_recall_due", 1, TRIGGER_RECALL)

    response = client.post(
        "/v1/tick",
        json={
            "now": "2026-04-26T11:00:00Z",
            "available_triggers": ["trg_002_recall_due"],
        },
    )
    assert response.status_code == 200

    data = response.json()
    assert len(data["actions"]) == 1

    action = data["actions"][0]
    assert action["merchant_id"] == "m_001_drmeera_dentist_delhi"
    assert action["customer_id"] == "c_001_priya"
    assert action["send_as"] == "merchant_on_behalf"
    assert action["trigger_id"] == "trg_002_recall_due"
    assert "Priya" in action["body"]
    assert "Dr. Meera's Dental Clinic" in action["body"]
    assert action["cta"] == "multi_choice_slot"


def test_tick_unresolved_trigger_ignored(client: TestClient):
    # Trigger exists, but no merchant context in store
    push_context(client, "trigger", "trg_001_research_digest", 1, TRIGGER_RESEARCH)

    response = client.post(
        "/v1/tick",
        json={
            "now": "2026-04-26T10:35:00Z",
            "available_triggers": ["trg_001_research_digest"],
        },
    )
    assert response.status_code == 200
    assert response.json() == {"actions": []}
