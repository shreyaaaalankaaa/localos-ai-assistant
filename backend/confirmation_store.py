import time
import uuid


PENDING_ACTIONS = {}


def create_pending_action(action_type: str, payload: dict):
    action_id = str(uuid.uuid4())[:8]

    PENDING_ACTIONS[action_id] = {
        "action_id": action_id,
        "action_type": action_type,
        "payload": payload,
        "created_at": time.time(),
    }

    return PENDING_ACTIONS[action_id]


def get_pending_action(action_id: str):
    return PENDING_ACTIONS.get(action_id)


def pop_pending_action(action_id: str):
    return PENDING_ACTIONS.pop(action_id, None)


def list_pending_actions():
    return list(PENDING_ACTIONS.values())


def clear_old_actions(max_age_seconds: int = 600):
    now = time.time()
    expired = []

    for action_id, action in PENDING_ACTIONS.items():
        if now - action["created_at"] > max_age_seconds:
            expired.append(action_id)

    for action_id in expired:
        PENDING_ACTIONS.pop(action_id, None)