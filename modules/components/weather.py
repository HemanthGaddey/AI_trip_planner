import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
from modules.api.open_meteo import WeatherClient
import random
import string

def random_string(length=10):
    chars = string.ascii_letters + string.digits  # A-Z, a-z, 0-9
    return ''.join(random.choice(chars) for _ in range(length))

def get_weather_interpretation(wmo_code):
    """
    Translates WMO weather code to a readable string and an emoji.
    Source: Open-Meteo documentation
    """
    codes = {
        0: ("Clear sky", "☀️"),
        1: ("Mainly clear", "🌤️"),
        2: ("Partly cloudy", "⛅"),
        3: ("Overcast", "☁️"),
        45: ("Fog", "🌫️"),
        48: ("Depositing rime fog", "🌫️"),
        51: ("Light drizzle", "💧"),
        53: ("Moderate drizzle", "💧"),
        55: ("Dense drizzle", "💧"),
        56: ("Light freezing drizzle", "❄️💧"),
        57: ("Dense freezing drizzle", "❄️💧"),
        61: ("Slight rain", "🌧️"),
        63: ("Moderate rain", "🌧️"),
        65: ("Heavy rain", "🌧️"),
        66: ("Light freezing rain", "❄️🌧️"),
        67: ("Heavy freezing rain", "❄️🌧️"),
        71: ("Slight snow fall", "🌨️"),
        73: ("Moderate snow fall", "🌨️"),
        75: ("Heavy snow fall", "🌨️"),
        77: ("Snow grains", "🌨️"),
        80: ("Slight rain showers", "🌦️"),
        81: ("Moderate rain showers", "🌦️"),
        82: ("Violent rain showers", "🌦️"),
        85: ("Slight snow showers", "🌨️"),
        86: ("Heavy snow showers", "🌨️"),
        95: ("Thunderstorm", "⛈️"),
        96: ("Thunderstorm with slight hail", "⛈️"),
        99: ("Thunderstorm with heavy hail", "⛈️"),
    }
    return codes.get(wmo_code, ("Unknown", "❓"))

