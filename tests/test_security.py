from starlette.requests import Request

from app.core.auth import get_client_ip, is_admin_ip


def fake_request(peer: str, forwarded: str | None = None) -> Request:
    headers = [(b"x-forwarded-for", forwarded.encode())] if forwarded else []
    return Request({"type": "http", "headers": headers, "client": (peer, 1234)})


def test_spoofed_forwarded_header_cannot_claim_localhost():
    # Attacker sends "X-Forwarded-For: 127.0.0.1"; nginx appends the real address.
    request = fake_request("172.18.0.5", "127.0.0.1, 203.0.113.9")
    assert get_client_ip(request) == "203.0.113.9"
    assert is_admin_ip(request) is False


def test_direct_connection_uses_peer_address():
    assert get_client_ip(fake_request("127.0.0.1")) == "127.0.0.1"
    assert is_admin_ip(fake_request("127.0.0.1")) is True
