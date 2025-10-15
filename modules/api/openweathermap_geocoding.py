import requests
from typing import Dict, List, Optional


class GeocodingClient:
    """Client for geocoding addresses and city names to coordinates."""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.geocode_url = "http://api.openweathermap.org/geo/1.0/direct"
        self.reverse_url = "http://api.openweathermap.org/geo/1.0/reverse"
    
    def get_coordinates(self, location: str, limit: int = 5) -> List[Dict]:
        """
        Get latitude and longitude for a city name or address.
        
        Args:
            location: City name or address (e.g., "London", "London,UK", "New York,NY,US")
            limit: Maximum number of results to return (default: 5)
            
        Returns:
            List of location dictionaries with coordinates and details
            
        Example:
            >>> client = GeocodingClient()
            >>> results = client.get_coordinates("Paris")
            >>> print(results[0])
            {
                'name': 'Paris',
                'lat': 48.8566969,
                'lon': 2.3514616,
                'country': 'FR',
                'state': 'Île-de-France'
            }
        """
        try:
            params = {
                'q': location,
                'limit': limit,
                'appid': self.api_key
            }
            
            response = requests.get(self.geocode_url, params=params, timeout=10)
            
            if response.status_code != 200:
                raise Exception(f"Geocoding failed: {response.text}")
            
            data = response.json()
            
            if not data:
                raise Exception(f"No results found for location: {location}")
            
            results = []
            for item in data:
                result = {
                    'name': item.get('name'),
                    'lat': item.get('lat'),
                    'lon': item.get('lon'),
                    'country': item.get('country'),
                    'state': item.get('state', ''),
                }
                
                # Add local names if available
                if 'local_names' in item and 'en' in item['local_names']:
                    result['local_name'] = item['local_names']['en']
                
                results.append(result)
            
            return results
            
        except requests.exceptions.RequestException as e:
            raise Exception(f"Network error during geocoding: {e}")
        except Exception as e:
            raise Exception(f"Error getting coordinates: {e}")
    
    def get_single_location(self, location: str) -> Optional[Dict]:
        """
        Get the first (most relevant) result for a location.
        
        client = GeocodingClient(api_key = OPENWEATHER_API_KEY)
        loc = client.get_single_location("bangkok")
        lat,lon = loc['lat'], loc['lon']
        
        Args:
            location: City name or address
            
        Returns:
            Dictionary with location details or None if not found
        """
        try:
            results = self.get_coordinates(location, limit=1)
            return results[0] if results else None
        except Exception as e:
            raise Exception(f"Error getting location: {e}")
    
    def reverse_geocode(self, lat: float, lon: float, limit: int = 5) -> List[Dict]:
        """
        Get location names from coordinates (reverse geocoding).
        
        Args:
            lat: Latitude
            lon: Longitude
            limit: Maximum number of results (default: 5)
            
        Returns:
            List of location dictionaries
        """
        try:
            params = {
                'lat': lat,
                'lon': lon,
                'limit': limit,
                'appid': self.api_key
            }
            
            response = requests.get(self.reverse_url, params=params, timeout=10)
            
            if response.status_code != 200:
                raise Exception(f"Reverse geocoding failed: {response.text}")
            
            data = response.json()
            
            if not data:
                raise Exception(f"No results found for coordinates: ({lat}, {lon})")
            
            results = []
            for item in data:
                result = {
                    'name': item.get('name'),
                    'lat': item.get('lat'),
                    'lon': item.get('lon'),
                    'country': item.get('country'),
                    'state': item.get('state', ''),
                }
                results.append(result)
            
            return results
            
        except requests.exceptions.RequestException as e:
            raise Exception(f"Network error during reverse geocoding: {e}")
        except Exception as e:
            raise Exception(f"Error in reverse geocoding: {e}")
    
    def format_location(self, location_dict: Dict) -> str:
        """
        Format a location dictionary into a readable string.
        
        Args:
            location_dict: Dictionary from get_coordinates or reverse_geocode
            
        Returns:
            Formatted location string
        """
        parts = [location_dict.get('name', '')]
        
        if location_dict.get('state'):
            parts.append(location_dict['state'])
        
        if location_dict.get('country'):
            parts.append(location_dict['country'])
        
        location_str = ', '.join(filter(None, parts))
        coords = f"({location_dict.get('lat')}, {location_dict.get('lon')})"
        
        return f"{location_str} {coords}"


# if __name__ == "__main__":
#     client = GeocodingClient()
    
#     print("\nExample 2: Get single location")
#     location = client.get_single_location("bangkok")
#     if location:
#         print(f"  Tokyo: {location['lat']}, {location['lon']}")
    