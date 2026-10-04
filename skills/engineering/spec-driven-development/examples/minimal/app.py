"""Small green demonstration, not a production service."""


def preview(message, correlation_id):
    outcome = "accepted" if message else "rejected"
    return outcome, {
        "event": "preview_decision",
        "outcome": outcome,
        "correlation_id": correlation_id,
    }
