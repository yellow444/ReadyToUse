from __future__ import annotations

import os
from typing import Any, Dict, List, Tuple
from collections import defaultdict
from datetime import datetime, timedelta

import numpy as np
import numba as nb
import orjson

from fastapi import APIRouter, Request
from fastapi.responses import ORJSONResponse

from .userid import get_user_id_from_file

BASE_DIR = os.path.join(os.path.dirname(__file__), "..", "routes")
STOCK_DUMP = os.path.join(BASE_DIR, "stock_dump.json")
SALES_DUMP = os.path.join(BASE_DIR, "sales_dump.json")

router = APIRouter(prefix="/item-analytics", tags=["item-analytics"])

_CODES: List[str] = []
_OFFSETS: np.ndarray | None = None
_TIMES_FLAT: np.ndarray | None = None
_STARTS_FLAT: np.ndarray | None = None
_ENDS_FLAT: np.ndarray | None = None
_SALES_ARR: np.ndarray | None = None
_PRICE_ARR: np.ndarray | None = None
_LOSSQ_ARR: np.ndarray | None = None
_NAME_BY_CODE: Dict[str, str] = {}
_GROUP_BY_CODE: Dict[str, str] = {}


def _parse_dt(val: str) -> datetime | None:
    for fmt in ("%d.%m.%Y %H:%M:%S", "%d.%m.%Y %H:%M", "%d.%m.%Y"):
        try:
            return datetime.strptime(val, fmt)
        except Exception:
            continue
    return None


def _load_json_fast(path: str) -> Any:
    if not os.path.exists(path):
        return []
    with open(path, "rb") as f:
        return orjson.loads(f.read())


@nb.njit(cache=True, fastmath=True, inline="always")
def _compute_osa_one_code(times, starts, ends, start_ts: float, end_ts: float) -> float:
    m = times.shape[0]
    if m == 0:
        return 0.0

    avail_hours = 0.0

    it_start = start_ts
    it_end = times[0]
    if it_end > end_ts:
        it_end = end_ts
    if it_end > it_start and starts[0] > 0.0:
        avail_hours += (it_end - it_start) / 3600.0

    for j in range(1, m):
        s = times[j - 1]
        e = times[j]
        if s < start_ts:
            s = start_ts
        if e > end_ts:
            e = end_ts
        if e > s and ends[j - 1] > 0.0:
            avail_hours += (e - s) / 3600.0
        if times[j] >= end_ts:
            break

    it_start = times[m - 1]
    it_end = end_ts
    if it_end > it_start and ends[m - 1] > 0.0:
        avail_hours += (it_end - it_start) / 3600.0

    total_hours = (end_ts - start_ts) / 3600.0
    if total_hours <= 0.0:
        return 0.0
    return 100.0 * (avail_hours / total_hours)


