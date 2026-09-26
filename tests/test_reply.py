from fastapi.testclient import TestClient


MERCHANT = {
    "merchant_id": "m_001_dental",
    "category_slug": "dentists",
    "identity": {
        "name": "Dr. Meera Dental Clinic",
        "owner_first_name": "Meera",
        "city": "Delhi",
    },
}


def push_merchant(client: TestClient):
    return client.post(
        "/v1/context",
        json={
            "scope": "merchant",
            "context_id": "m_001_dental",
            "version": 1,
            "payload": MERCHANT,
            "delivered_at": "2026-04-26T09:45:00Z",
        },
    )


def test_reply_hostile_opt_out(client: TestClient):
    push_merchant(client)

    response = client.post(
        "/v1/reply",
        json={
            "conversation_id": "conv_hostile_1",
            "merchant_id": "m_001_dental",
            "customer_id": None,
            "from_role": "merchant",
            "message": "Stop messaging me. This is useless spam.",
            "received_at": "2026-04-26T10:00:00Z",
            "turn_number": 2,
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["action"] == "end"


def test_reply_auto_reply_pattern(client: TestClient):
    push_merchant(client)

    response = client.post(
        "/v1/reply",
        json={
            "conversation_id": "conv_auto_1",
            "merchant_id": "m_001_dental",
            "customer_id": None,
            "from_role": "merchant",
            "message": "Thank you for contacting us! Our team will respond shortly.",
            "received_at": "2026-04-26T10:00:00Z",
            "turn_number": 2,
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["action"] == "end"


def test_reply_intent_transition(client: TestClient):
    push_merchant(client)

    response = client.post(
        "/v1/reply",
        json={
            "conversation_id": "conv_intent_1",
            "merchant_id": "m_001_dental",
            "customer_id": None,
            "from_role": "merchant",
            "message": "Ok lets do it. Whats next?",
            "received_at": "2026-04-26T10:00:00Z",
            "turn_number": 2,
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["action"] in ("reply", "send")
    assert data["cta"] is not None and len(data["cta"]) > 0
    assert len(data["body"]) > 5


def test_reply_general_exploration(client: TestClient):
    push_merchant(client)

    response = client.post(
        "/v1/reply",
        json={
            "conversation_id": "conv_general_1",
            "merchant_id": "m_001_dental",
            "customer_id": None,
            "from_role": "merchant",
            "message": "Can you explain how this campaign works?",
            "received_at": "2026-04-26T10:00:00Z",
            "turn_number": 2,
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["action"] in ("reply", "send")
    assert data["body"] is not None and len(data["body"]) > 5
