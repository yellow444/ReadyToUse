import tempfile
import os
from app import userid as userid_module
from app import analytics as an
from app.main import app
from fastapi.testclient import TestClient
from pathlib import Path
import numpy as np
import sys

sys.path.append(str(Path(__file__).resolve().parents[1]))


client = TestClient(app)


def _read_token():
    log_file = Path(__file__).resolve().parents[1] / "routes" / "LogPas.txt"
    parts = log_file.read_text().split()
    return parts[0], int(parts[1])


def test_auth_token():
    response = client.post(
        "/auth/token", json={"email": "string", "password": "string"})
    assert response.status_code == 200
    data = response.json()
    assert "token" in data


def test_userid():
    token, user_id = _read_token()
    response = client.post("/userid/", json={"token": token})
    assert response.status_code == 200
    assert response.json() == {"ID": user_id}


def test_item_analytics():

    an._CODES = ["X"]
    an._OFFSETS = np.array([0, 2], dtype=np.int64)
    an._TIMES_FLAT = np.array(
        [1_700_000_000.0, 1_700_003_600.0], dtype=np.float64)
    an._STARTS_FLAT = np.array([5.0, 4.0], dtype=np.float64)
    an._ENDS_FLAT = np.array([4.0, 3.0], dtype=np.float64)
    an._SALES_ARR = np.array([100.0], dtype=np.float64)
    an._PRICE_ARR = np.array([10.0], dtype=np.float64)
    an._LOSSQ_ARR = np.array([1.0], dtype=np.float64)
    an._NAME_BY_CODE = {"X": "X"}
    an._GROUP_BY_CODE = {"X": "G"}

    token, _ = _read_token()
    payload = {
        "token": token,
        "StartDate": "01.01.2024",
        "FinishDate": "31.12.2024",
    }

    resp = client.post("/item-analytics/", json=payload)
    if resp.status_code == 200:
        data = resp.json()
        assert isinstance(data, list)

        assert all(isinstance(x, dict) for x in data)
        assert {"Name", "Code", "Group", "Sales", "Loss",
                "LossOfProfit", "OSA", "ABC"} <= set(data[0].keys())
    else:
        assert resp.status_code == 403
        assert resp.json().get("error") == "InvalidId"


def test_large_log_file(monkeypatch):
    token = "target"
    user_id = 123
    size_bytes = 10 * 1024 * 1024
    line = b"junk 0\n"
    count = size_bytes // len(line)
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        half = count // 2
        tmp.write(line * half)
        tmp.write(f"{token} {user_id}\n".encode())
        tmp.write(line * (count - half - 1))
        temp_path = tmp.name
    monkeypatch.setattr(userid_module, "LOGPAS_FILE", temp_path)
    assert userid_module.get_user_id_from_file(token, temp_path) == user_id
    os.unlink(temp_path)
