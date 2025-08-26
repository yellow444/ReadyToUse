import os
from fastapi import APIRouter
from pydantic import BaseModel
import requests

router = APIRouter(prefix="/UserId", tags=["UserId"])


class UserRequest(BaseModel):
    token: str


@router.post("/")
def get_history_data(payload: UserRequest):
    with open('routes/LogPas.txt', 'r', encoding='utf-8') as file:
        for line in file:
            if payload.token == line.split(' ')[0]:
                return {"ID": int(line.split(' ')[1])}