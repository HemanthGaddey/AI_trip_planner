import requests
import certifi
from datetime import datetime, timedelta, date
from modules.api.openweathermap_geocoding import GeocodingClient

class WeatherClient:
    def __init__(self, openweather_api_key: str, api_key: str = None):
        self.api_key = api_key
        self.geocoding_client = GeocodingClient(api_key=openweather_api_key)

    def fetch_weather_data(self, location, start_date, end_date, verify_ssl=True):
        """
        Fetch archived weather data from Open-Meteo API for the given coordinates and date range.
        
        Parameters
        ----------
        location : str
        start_date : str
            Start date in 'YYYY-MM-DD' format.
        end_date : str
            End date in 'YYYY-MM-DD' format.
        verify_ssl : bool, optional
            Whether to verify SSL certificates (default: True).

        Returns
        -------
        dict
            Parsed JSON response containing weather data.

        Raises
        ------
        Exception
            If the request fails or returns a non-200 response.
        """
        coords = self.geocoding_client.get_single_location(location)
        lat, lon = coords['lat'], coords['lon']

        base_url = "https://archive-api.open-meteo.com/v1/archive"

        daily_params = ",".join([
            "sunset", "sunrise", "precipitation_hours", "cloud_cover_mean",
            "temperature_2m_max", "temperature_2m_min", "weather_code",
            "rain_sum", "snowfall_sum"
        ])

        hourly_params = ",".join([
            "temperature_2m", "relative_humidity_2m", "rain", "snowfall",
            "weather_code", "cloud_cover", "wind_speed_100m"
        ])

        url = (
            f"{base_url}?"
            f"latitude={lat}&longitude={lon}"
            f"&start_date={start_date}&end_date={end_date}"
            f"&daily={daily_params}"
            f"&hourly={hourly_params}"
        )

        try:
            res = requests.get(url, verify=certifi.where() if verify_ssl else False)
            res.raise_for_status()
            return res.json()
        except requests.exceptions.SSLError as e:
            raise Exception("SSL verification failed. Try setting verify_ssl=False.") from e
        except requests.exceptions.RequestException as e:
            raise Exception(f"Weather fetch failed: {e}") from e

    def fetch_forecast_data(self, location, start_date, end_date, verify_ssl=True):
        """
        Fetch forecast weather data from the Open-Meteo API for the given coordinates and date range.
        Automatically limits the range to within 16 days from today.

        Parameters
        ----------
        location: str
        start_date : str
            Start date in 'YYYY-MM-DD' format
        end_date : str
            End date in 'YYYY-MM-DD' format
        verify_ssl : bool, optional
            Whether to verify SSL certificates (default: True)

        Returns
        -------
        dict
            { "data": <API JSON or None>, "remarks": <string explanation> }
        """
        coords = self.geocoding_client.get_single_location(location)
        lat, lon = coords['lat'], coords['lon']

        today = date.today()
        start_dt = datetime.strptime(start_date, "%Y-%m-%d").date()
        end_dt = datetime.strptime(end_date, "%Y-%m-%d").date()
        
        # Forecast API provides data for 16 days (today + 15 days into the future)
        max_future = today + timedelta(days=15)
        remarks = []

        if start_dt < today:
            remarks.append(f"Requested start date {start_dt} is in the past; adjusted to {today}.")
            start_dt = today
        if end_dt < start_dt:
            remarks.append("End date is before start date; adjusted to same as start date.")
            end_dt = start_dt
        if end_dt > max_future:
            remarks.append(f"Requested end date {end_dt} exceeds 16-day forecast limit; adjusted to {max_future}.")
            end_dt = max_future

        if start_dt > max_future:
            return {
                "data": None,
                "remarks": f"No forecast data available: dates ({start_date} to {end_date}) are beyond the 16-day limit."
            }

        base_url = "https://api.open-meteo.com/v1/forecast"
        daily_params = ",".join([
            "weather_code", "temperature_2m_max", "temperature_2m_min", "sunrise", "sunset",
            "precipitation_sum", "rain_sum", "showers_sum", "snowfall_sum", "precipitation_hours",
            "precipitation_probability_max", "wind_speed_10m_max", "wind_direction_10m_dominant", "uv_index_max"
        ])
        hourly_params = ",".join([
            "temperature_2m", "relative_humidity_2m", "precipitation_probability", "showers",
            "rain", "snowfall", "cloud_cover", "visibility", "wind_speed_80m"
        ])

        url = (
            f"{base_url}?"
            f"latitude={lat}&longitude={lon}"
            f"&daily={daily_params}"
            f"&hourly={hourly_params}"
            f"&models=best_match"
            f"&start_date={start_dt}&end_date={end_dt}"
            f"&timezone=auto"
        )

        data = None
        try:
            res = requests.get(url, verify=certifi.where() if verify_ssl else False)
            res.raise_for_status()
            data = res.json()
        except requests.exceptions.SSLError as e:
            remarks.append("SSL verification failed; try setting verify_ssl=False.")
        except requests.exceptions.RequestException as e:
            remarks.append(f"API request failed: {e}")

        final_remark = " ".join(remarks) if remarks else "Data fetched successfully for the valid forecast window."
        return {"data": data, "remarks": final_remark}
