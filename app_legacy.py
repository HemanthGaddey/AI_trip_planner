import streamlit as st
from datetime import datetime, timedelta
from config import SERPAPI_KEY, AMADEUS_API_KEY, AMADEUS_API_SECRET, OPENWEATHER_API_KEY, TRIPADVISOR_API_KEY

from modules.components.flights import display_flight_results
from modules.components.hotels import display_hotel_results
from modules.components.things_to_do import display_things_to_do_results
from modules.api.amadeus import AmadeusClient

amadeus_client = AmadeusClient(AMADEUS_API_KEY, AMADEUS_API_SECRET, OPENWEATHER_API_KEY)

# --- Page Configuration ---
st.set_page_config(
    page_title="AI Trip Planner",
    page_icon="✈️",
    layout="wide"
)

# --- App Title ---
st.title("AI Trip Planner 🤖✈️🏨")
st.write("Tell us your travel preferences, and we'll find the perfect flights, hotels, and things to do for your next adventure!")

# --- Session State Initialization ---
if 'search_clicked' not in st.session_state:
    st.session_state.search_clicked = False
if 'trip_details' not in st.session_state:
    st.session_state.trip_details = {}

# --- User Inputs ---
st.header("Your Travel Details")

col1, col2, col3 = st.columns(3)

with col1:
    departure_loc = st.text_input("Departure Location", "Bangalore", help="e.g., Bangalore city")
    destination_loc = st.text_input("Destination", "Bangkok", help="e.g., Bangkok city")
    num_adults = st.number_input("Number of Adults", 1, 10, 2)

with col2:
    today = datetime.now().date()
    start_date = st.date_input(
        "Start Date",
        value=today + timedelta(days=90),
        min_value=today
    )
    duration = st.number_input("Trip Duration (nights)", 1, 30, 7)
    end_date = start_date + timedelta(days=duration)
    st.info(f"Your trip ends on: {end_date.strftime('%B %d, %Y')}")

with col3:
    travel_type = st.selectbox(
        "Preferred Travel Type",
        ["Relaxation", "Adventure", "Sightseeing", "Family", "Romantic", "Budget-friendly"]
    )
    budget_flight = st.slider(
        "Max Flight Budget (inr)",
        min_value=1000,
        max_value=500000,
        value=45000,
        step=10,
        format="₹%d"
    )
    budget_per_night = st.slider(
        "Max Hotel Budget ($/night)",
        min_value=50,
        max_value=5000,
        value=250,
        step=10,
        format="$%d"
    )

st.divider()

# --- Search Button ---
if st.button("Plan My Trip!", type="primary", use_container_width=True):
    # Store all inputs in session state to persist them
    st.session_state.trip_details = {
        'departure': departure_loc.upper(),
        'destination': destination_loc.upper(),
        'destination_display': destination_loc,
        'start_date': start_date,
        'end_date': end_date,
        'adults': num_adults,
        'travel_type': travel_type,
        'hotel_budget': budget_per_night,
        'flight_budget': budget_flight
    }
    st.session_state.search_clicked = True

# --- Results Display ---
# This section runs if the search button has been clicked.
# --- Results Display ---
# This section runs if the search button has been clicked.
if st.session_state.search_clicked:
    details = st.session_state.trip_details
    st.header(f"Your Custom Trip Plan to {details['destination']}")
    
    # Construct a more descriptive query for hotels
    hotel_query = f"{details['travel_type']} hotels in {details['destination']}"
    
    # --- Weather Display ---
    st.subheader("🌤️ Weather Forecast")
    from modules.components.weather import display_weather_results
    
    # You'll need to pass the actual destination and dates from trip details
    # Note: You'll need to modify display_weather_results to accept location and date parameters
    # For now, using the hardcoded values from your weather component
    display_weather_results(
        openweather_api_key=OPENWEATHER_API_KEY, 
        location=details['destination_display'],
        start_date=details['start_date'].strftime('%Y-%m-%d'),
        end_date=details['end_date'].strftime('%Y-%m-%d')
    )
    
    st.divider()
    
    # --- Tabs for other results ---
    flights_tab, hotels_tab, things_to_do_tab = st.tabs(["✈️ Flights", "🏨 Hotels", "🗺️ Things to Do"])

    with flights_tab:
        departure_iata = amadeus_client.find_nearest_airport(details['departure'], specific_get='iataCode')
        arrival_iata = amadeus_client.find_nearest_airport(details['destination'], specific_get='iataCode')
        print('FFFFFFFFFFFFFF:', departure_iata, arrival_iata)
        display_flight_results(
            api_key=SERPAPI_KEY,
            departure_id='BLR',
            arrival_id='DMK',
            outbound_date=details['start_date'],
            return_date=details['end_date'],
            max_price=details['flight_budget']
        )

    with hotels_tab:
        display_hotel_results(
            query_input=hotel_query,
            check_in_date=details['start_date'],
            check_out_date=details['end_date'],
            num_adults=details['adults'],
            api_key=SERPAPI_KEY,
            max_price=details['hotel_budget']
        )
    
    with things_to_do_tab:
        display_things_to_do_results(
            query_input=details['destination_display'],
            api_key=TRIPADVISOR_API_KEY
        )

else:
    st.info("Fill in your travel details above and click 'Plan My Trip!' to get started.")