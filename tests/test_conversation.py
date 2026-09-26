from app.core.conversation_store import ConversationStore
from app.domain.conversation import ConversationState, ConversationTurn


def test_conversation_state_add_turn():
    state = ConversationState(
        conversation_id="conv_1",
        merchant_id="m_1",
        customer_id="c_1",
    )

    assert state.turn_count == 0
    assert state.user_turn_count == 0

    state.add_turn("vera", "Hello! How can I assist?", "2026-04-26T10:00:00Z")
    state.add_turn("user", "What are my options?", "2026-04-26T10:01:00Z")

    assert state.turn_count == 2
    assert state.user_turn_count == 1
    assert state.last_user_turn is not None
    assert state.last_user_turn.text == "What are my options?"


def test_conversation_store_thread_safe_operations():
    store = ConversationStore()

    state = store.get_or_create(
        conversation_id="conv_100",
        merchant_id="m_100",
        now="2026-04-26T10:00:00Z",
    )
    assert state.conversation_id == "conv_100"
    assert state.merchant_id == "m_100"
    assert state.status == "active"

    turn = store.add_turn(
        conversation_id="conv_100",
        speaker="user",
        text="Can we discuss pricing?",
        timestamp="2026-04-26T10:02:00Z",
    )
    assert turn.text == "Can we discuss pricing?"

    fetched = store.get("conv_100")
    assert fetched is not None
    assert fetched.turn_count == 1

    store.set_status("conv_100", "ended")
    assert store.get("conv_100").status == "ended"
