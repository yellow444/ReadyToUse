from __future__ import annotations

import json
import os

import requests
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Any, Dict, List
from collections import defaultdict
from datetime import datetime, timedelta

BASE_DIR = os.path.dirname(__file__)
STOCK_DUMP = os.path.join(BASE_DIR, "stock_dump.json")
SALES_DUMP = os.path.join(BASE_DIR, "sales_dump.json")

router = APIRouter(prefix="/item-analytics", tags=["item-analytics"])


class ItemAnalyticsRequest(BaseModel):
    token: str
    StartDate: str
    FinishDate: str


def _parse_dt(val: str) -> datetime | None:
    for fmt in ("%d.%m.%Y %H:%M:%S", "%d.%m.%Y %H:%M", "%d.%m.%Y"):
        try:
            return datetime.strptime(val, fmt)
        except Exception:
            continue
    return None


def _fetch_stock(start_date: str, finish_date: str) -> List[Dict[str, Any]]:
    try:
        with open(STOCK_DUMP, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                return data
    except Exception:
        return []
    return []


def _fetch_sales(start_date: str, finish_date: str) -> List[Dict[str, Any]]:
    try:
        with open(SALES_DUMP, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                return data
    except Exception:
        return []
    return []


def _calculate_osa(events: List[Dict[str, Any]], start_dt: datetime, end_dt: datetime) -> float:
    if not events:
        return 0.0
    events = sorted(events, key=lambda x: x["time"])
    balance = events[0]["start"]
    current = start_dt
    avail_hours = 0.0
    for ev in events:
        t = ev["time"]
        if t < start_dt:
            balance = ev["end"]
            continue
        if t > end_dt:
            break
        if balance > 0:
            avail_hours += (t - current).total_seconds() / 3600
        balance = ev["end"]
        current = t
    if current < end_dt and balance > 0:
        avail_hours += (end_dt - current).total_seconds() / 3600
    total_hours = (end_dt - start_dt).total_seconds() / 3600
    if total_hours <= 0:
        return 0.0
    return round(100 * avail_hours / total_hours, 2)


def _prepare_data(stock_data: List[Dict[str, Any]], sales_data: List[Dict[str, Any]], start_dt: datetime, end_dt: datetime) -> List[Dict[str, Any]]:
    events_by_code: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    loss_qty: Dict[str, float] = defaultdict(float)
    name_by_code: Dict[str, str] = {}
    group_by_code: Dict[str, str] = {}
    for item in stock_data:
        code = str(item.get("НоменклатураКод", "")).strip()
        name = item.get("Номенклатура")
        group = item.get("Родитель")
        if code:
            name_by_code[code] = name
            group_by_code[code] = group
        dt = _parse_dt(str(item.get("Период", "")))
        if dt:
            events_by_code[code].append({
                "time": dt,
                "start": float(item.get("НачальныйОстаток", 0) or 0),
                "end": float(item.get("КонечныйОстаток", 0) or 0),
            })
        if item.get("СтатьяРасходов") == "Порча на складах (94)":
            start = float(item.get("НачальныйОстаток", 0) or 0)
            end = float(item.get("КонечныйОстаток", 0) or 0)
            diff = start - end
            if diff > 0:
                loss_qty[code] += diff

    sales_sum: Dict[str, float] = defaultdict(float)
    sales_qty: Dict[str, float] = defaultdict(float)
    name_sales: Dict[str, str] = {}
    for rec in sales_data:
        code = str(rec.get("Код", "")).strip()
        name = rec.get("Номенклатура")
        group = group_by_code.get(code, "")
        if code:
            name_sales[code] = name
        sales_sum[code] += float(rec.get("Сумма", 0) or 0)
        sales_qty[code] += float(rec.get("Количество", 0) or 0)

    price_by_code: Dict[str, float] = {}
    for code, qty in sales_qty.items():
        if qty > 0:
            price_by_code[code] = sales_sum[code] / qty

    items: List[Dict[str, Any]] = []
    for code, total_sum in sales_sum.items():
        price = price_by_code.get(code, 0)
        qty_loss = loss_qty.get(code, 0)
        loss_amount = qty_loss * price
        osa = _calculate_osa(events_by_code.get(code, []), start_dt, end_dt)
        name = name_sales.get(code) or name_by_code.get(code) or code
        group = group_by_code.get(code, "")
        loss_percent = (loss_amount / total_sum * 100) if total_sum else 0
        if group == "":
            group = "Без группы 🤔"
        items.append({
            "Name": name,
            "Code": code,
            "Group": group,
            "Sales": round(total_sum, 2),
            "Loss": round(loss_amount, 2),
            "LossOfProfit": round(loss_percent, 3),
            "OSA": osa,
        })
    total_sales = sum(item["Sales"] for item in items)
    cumulative = 0.0
    for item in sorted(items, key=lambda x: x["Sales"], reverse=True):
        cumulative += item["Sales"]
        share = (cumulative / total_sales * 100) if total_sales else 0
        if share <= 80:
            item["ABC"] = "A"
        elif share <= 95:
            item["ABC"] = "B"
        else:
            item["ABC"] = "C"
    items.sort(key=lambda x: x["Sales"], reverse=True)
    return items


def _get_item_analytics(payload: ItemAnalyticsRequest) -> List[Dict[str, Any]]:
    start_dt = datetime.strptime(payload.StartDate, "%d.%m.%Y")
    end_dt = datetime.strptime(payload.FinishDate, "%d.%m.%Y") + timedelta(days=1)
    stock_data = _fetch_stock(payload.StartDate, payload.FinishDate)
    sales_data = _fetch_sales(payload.StartDate, payload.FinishDate)
    return _prepare_data(stock_data, sales_data, start_dt, end_dt)


@router.post("/")
def item_analytics(payload: ItemAnalyticsRequest):
    response = requests.post(
        "http://localhost:8005/UserId/",
        headers={"Content-Type": "application/json"},
        json={"token": payload.token},
        timeout=90,
    )
    response.raise_for_status()
    UserId = response.json()
    try:
        if UserId.get("ID") == 1:
            return _get_item_analytics(payload)
    except Exception:
        return {"error": "InvalidId"}
    return {"error": "InvalidId"}