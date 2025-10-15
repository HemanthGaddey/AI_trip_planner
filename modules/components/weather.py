import streamlit as st
import requests
import json
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta, date
from modules.api.open_meteo import WeatherClient

def display_weather_results(
        openweather_api_key,
        location: str,
        start_date: str,
        end_date: str
    ):
    """
    A self-contained Streamlit component to fetch and display weather results from Open-Meteo API.

    Args:
        location (str): The location name (e.g., "New York").
        start_date (str): Start date in 'YYYY-MM-DD' format.
        end_date (str): End date in 'YYYY-MM-DD' format.
        api_key (str): Your API key for geocoding.
    """
    weather_client = WeatherClient(openweather_api_key=openweather_api_key)
    data = weather_client.fetch_forecast_data('Bangalore', '2025-10-10','2025-10-11', verify_ssl=False)
    remarks = data['remarks']
    data = data['data']

    # ------------------------------
    # 🧭 LOCATION INFO
    st.text(remarks)
    st.subheader("📍 Location Info")
    cols = st.columns(4)
    cols[0].metric("Latitude", f"{data['latitude']}° N")
    cols[1].metric("Longitude", f"{data['longitude']}° E")
    cols[2].metric("Elevation", f"{data['elevation']} m")
    cols[3].metric("Timezone", data['timezone'])
    
    st.divider()
    
    # ------------------------------
    # 🌅 DAILY DATA
    st.subheader("🌅 Daily Summary")
    
    daily_df = pd.DataFrame(data["daily"])
    st.dataframe(
        daily_df.rename(columns={
            "time": "Date",
            "sunrise": "Sunrise (GMT)",
            "sunset": "Sunset (GMT)",
            "precipitation_hours": "Precipitation Hours"
        }),
        use_container_width=True,
        hide_index=True
    )
    
    # ------------------------------
    # 🌤️ HOURLY DATA
    st.subheader("🌤️ Hourly Forecast")
    
    hourly_df = pd.DataFrame(data["hourly"])
    hourly_df["time"] = pd.to_datetime(hourly_df["time"], format="mixed").dt.strftime("%H:%M")
    
    # ---- Cards for ranges ----
    st.markdown("### 🔍 Overview")
    col1, col2, col3 = st.columns(3)
    col1.metric("Temperature Range", f"{hourly_df['temperature_2m'].min()} – {hourly_df['temperature_2m'].max()} °C")
    col2.metric("Humidity Range", f"{hourly_df['relative_humidity_2m'].min()} – {hourly_df['relative_humidity_2m'].max()} %")
    col3.metric("Wind Speed Range", f"{hourly_df['wind_speed_80m'].min()} – {hourly_df['wind_speed_80m'].max()} km/h")
    
    # ---- Line Chart for temperature ----
    st.markdown("### 🌡️ Temperature & Rain")
    fig = px.line(
        hourly_df,
        x="time",
        y=["temperature_2m", "rain", "showers"],
        labels={"value": "Value", "time": "Time (GMT)", "variable": "Parameter"},
        title="Temperature, Rain & Showers Over Time"
    )
    st.plotly_chart(fig, use_container_width=True)
    
    # ---- Additional Charts ----
    col1, col2 = st.columns(2)
    
    with col1:
        fig_humidity = px.line(hourly_df, x="time", y="relative_humidity_2m", title="💧 Relative Humidity Over Time")
        st.plotly_chart(fig_humidity, use_container_width=True)
    
    with col2:
        fig_cloud = px.line(hourly_df, x="time", y="cloud_cover", title="☁️ Cloud Cover (%) Over Time")
        st.plotly_chart(fig_cloud, use_container_width=True)
    
    # ---- Detailed Table ----
    with st.expander("📋 Detailed Hourly Data"):
        st.dataframe(hourly_df, use_container_width=True, hide_index=True)
    
    # ------------------------------
    # 📊 Summary remarks
    st.divider()
    st.subheader("🧠 Summary Insights")
    st.markdown("""
    - 🌡️ **Mild temperatures** throughout (20–27°C)  
    - 💧 **High humidity** (70–95%) → expect muggy conditions  
    - ☁️ **Mostly cloudy/overcast**, limited sunshine  
    - 🌦️ **Possible showers** during afternoon and evening  
    - 💨 **Gentle winds**, up to 12 km/h  
    """)
