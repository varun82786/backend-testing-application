from fastapi import Request
from sqlalchemy.exc import IntegrityError

from app.exceptions.handlers import _handle_integrity_error


def test_integrity_error_handler_returns_conflict_response() -> None:
    """Integrity errors are translated into a safe 409 conflict response."""
    request = Request({"type": "http", "method": "POST", "path": "/api/v1/test", "headers": []})
    exc = IntegrityError("duplicate key value violates unique constraint", {}, Exception("UNIQUE constraint failed"))

    response = _handle_integrity_error(request, exc)

    assert response.status_code == 409
    assert response.media_type == "application/json"
    body = response.body.decode()
    assert "CONFLICT" in body
    assert "integrity_constraint_violation" in body
