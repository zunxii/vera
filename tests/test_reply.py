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
    assert data["rationale"]


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
    assert data["action"] == "send"
    assert data["cta"]
    assert data["rationale"]


def test_reply_wait_request(client: TestClient):
    push_merchant(client)

    response = client.post(
        "/v1/reply",
        json={
            "conversation_id": "conv_wait",
            "merchant_id": "m_001_dental",
            "customer_id": None,
            "from_role": "merchant",
            "message": "Let me think about it and get back to you.",
            "received_at": "2026-04-26T10:00:00Z",
            "turn_number": 2,
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["action"] == "wait"
    assert data["wait_seconds"] == 1800
    assert data["rationale"]


def test_reply_normal_action_is_send(client: TestClient):
    push_merchant(client)

    response = client.post(
        "/v1/reply",
        json={
            "conversation_id": "conv_normal",
            "merchant_id": "m_001_dental",
            "customer_id": None,
            "from_role": "merchant",
            "message": "Sounds interesting.",
            "received_at": "2026-04-26T10:00:00Z",
            "turn_number": 2,
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["action"] == "send"
    assert data["body"]
    assert data["cta"]
    assert data["rationale"]


def test_reply_auto_reply_eventually_ends(client: TestClient):
    push_merchant(client)

    message = (
        "Thank you for contacting us! "
        "Our team will respond shortly."
    )

    for index in range(1, 4):
        response = client.post(
            "/v1/reply",
            json={
                "conversation_id": f"conv_auto_{index}",
                "merchant_id": "m_001_dental",
                "customer_id": None,
                "from_role": "merchant",
                "message": message,
                "received_at": f"2026-04-26T10:0{index}:00Z",
                "turn_number": 2,
            },
        )

        assert response.status_code == 200
        data = response.json()

        if index < 3:
            assert data["action"] == "wait"
        else:
            assert data["action"] == "end"
