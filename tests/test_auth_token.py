from pathlib import Path
import sys
import time
import numpy as np

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.auth import _create_token, _verify_token, _token_cache


def test_sign_and_verify():
    email = "user@example.com"
    password = "secret"
    token = _create_token(email, password)
    payload = _verify_token(token)
    assert payload == {"email": email, "password": password}


def test_tampered_token_invalid():
    token = _create_token("a", "b")
    bad_token = token[:-1] + ("A" if token[-1] != "A" else "B")
    assert _verify_token(bad_token) is None


def test_token_issuance_latency_p95_under_2ms():
    _token_cache.clear()
    _create_token("latency", "test")
    times = []
    for _ in range(1000):
        start = time.perf_counter()
        _create_token("latency", "test")
        times.append((time.perf_counter() - start) * 1000)
    p95 = np.percentile(times, 95)
    assert p95 <= 2