def display_weather_results(
        openweather_api_key,
        location: str,
        start_date: str,
        end_date: str
    ):
    """
    A self-contained Streamlit component to fetch and display weather results from Open-Meteo API.

    Args:
        openweather_api_key (str): API key for geocoding service.
        location (str): The location name (e.g., "New York").
        start_date (str): Start date in 'YYYY-MM-DD' format.
        end_date (str): End date in 'YYYY-MM-DD' format.
    """
    weather_client = WeatherClient(openweather_api_key=openweather_api_key)
    data_response = weather_client.fetch_forecast_data(location, start_date, end_date, verify_ssl=False)
    
    remarks = data_response.get('remarks')
    data = data_response.get('data')

    if not data:
        st.warning(f"Could not retrieve weather data. Reason: {remarks}")
        return

    # ------------------------------
    # 🧭 LOCATION INFO
    st.info(remarks)
    st.subheader(f"📍 Location: {location.title()}")
    cols = st.columns(4)
    cols[0].metric("Latitude", f"{data.get('latitude', 'N/A')}°")
    cols[1].metric("Longitude", f"{data.get('longitude', 'N/A')}°")
    cols[2].metric("Elevation", f"{data.get('elevation', 'N/A')} m")
    cols[3].metric("Timezone", data.get('timezone', 'N/A'))
    
    st.divider()
    
    # ------------------------------
    # 🌅 DAILY DATA TABLE
    st.subheader("🗓️ Daily Summary")
    
    daily_df = pd.DataFrame(data["daily"])
    
    # --- Generate Stylized Markdown Table ---
    table_style = """
    <style>
        .weather-table {
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 20px;
            font-size: 0.9rem;
        }
        .weather-table th, .weather-table td {
            border: 1px solid #444;
            padding: 8px 10px;
            text-align: center;
        }
        .weather-table th {
            background-color: #0E1117; /* Streamlit dark theme background */
            color: #FAFAFA;
        }
        .weather-table tr:hover {
            background-color: #4A4A58;    
            color: white;
        }
        .weather-icon {
            font-size: 24px;
        }
    </style>
    """
    
    # .weather-table tr:nth-child(even) {
    #     background-color: #2F2F3B;
    # }

    table_header = """
    <table class="weather-table">
        <thead>
            <tr>
                <th>Date</th>
                <th>Conditions</th>
                <th>Temp (Min/Max)</th>
                <th>Rain</th>
                <th>Precip. Chance</th>
                <th>UV Index</th>
                <th>Wind (Max)</th>
                <th>Sunrise / Sunset</th>
            </tr>
        </thead>
        <tbody>
    """
    
    table_rows = ""
    for _, row in daily_df.iterrows():
        date_str = pd.to_datetime(row['time']).strftime('%A, %b %d')
        condition, icon = get_weather_interpretation(row['weather_code'])
        temp_min = row['temperature_2m_min']
        temp_max = row['temperature_2m_max']
        rain_sum = row['rain_sum']
        wind_speed = row['wind_speed_10m_max']
        sunrise = pd.to_datetime(row['sunrise']).strftime('%H:%M')
        sunset = pd.to_datetime(row['sunset']).strftime('%H:%M')
        precip_prob = row['precipitation_probability_max']
        uv_index = row['uv_index_max']

        table_rows += f"""
        <tr>
            <td>{date_str}</td>
            <td><span class="weather-icon">{icon}</span><br>{condition}</td>
            <td>{temp_min}°C / {temp_max}°C</td>
            <td>{rain_sum} mm</td>
            <td>{precip_prob}%</td>
            <td>{uv_index}</td>
            <td>{wind_speed} km/h</td>
            <td>{sunrise} / {sunset}</td>
        </tr>
        """
        
    table_footer = "</tbody></table>"
    
    # Using st.write as it can be more reliable for rendering complex HTML blocks
    st.html(table_style + table_header + table_rows + table_footer)#, unsafe_allow_html=True)

    # ------------------------------
    # 🌤️ HOURLY DATA TABS
    st.subheader("🌤️ Hourly Forecast")
    with st.expander("📋 View Detailed Hourly Data"):

        hourly_df = pd.DataFrame(data["hourly"])
        hourly_df["date"] = pd.to_datetime(hourly_df["time"]).dt.date

        tab_dates = [pd.to_datetime(d).strftime('%a, %b %d') for d in daily_df['time']]
        
        if not tab_dates:
            st.info("No daily data available to display hourly forecasts.")
            return

        tabs = st.tabs(tab_dates)
        
        for i, tab in enumerate(tabs):
            with tab:
                current_date = pd.to_datetime(daily_df['time'][i]).date()
                day_hourly_df = hourly_df[hourly_df["date"] == current_date].copy()
                
                if day_hourly_df.empty:
                    st.write("No hourly data available for this day.")
                    continue

                day_hourly_df["time_formatted"] = pd.to_datetime(day_hourly_df["time"]).dt.strftime("%H:%M")

                st.markdown("##### 🔍 Day Overview")
                col1, col2, col3 = st.columns(3)
                col1.metric("Temp Range", f"{day_hourly_df['temperature_2m'].min()} – {day_hourly_df['temperature_2m'].max()} °C")
                col2.metric("Humidity Range", f"{day_hourly_df['relative_humidity_2m'].min()} – {day_hourly_df['relative_humidity_2m'].max()} %")
                col3.metric("Wind Speed Range", f"{day_hourly_df['wind_speed_80m'].min()} – {day_hourly_df['wind_speed_80m'].max()} km/h")

                st.markdown("##### 🌡️ Temperature & Rain")
                fig = px.line(
                    day_hourly_df, x="time_formatted", y=["temperature_2m", "rain", "showers"],
                    labels={"value": "Value", "time_formatted": "Time (Local)", "variable": "Parameter"},
                    title="Temperature, Rain & Showers"
                )
                st.plotly_chart(fig, use_container_width=True, key=random_string())

                colA, colB = st.columns(2)
                with colA:
                    fig_humidity = px.line(day_hourly_df, x="time_formatted", y="relative_humidity_2m", title="💧 Relative Humidity")
                    st.plotly_chart(fig_humidity, use_container_width=True, key=random_string())
                with colB:
                    fig_cloud = px.line(day_hourly_df, x="time_formatted", y="cloud_cover", title="☁️ Cloud Cover (%)")
                    st.plotly_chart(fig_cloud, use_container_width=True, key=random_string())

                # with st.expander("📋 View Detailed Hourly Data Table"):
                #     display_cols = ['time_formatted', 'temperature_2m', 'relative_humidity_2m', 'rain', 'showers', 'cloud_cover', 'wind_speed_80m']
                #     rename_cols = {'time_formatted': 'Time', 'temperature_2m': 'Temp (°C)', 'relative_humidity_2m': 'Humidity (%)', 'rain': 'Rain (mm)', 'showers': 'Showers (mm)', 'cloud_cover': 'Cloud Cover (%)', 'wind_speed_80m': 'Wind (km/h)'}
                #     st.dataframe(day_hourly_df[display_cols].rename(columns=rename_cols), use_container_width=True, hide_index=True)

