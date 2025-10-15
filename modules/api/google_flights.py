

import streamlit as st
import json
import requests
from datetime import datetime

class SerpApiFlightClient:
    """
    A client to fetch flight data from the SerpApi Google Flights engine.
    """
    BASE_URL = "https://serpapi.com/search.json"

    def __init__(self, api_key):
        """
        Initializes the client with a SerpApi API key.
        
        Args:
            api_key (str): Your SerpApi secret API key.
        """
        if not api_key:
            raise ValueError("API key cannot be empty.")
        self.api_key = api_key

    def get_flight_data(self, departure_id, arrival_id, outbound_date, return_date, currency="INR", gl="in", hl="en"):
        """
        Fetches flight data for a given route and dates.
        
        Returns:
            dict: The JSON response from the API as a dictionary, or None if an error occurs.
        """
        params = {
            "engine": "google_flights",
            "api_key": self.api_key,
            "departure_id": departure_id,
            "arrival_id": arrival_id,
            "outbound_date": outbound_date,
            "return_date": return_date,
            "currency": currency,
            "gl": gl,
            "hl": hl,
            "type": 1,
            "deep_search": "true", # Using string as per API docs
            "sort_by": "2" # Sort by best flights
        }
        
        try:
            response = requests.get(self.BASE_URL, params=params)
            response.raise_for_status()  # Raises an HTTPError for bad responses (4XX or 5XX)
            
            data = response.json()
            if "error" in data:
                st.error(f"SerpApi Error: {data['error']}")
                return None
            return data

        except requests.exceptions.RequestException as e:
            st.error(f"Network error while calling SerpApi: {e}")
            return None
        except json.JSONDecodeError:
            st.error("Failed to decode the JSON response from the API.")
            return None
