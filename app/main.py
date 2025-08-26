from __future__ import annotations

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import ORJSONResponse

from numba import set_num_threads

from .analytics import router as analytics_router, warmup_numba
from .auth import router as auth_router
from .userid import router as userid_router


@asynccontextmanager
async def lifespan(app: FastAPI):

    os.environ.setdefault("NUMBA_CPU_NAME", "haswell")
    os.environ.setdefault("NUMBA_THREADING_LAYER", "tbb")

    os.environ.setdefault("NUMBA_NUM_THREADS", "10")

    os.environ.setdefault("OMP_NUM_THREADS", "1")
    os.environ.setdefault("MKL_NUM_THREADS", "1")
    os.environ.setdefault("MKL_DYNAMIC", "FALSE")

    try:
        set_num_threads(int(os.environ.get("NUMBA_NUM_THREADS", "10")))
    except Exception:
        pass

    try:
        warmup_numba()
    except Exception:
        pass

    yield


app = FastAPI(default_response_class=ORJSONResponse, lifespan=lifespan)

app.include_router(auth_router)
app.include_router(userid_router)
app.include_router(analytics_router)
