import requests
import time
import json


from modules.api.openweathermap_geocoding import GeocodingClient



class AmadeusClient:
    """client for various amadeus api calls like nearest airport
     one which takes lat and lon as input and gives list of airports till 
     max_limit within 0-500km of this coordinates"""
    
    def __init__(self, api_key, api_secret, open_weather_api_key):
        self.api_key = api_key
        self.api_secret = api_secret
        self.token_url = "https://test.api.amadeus.com/v1/security/oauth2/token"
        self.token_cache = {
            "access_token": None,
            "expires_at": 0  # Unix timestamp for when the token expires
        }
        self.geocoding_client = GeocodingClient(api_key=open_weather_api_key)

        self.get_valid_token()


    def get_valid_token(self):
        """
        Retrieves a valid token, either from cache or by fetching a new one.
        """
        # Check if the cached token exists and is not expired
        # We add a 30-second buffer to be safe
        if self.token_cache["access_token"] and time.time() < self.token_cache["expires_at"] - 30:
            print("Using cached token.")
            return self.token_cache["access_token"]

        # If token is invalid or expired, fetch a new one
        print("Token is expired or not found. Fetching a new one...")
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        body = {
            "grant_type": "client_credentials",
            "client_id": self.api_key,
            "client_secret": self.api_secret
        }
        
        try:
            response = requests.post(self.token_url, headers=headers, data=body)
            response.raise_for_status()
            
            # Get the new token and its validity duration (in seconds)
            response_data = response.json()
            new_token = response_data['access_token']
            expires_in = response_data['expires_in']
            
            # Update the cache
            self.token_cache["access_token"] = new_token
            self.token_cache["expires_at"] = time.time() + expires_in
            print("New token fetched and cached successfully!")
            
            return new_token
            
        except requests.exceptions.RequestException as e:
            print(f"Failed to get new access token: {e}")
            # Clear the cache on failure
            self.token_cache["access_token"] = None
            self.token_cache["expires_at"] = 0
            return None

    def find_nearest_airport(self, location: str, specific_get=None):
        """Finds the nearest airport (this function remains the same)."""

        coords = self.geocoding_client.get_single_location(location)
        latitude, longitude = coords['lat'], coords['lon']

        if not self.token_cache["access_token"]:
            print("Cannot search for airport without an access token.")
            return None
            
        API_URL = "https://test.api.amadeus.com/v1/reference-data/locations/airports"
        headers = {"Authorization": f"Bearer {self.token_cache['access_token']}"}
        params = {"latitude": latitude, "longitude": longitude, "radius": 500, "page[limit]": 1}
        
        try:
            response = requests.get(API_URL, headers=headers, params=params)
            response.raise_for_status()
            if specific_get:
                return response.json().get('data', [{}])[0].get(specific_get, 'N/A')
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Airport search failed: {e}")
            return None
        

# EXAMPLE USAGE:
# from modules.api.amadeus import AmadeusClient
# import time

# from config import AMADEUS_API_KEY, AMADEUS_API_SECRET 
# from config import OPENWEATHER_API_KEY

# # --- Main execution to demonstrate caching ---

# if __name__ == "__main__":
#     # Define coordinates for Chennai

#     amadeus_client = AmadeusClient(AMADEUS_API_KEY, AMADEUS_API_SECRET, OPENWEATHER_API_KEY)
#     airport_data = amadeus_client.find_nearest_airport("hyderabad",specific_get='iataCode')
#     if airport_data:
#         print(f"Successfully found nearest airport: {airport_data}\n")

#     # Wait a few seconds to simulate another action
#     time.sleep(5) 