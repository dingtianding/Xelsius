from app import ratelimit


def setup_function():
    ratelimit._hits.clear()


def test_first_request_allowed():
    allowed, remaining = ratelimit.check("1.2.3.4")
    assert allowed is True
    assert remaining == ratelimit._FREE_LIMIT - 1


def test_limit_exhaustion():
    for _ in range(ratelimit._FREE_LIMIT):
        ratelimit.check("1.2.3.4")
    allowed, remaining = ratelimit.check("1.2.3.4")
    assert allowed is False
    assert remaining == 0


def test_different_ips_independent():
    for _ in range(ratelimit._FREE_LIMIT):
        ratelimit.check("1.1.1.1")
    allowed, _ = ratelimit.check("2.2.2.2")
    assert allowed is True


def test_remaining_decrements():
    _, r1 = ratelimit.check("5.5.5.5")
    _, r2 = ratelimit.check("5.5.5.5")
    assert r2 == r1 - 1
