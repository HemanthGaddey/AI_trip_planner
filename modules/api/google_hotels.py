import streamlit as st
import requests
from datetime import datetime, timedelta

class SerpApiHotelClient:
    """
    A client to interact with the SerpApi Google Hotels Search API.
    """
    BASE_URL = "https://serpapi.com/search.json"

    def __init__(self, api_key: str):
        if not api_key:
            raise ValueError("API key cannot be empty.")
        self.api_key = api_key

    def get_hotel_data(self, query: str, check_in: datetime.date, check_out: datetime.date, adults: int = 2):
        
        check_in_obj = datetime.strptime(check_in, "%Y-%m-%d")
        check_out_obj = datetime.strptime(check_out, "%Y-%m-%d")

        params = {
            "engine": "google_hotels",
            "q": query,
            "check_in_date": check_in_obj.strftime("%Y-%m-%d"),
            "check_out_date": check_out_obj.strftime("%Y-%m-%d"),
            "adults": adults,
            "gl": "us",
            "hl": "en",
            "currency": "USD",
            "api_key": self.api_key
        }
        try:
            response = requests.get(self.BASE_URL, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            st.error(f"An error occurred while calling the API: {e}")
            return None
        except ValueError as e:
            st.error(f"Failed to decode API response: {e}")
            return None

