import requests
import json

class TripadvisorClient:
    """
    A client to interact with the SerpApi TripAdvisor search engine.
    """
    BASE_URL = "https://serpapi.com/search.json"

    def __init__(self, api_key: str):
        """
        Initializes the TripadvisorClient with a SerpApi API key.

        Args:
            api_key: Your SerpApi API key.
        """
        if not api_key:
            raise ValueError("API key cannot be empty.")
        self.api_key = api_key

    def get_things_to_do(self, query: str):
        """
        Fetches a list of "things to do" for a given location from TripAdvisor via SerpApi.

        Args:
            query: The location to search for (e.g., "Bangalore").

        Returns:
            A dictionary containing the JSON response from the API, or None if the request fails.
        """
        params = {
            "engine": "tripadvisor",
            "q": query,
            "tripadvisor_domain": "www.tripadvisor.in",  # Or any other domain
            "ssrc": "A", # Search source
            "api_key": self.api_key
        }

        try:
            response = requests.get(self.BASE_URL, params=params)
            # Raise an exception for bad status codes (4xx or 5xx)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as http_err:
            print(f"HTTP error occurred: {http_err}")
            print(f"Response content: {response.text}")
        except requests.exceptions.RequestException as req_err:
            print(f"An error occurred during the request: {req_err}")
        except json.JSONDecodeError:
            print("Failed to decode JSON from response.")
            print(f"Response content: {response.text}")

        return None

# Example usage
# if __name__ == '__main__':
#     # --- Example Usage ---
#     # IMPORTANT: Replace "YOUR_API_KEY" with your actual SerpApi key.
#     # You can get a free key from https://serpapi.com/
#     API_KEY = "ffdca1f5145c3cd2b8d01f06bc6029b3ccaf5d34d9f677339409004513f573d0"
    
#     if API_KEY == "YOUR_API_KEY":
#         print("Please replace 'YOUR_API_KEY' with your actual SerpApi key.")
#     else:
#         # 1. Initialize the client
#         client = TripadvisorClient(api_key=API_KEY)

#         # 2. Define the location you want to search for
#         location_query = "bangalore"

#         # 3. Call the method to get things to do
#         print(f"Searching for things to do in '{location_query}'...")
#         things_to_do_data = client.get_things_to_do(location_query)

#         # 4. Print the result
#         if things_to_do_data:
#             print("\nSuccessfully fetched data!")
#             # Pretty-print the JSON response
#             print(json.dumps(things_to_do_data, indent=2, sort_keys=True))
#         else:
#             print("\nFailed to fetch data.")
