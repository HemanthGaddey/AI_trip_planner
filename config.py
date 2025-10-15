# config.py
import os
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GOOGLE_CX = os.getenv("GOOGLE_CX")
TRAVEL_API_KEY = os.getenv("TRAVEL_API_KEY")
SERPAPI_KEY=os.getenv("SERPAPI_KEY")
AMADEUS_API_KEY=os.getenv("AMADEUS_API_KEY")
AMADEUS_API_SECRET=os.getenv("AMADEUS_API_SECRET")
TRIPADVISOR_API_KEY=os.getenv("TRIPADVISOR_API_KEY")
LANGSMITH_API_KEY=os.getenv("LANGSMITH_API_KEY")

DEFAULT_UNITS = "metric"  # or "imperial"
WEATHER_CACHE_DIR = os.path.join(BASE_DIR, "data", "weather_cache")