@nb.njit(cache=True, parallel=True, fastmath=True)
def _compute_metrics_numba_csr(
    times_flat: np.ndarray,
    starts_flat: np.ndarray,
    ends_flat: np.ndarray,
    offsets: np.ndarray,
    start_ts: float,
    end_ts: float,
    sales_arr: np.ndarray,
    price_arr: np.ndarray,
    loss_qty_arr: np.ndarray,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    n_codes = sales_arr.shape[0]
    osa_res = np.empty(n_codes, dtype=np.float64)
    loss_amounts = np.empty(n_codes, dtype=np.float64)
    loss_percents = np.empty(n_codes, dtype=np.float64)

    for i in nb.prange(n_codes):
        s = offsets[i]
        e = offsets[i + 1]
        if e > s:
            osa = _compute_osa_one_code(
                times_flat[s:e], starts_flat[s:e], ends_flat[s:e],
                start_ts, end_ts
            )
        else:
            osa = 0.0

        osa_res[i] = osa

        amt = loss_qty_arr[i] * price_arr[i]
        loss_amounts[i] = amt
        total = sales_arr[i]
        loss_percents[i] = (amt / total) * 100.0 if total > 0.0 else 0.0

    return osa_res, loss_amounts, loss_percents


@nb.njit(cache=True, parallel=True, fastmath=True)
def _assign_abc_numba(sales: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    order = np.argsort(sales)[::-1]
    sorted_sales = sales[order]
    cumulative = np.cumsum(sorted_sales)
    total = cumulative[-1] if sorted_sales.size > 0 else 0.0
    abc = np.empty(sales.shape[0], dtype=np.uint8)

    for i in nb.prange(sorted_sales.shape[0]):
        share = (cumulative[i] / total * 100.0) if total > 0.0 else 0.0
        if share <= 80.0:
            abc[i] = 65
        elif share <= 95.0:
            abc[i] = 66
        else:
            abc[i] = 67
    return order, abc


def assign_abc(sales: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:

    return _assign_abc_numba(sales)


def _prepare_csr_on_start(stock_data: List[Dict[str, Any]], sales_data: List[Dict[str, Any]]) -> None:
    global _CODES, _OFFSETS, _TIMES_FLAT, _STARTS_FLAT, _ENDS_FLAT
    global _SALES_ARR, _PRICE_ARR, _LOSSQ_ARR, _NAME_BY_CODE, _GROUP_BY_CODE

    events_by_code: Dict[str,
                         List[Tuple[datetime, float, float]]] = defaultdict(list)
    loss_qty: Dict[str, float] = defaultdict(float)
    name_by_code: Dict[str, str] = {}
    group_by_code: Dict[str, str] = {}

    for item in stock_data:
        code = str(item.get("НоменклатураКод", "")).strip()
        if not code:
            continue

        name_by_code[code] = item.get("Номенклатура")
        group_by_code[code] = item.get("Родитель") or "Без группы 🤔"

        dt = _parse_dt(str(item.get("Период", "")))
        if dt is not None:
            start_val = float(item.get("НачальныйОстаток", 0) or 0.0)
            end_val = float(item.get("КонечныйОстаток", 0) or 0.0)
            events_by_code[code].append((dt, start_val, end_val))

        if item.get("СтатьяРасходов") == "Порча на складах (94)":
            sv = float(item.get("НачальныйОстаток", 0) or 0.0)
            ev = float(item.get("КонечныйОстаток", 0) or 0.0)
            diff = sv - ev
            if diff > 0.0:
                loss_qty[code] += diff

    sales_sum: Dict[str, float] = defaultdict(float)
    sales_qty: Dict[str, float] = defaultdict(float)
    name_sales: Dict[str, str] = {}

    for rec in sales_data:
        code = str(rec.get("Код", "")).strip()
        if not code:
            continue
        name_sales[code] = rec.get("Номенклатура")
        sales_sum[code] += float(rec.get("Сумма", 0) or 0.0)
        sales_qty[code] += float(rec.get("Количество", 0) or 0.0)

    price_by_code: Dict[str, float] = {}
    for code, qty in sales_qty.items():
        price_by_code[code] = (sales_sum[code] / qty) if qty > 0.0 else 0.0

    codes: List[str] = []
    code_lengths: List[int] = []
    for code, total_sum in sales_sum.items():
        if total_sum > 0.0:
            codes.append(code)
            evs = events_by_code.get(code)
            code_lengths.append(0 if not evs else len(evs))

    n_codes = len(codes)
    total_events = int(
        np.sum(np.array(code_lengths, dtype=np.int64))) if n_codes > 0 else 0

    times_flat = np.empty(total_events, dtype=np.float64)
    starts_flat = np.empty(total_events, dtype=np.float64)
    ends_flat = np.empty(total_events, dtype=np.float64)
    offsets = np.empty(n_codes + 1, dtype=np.int64)

    sales_arr = np.empty(n_codes, dtype=np.float64)
    price_arr = np.empty(n_codes, dtype=np.float64)
    loss_arr = np.empty(n_codes, dtype=np.float64)

    cur = 0
    for i, code in enumerate(codes):
        offsets[i] = cur
        evs = events_by_code.get(code, [])
        if evs:
            evs.sort(key=lambda x: x[0])
            m = len(evs)
            for j in range(m):
                dt, sv, ev = evs[j]
                times_flat[cur + j] = dt.timestamp()
                starts_flat[cur + j] = float(sv)
                ends_flat[cur + j] = float(ev)
            cur += m

        sales_arr[i] = sales_sum.get(code, 0.0)
        price_arr[i] = price_by_code.get(code, 0.0)
        loss_arr[i] = loss_qty.get(code, 0.0)

        nm = name_sales.get(code) or name_by_code.get(code) or code
        name_by_code[code] = nm
        if code not in group_by_code:
            group_by_code[code] = "Без группы 🤔"

    offsets[n_codes] = cur

    _CODES = codes
    _OFFSETS = offsets
    _TIMES_FLAT = times_flat
    _STARTS_FLAT = starts_flat
    _ENDS_FLAT = ends_flat
    _SALES_ARR = sales_arr
    _PRICE_ARR = price_arr
    _LOSSQ_ARR = loss_arr
    _NAME_BY_CODE = name_by_code
    _GROUP_BY_CODE = group_by_code


def warmup_numba() -> None:

    stock_data = _load_json_fast(STOCK_DUMP)
    sales_data = _load_json_fast(SALES_DUMP)
    if not isinstance(stock_data, list):
        stock_data = []
    if not isinstance(sales_data, list):
        sales_data = []

    _prepare_csr_on_start(stock_data, sales_data)

    if (
        _OFFSETS is not None and _TIMES_FLAT is not None and
        _STARTS_FLAT is not None and _ENDS_FLAT is not None and
        _SALES_ARR is not None and _PRICE_ARR is not None and _LOSSQ_ARR is not None
    ):
        start_ts = 1_700_000_000.0
        end_ts = start_ts + 3600.0
        _compute_metrics_numba_csr(
            _TIMES_FLAT, _STARTS_FLAT, _ENDS_FLAT, _OFFSETS,
            start_ts, end_ts, _SALES_ARR, _PRICE_ARR, _LOSSQ_ARR
        )


@router.post("/")
async def item_analytics(request: Request) -> ORJSONResponse:

    raw = await request.body()
    try:
        payload = orjson.loads(raw)
    except Exception:
        return ORJSONResponse({"error": "invalid json"}, status_code=400)

    token = str(payload.get("token", ""))
    user_id = get_user_id_from_file(token)
    if user_id != 1:
        return ORJSONResponse({"error": "InvalidId"}, status_code=403)

    start_s = str(payload.get("StartDate", ""))
    finish_s = str(payload.get("FinishDate", ""))

    def _parse_or_400(s: str) -> datetime | None:
        for fmt in ("%d.%m.%Y %H:%M:%S", "%d.%m.%Y %H:%M", "%d.%m.%Y"):
            try:
                return datetime.strptime(s, fmt)
            except Exception:
                continue
        return None

    start_dt = _parse_or_400(start_s)
    finish_dt = _parse_or_400(finish_s)
    if start_dt is None or finish_dt is None:
        return ORJSONResponse({"error": "invalid dates"}, status_code=400)

    end_dt = finish_dt + timedelta(days=1)
    start_ts = float(start_dt.timestamp())
    end_ts = float(end_dt.timestamp())

    codes = _CODES
    offsets = _OFFSETS
    times_flat = _TIMES_FLAT
    starts_flat = _STARTS_FLAT
    ends_flat = _ENDS_FLAT
    sales_arr = _SALES_ARR
    price_arr = _PRICE_ARR
    lossq_arr = _LOSSQ_ARR
    name_by_code = _NAME_BY_CODE
    group_by_code = _GROUP_BY_CODE

    if offsets is None or times_flat is None or starts_flat is None or ends_flat is None:
        return ORJSONResponse({"error": "data not loaded"}, status_code=500)

    osa_res, loss_amounts, loss_percents = _compute_metrics_numba_csr(
        times_flat, starts_flat, ends_flat, offsets,
        start_ts, end_ts, sales_arr, price_arr, lossq_arr
    )

    order, abc_codes = _assign_abc_numba(sales_arr)

    n = len(codes)
    out = []
    append = out.append
    for rank_idx in range(n):
        i = order[rank_idx]
        code = codes[i]
        append({
            "Name": name_by_code.get(code, code),
            "Code": code,
            "Group": group_by_code.get(code, "Без группы"),
            "Sales": round(float(sales_arr[i]), 2),
            "Loss": round(float(loss_amounts[i]), 2),
            "LossOfProfit": round(float(loss_percents[i]), 3),
            "OSA": round(float(osa_res[i]), 2),
            "ABC": chr(abc_codes[rank_idx]),
        })

    return ORJSONResponse(out, status_code=200)
