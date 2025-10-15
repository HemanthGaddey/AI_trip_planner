import streamlit as st
import requests
import json
from datetime import datetime, timedelta

from modules.api.google_flights import SerpApiFlightClient

def display_flight_results(api_key, departure_id, arrival_id, outbound_date, return_date, max_price=None):
    """
    A self-contained Streamlit component to fetch and display flight results from SerpApi.

    Args:
        api_key (str): Your SerpApi secret API key.
        departure_id (str): The IATA code for the departure airport (e.g., "CDG").
        arrival_id (str): The IATA code for the arrival airport (e.g., "AUS").
        outbound_date (datetime.date): The outbound travel date.
        return_date (datetime.date): The return travel date.
        max_price (float, optional): Maximum price filter. Flights above this price won't be displayed.
    """

    # --- Nested Helper Functions ---
    def _format_duration(total_minutes):
        if total_minutes is None: return "N/A"
        h = total_minutes // 60
        m = total_minutes % 60
        return f"{h}h {m}m"

    def _format_time(time_str):
        try:
            return datetime.strptime(time_str, "%Y-%m-%d %H:%M").strftime("%H:%M")
        except (ValueError, TypeError):
            return "N/A"

    # --- Component Execution Logic ---
    client = SerpApiFlightClient(api_key=api_key)
    with st.spinner(f"Searching for flights from {departure_id} to {arrival_id}..."):
        data = client.get_flight_data(departure_id, arrival_id, outbound_date, return_date)

    if data:
        params = data.get("search_parameters", {})
        # Safe navigation for airport data
        airports = data.get("airports")
        from_airport = params.get("departure_id")
        to_airport = params.get("arrival_id")
        if airports and isinstance(airports, list) and len(airports) > 0:
            from_airport = airports[0].get("departure", [{}])[0].get("city", from_airport)
            to_airport = airports[0].get("arrival", [{}])[0].get("city", to_airport)
        
        st.header(f"Results: {from_airport} to {to_airport}")
        st.subheader(f"Flights from {params.get('outbound_date')} to {params.get('return_date')}")
        st.divider()

        price_insights = data.get("price_insights")
        if price_insights:
            low, high = price_insights.get('typical_price_range', [0, 0])
            currency = params.get('currency', 'INR')
            col1, col2, col3 = st.columns(3)
            col1.metric("Lowest Price", f"{price_insights.get('lowest_price', 0):,.0f} {currency}")
            col2.metric("Typical Range", f"{low:,.0f} - {high:,.0f} {currency}")
            col3.metric("Price Level", f"{price_insights.get('price_level', 'N/A').title()}")
            st.divider()
        
        # Get all flights
        all_flights = data.get("other_flights", [])
        
        # --- FILTER AND SORT SECTION ---
        filter_col1, filter_col2, filter_col3 = st.columns(3)
        
        with filter_col1:
            sort_by = st.selectbox(
                "Sort by",
                ["Price (Low to High)", "Price (High to Low)", "Duration (Shortest)", "Duration (Longest)"],
                key="sort_flights"
            )
        
        with filter_col2:
            stop_filter = st.multiselect(
                "Number of Stops",
                ["Non-stop", "1 Stop", "2+ Stops"],
                default=["Non-stop", "1 Stop", "2+ Stops"],
                key="stop_filter"
            )
        
        with filter_col3:
            # Get unique airlines from all flights
            all_airlines = set()
            for flight in all_flights:
                for leg in flight.get("flights", []):
                    airline = leg.get("airline")
                    if airline:
                        all_airlines.add(airline)
            
            airline_filter = st.multiselect(
                "Airlines",
                sorted(list(all_airlines)),
                default=sorted(list(all_airlines)),
                key="airline_filter"
            )
        
        st.divider()
        
        # --- APPLY FILTERS ---
        filtered_flights = []
        
        for flight in all_flights:
            # Price filter
            flight_price = flight.get('price', 0)
            if max_price and flight_price > max_price:
                continue
            
            # Stop filter
            num_stops = len(flight.get("layovers", []))
            stop_category = "Non-stop" if num_stops == 0 else ("1 Stop" if num_stops == 1 else "2+ Stops")
            if stop_category not in stop_filter:
                continue
            
            # Airline filter
            flight_airlines = set()
            for leg in flight.get("flights", []):
                airline = leg.get("airline")
                if airline:
                    flight_airlines.add(airline)
            
            if not any(airline in airline_filter for airline in flight_airlines):
                continue
            
            filtered_flights.append(flight)
        
        # --- APPLY SORTING ---
        if sort_by == "Price (Low to High)":
            filtered_flights.sort(key=lambda x: x.get('price', 0))
        elif sort_by == "Price (High to Low)":
            filtered_flights.sort(key=lambda x: x.get('price', 0), reverse=True)
        elif sort_by == "Duration (Shortest)":
            filtered_flights.sort(key=lambda x: x.get('total_duration', float('inf')))
        elif sort_by == "Duration (Longest)":
            filtered_flights.sort(key=lambda x: x.get('total_duration', 0), reverse=True)
        
        # Display count
        st.write(f"**Showing {len(filtered_flights)} of {len(all_flights)} flights**")
        
        if not filtered_flights:
            st.warning("No flights match your filter criteria. Try adjusting your filters.")
            return
        
        # Use Streamlit's native container with a fixed height for scrolling
        with st.container(border=True, height=500):
            for flight_option in filtered_flights:
                with st.container(border=True):
                    cols = st.columns([1, 4, 2])
                    with cols[0]:
                        # Create a dictionary to store unique airlines and their logos
                        unique_airlines = {}
                        for leg in flight_option.get("flights", []):
                            airline_name = leg.get("airline")
                            logo_url = leg.get("airline_logo")
                            if airline_name and logo_url:
                                unique_airlines[airline_name] = logo_url

                        # Display the logos of all unique airlines involved in this option
                        if unique_airlines:
                            for airline, logo in unique_airlines.items():
                                st.image(logo, width=65, caption=airline)
                        else:
                            # Fallback to original behavior if no logos are found in legs
                            st.image(flight_option.get("airline_logo", ""), width=80)

                    with cols[1]:
                        stops = len(flight_option.get("layovers", []))
                        stops_txt = "Non-stop" if stops == 0 else f"{stops} Stop{'s' if stops > 1 else ''}"
                        st.subheader(f"{_format_duration(flight_option.get('total_duration'))} ({stops_txt})")
                        airlines_text = ", ".join(unique_airlines.keys()) if unique_airlines else "N/A"
                        st.write(airlines_text)

                    with cols[2]:
                        price = flight_option.get('price', 0)
                        currency_symbol = "₹" if params.get('currency', 'INR') == 'INR' else "$"
                        st.subheader(f"{currency_symbol}{price:,.0f}")
                        st.caption(flight_option.get('type', 'N/A').title())
                    
                    st.divider()
                    
                    # Get layovers list safely
                    layovers = flight_option.get("layovers", [])
                    
                    for i, leg in enumerate(flight_option.get("flights", [])):
                        leg_cols = st.columns([1, 1, 3])
                        leg_cols[0].write(f"**{_format_time(leg.get('departure_airport', {}).get('time'))}** → **{_format_time(leg.get('arrival_airport', {}).get('time'))}**")
                        leg_cols[0].caption(f"{leg.get('departure_airport', {}).get('id', 'N/A')} → {leg.get('arrival_airport', {}).get('id', 'N/A')}")
                        leg_cols[1].write(f"**{leg.get('airline', 'N/A')}** `{leg.get('flight_number', 'N/A')}`")
                        leg_cols[1].caption(f"🕒 {_format_duration(leg.get('duration'))}")
                        leg_cols[2].caption(f"✈️ {leg.get('airplane', 'N/A')}")
                        
                        # Display layover info after each leg except the last one
                        if i < len(layovers):
                            layover = layovers[i]
                            st.warning(f"🕒 Layover: **{_format_duration(layover.get('duration'))}** in {layover.get('name', 'N/A')} ({layover.get('id', 'N/A')})")
    else:
        st.error("Could not retrieve flight data. Please check your inputs or API key.")
