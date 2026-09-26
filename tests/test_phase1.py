from fastapi.testclient import TestClient


CATEGORY = {
    "slug": "dentists",
    "voice": {
        "tone": "peer_clinical",
        "vocab_taboo": [
            "guaranteed",
            "100% safe",
        ],
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
        "city": "Delhi",
        "locality": "Lajpat Nagar",
    },
    "subscription": {
        "status": "active",
        "plan": "Pro",
        "days_remaining": 82,
    },
}


def push(
    client: TestClient,
    scope: str,
    context_id: str,
    version: int,
    payload: dict,
):
    return client.post(
        "/v1/context",
        json={
            "scope": scope,
            "context_id": context_id,
            "version": version,
            "payload": payload,
            "delivered_at": (
                "2026-04-26T09:45:00Z"
            ),
        },
    )


def test_healthz_starts_empty(
    client: TestClient,
):
    response = client.get(
        "/v1/healthz"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "ok"

    assert data["contexts_loaded"] == {
        "category": 0,
        "merchant": 0,
        "customer": 0,
        "trigger": 0,
    }


def test_metadata(
    client: TestClient,
):
    response = client.get(
        "/v1/metadata"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["team_name"]

    assert isinstance(
        data["team_members"],
        list,
    )

    assert data["version"]


def test_context_accepts_first_version_and_updates_healthz(
    client: TestClient,
):
    response = push(
        client,
        "category",
        "dentists",
        1,
        CATEGORY,
    )

    assert response.status_code == 200

    body = response.json()

    assert body["accepted"] is True

    assert (
        body["ack_id"]
        == "ack_dentists_v1"
    )

    health = client.get(
        "/v1/healthz"
    ).json()

    assert (
        health["contexts_loaded"][
            "category"
        ]
        == 1
    )


def test_equal_version_is_idempotent_success(
    client: TestClient,
):
    first = push(
        client,
        "merchant",
        "m_001",
        1,
        MERCHANT,
    )

    second = push(
        client,
        "merchant",
        "m_001",
        1,
        MERCHANT,
    )

    assert first.status_code == 200
    assert first.json()["accepted"] is True

    assert second.status_code == 200
    assert second.json()["accepted"] is True


def test_lower_version_is_stale_and_returns_409(
    client: TestClient,
):
    push(
        client,
        "merchant",
        "m_001",
        2,
        MERCHANT,
    )

    response = push(
        client,
        "merchant",
        "m_001",
        1,
        {
            "changed": "old"
        },
    )

    assert response.status_code == 409

    data = response.json()

    assert data["accepted"] is False

    assert (
        data["current_version"]
        == 2
    )


def test_higher_version_replaces(
    client: TestClient,
):
    updated = {
        **MERCHANT,
        "performance": {
            "views": 2580
        },
    }

    push(
        client,
        "merchant",
        "m_001",
        1,
        MERCHANT,
    )

    response = push(
        client,
        "merchant",
        "m_001",
        2,
        updated,
    )

    assert response.status_code == 200
    assert response.json()["accepted"] is True

    assert (
        response.json()["ack_id"]
        == "ack_m_001_v2"
    )


def test_each_scope_has_independent_namespace(
    client: TestClient,
):
    push(
        client,
        "category",
        "same-id",
        1,
        CATEGORY,
    )

    push(
        client,
        "merchant",
        "same-id",
        1,
        MERCHANT,
    )

    health = client.get(
        "/v1/healthz"
    ).json()

    assert (
        health["contexts_loaded"][
            "category"
        ]
        == 1
    )

    assert (
        health["contexts_loaded"][
            "merchant"
        ]
        == 1
    )


def test_invalid_scope_is_rejected(
    client: TestClient,
):
    response = client.post(
        "/v1/context",
        json={
            "scope": "bogus",
            "context_id": "x",
            "version": 1,
            "payload": {},
            "delivered_at": (
                "2026-04-26T09:45:00Z"
            ),
        },
    )

    assert response.status_code == 400

    assert (
        response.json()["detail"][
            "reason"
        ]
        == "invalid_scope"
    )
