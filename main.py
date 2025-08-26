from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
from dotenv import load_dotenv
# from routes.holidays import router as HolidaysRouter
# from routes.weather import router as WeatherRouter
# from routes.traffic import router as TrafficRouter
# from routes.competition import router as CompetitionRouter
# from routes.opening_hours import router as OpeningHoursRouter
# from routes.rating import router as RatingRouter
# from routes.income import router as IncomeRouter
# from routes.unemployment import router as UnemploymentRouter
# from routes.SLA import router as SLA
from routes.AuthAPI import router as AuthRouter
# from routes.history import router as History
from routes.UserId import router as UserID
# from routes.getforecast import router as Forcast
# from routes.gethistoryforecast import router as HistoryForecast
# from routes.RegisterAPI import router as AuthRegister
# from routes.StockAndKeeping import router as StockAndKeeping
# from routes.GetItemsCount import router as GetItemsCount
# from routes.GetItemsCountAditionalInfo import router as GetItemsCountAditionalInfo
# from routes.GetListOfStock import router as GetListOfStock
# from routes.GetSupplyInfo import router as GetSupplyInfo
# from routes.GetSupplyInfoHistory import router as GetSupplyInfoHistory
# from routes.OSAcounter import router as OSAcounter
# from routes.DataBaseUpload import router as DataBaseUpload
# from routes.OSAcounterForGroup import router as OSAcounterForGroup
# from routes.GetGroups import router as GetGroups
from routes.GetItemAnalytics import router as GetItemAnalytics
# from routes.StockQuality import router as StockQuality


load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],   
    allow_headers=["*"],   
)

# app.include_router(HolidaysRouter)
# print("Start2")

# app.include_router(WeatherRouter)
# print("Start3")

# app.include_router(TrafficRouter)
# print("Start4")

# app.include_router(CompetitionRouter)
# print("Start5")

# app.include_router(OpeningHoursRouter)
# print("Start6")

# app.include_router(RatingRouter)
# print("Start7")

# app.include_router(IncomeRouter)
# print("Start8")

# app.include_router(UnemploymentRouter)
# print("Start9")

# app.include_router(SLA)
# print("Start10")

# app.include_router(AuthRouter)
# print("Start11")

# app.include_router(History)
# print("Start12")
# app.include_router(UserID)# print("Start13")
# app.include_router(Forcast)
# print("Start14")
# app.include_router(HistoryForecast)
# print("Start15")
# app.include_router(AuthRegister)
# print("Start16")
# app.include_router(StockAndKeeping)
# print("Start17")
# app.include_router(GetItemsCount)
# print("Start18")
# app.include_router(GetItemsCountAditionalInfo)
# print("Start19")
# app.include_router(GetListOfStock)
# print("Start20")
# app.include_router(GetSupplyInfo)
# print("Start21")
# app.include_router(GetSupplyInfoHistory)
# print("Start22")
# app.include_router(OSAcounter)
# print("Start23")
# app.include_router(DataBaseUpload)
# print("Start24")
# app.include_router(OSAcounterForGroup)
# print("Start25")
# app.include_router(GetGroups)
# print("Start26")
# app.include_router(GetItemAnalytics)
# print("Start27")
# app.include_router(StockQuality)
# print("Start28")
app.include_router(UserID)
app.include_router(AuthRouter)
app.include_router(GetItemAnalytics)

@app.get("/")
def read_root():
    return {"Ohh": f"Nothing here..."}
