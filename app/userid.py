from __future__ import annotations

import os
from typing import Optional
import mmap
import hyperscan as hs

from fastapi import APIRouter
from fastapi.responses import ORJSONResponse

BASE_DIR = os.path.dirname(__file__)
LOGPAS_FILE = os.path.join(BASE_DIR, "..", "routes", "LogPas.txt")

router = APIRouter(prefix="/userid", tags=["userid"])


def get_user_id_from_file(token: str, file_path: str = LOGPAS_FILE) -> Optional[int]:
    try:
        db = hs.Database()
        pattern = token.encode()
        db.compile([pattern], ids=[1],
                   flags=hs.HS_FLAG_SINGLEMATCH, literal=True)

        with open(file_path, "rb") as f, mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as mm:
            match_end: list[int] = []

            chunk_size = 1024 * 1024
            overlap = max(len(pattern) - 1, 0)

            for pos in range(0, len(mm), chunk_size):
                end = min(len(mm), pos + chunk_size + overlap)

                def _on_match(_id, _from, to, _flags, _ctx, base=pos):
                    match_end.append(base + to)
                    return hs.HS_SCAN_TERMINATED

                try:
                    db.scan(mm[pos:end], match_event_handler=_on_match)
                except hs.ScanTerminated:
                    pass

                if match_end:
                    break

            if not match_end:
                return None

            i = match_end[0]
            n = len(mm)
            while i < n and mm[i] in b" \t":
                i += 1
            start = i
            while i < n and 48 <= mm[i] <= 57:
                i += 1
            if start < i:
                try:
                    return int(mm[start:i])
                except ValueError:
                    return None
    except FileNotFoundError:
        return None
    return None


@router.post("/")
def get_user_id(body: dict):
    token = str(body.get("token", ""))
    user_id = get_user_id_from_file(token)
    if user_id is not None:
        return ORJSONResponse({"ID": user_id}, status_code=200)
    return ORJSONResponse({"error": "Invalid token"}, status_code=403)
