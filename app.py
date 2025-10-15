import streamlit as st
from datetime import datetime, timedelta
from config import (
    SERPAPI_KEY, 
    AMADEUS_API_KEY, 
    AMADEUS_API_SECRET, 
    OPENWEATHER_API_KEY, 
    TRIPADVISOR_API_KEY,
    GEMINI_API_KEY
)

# corpo ssl issue fix (?)
import os, certifi
os.environ["REQUESTS_CA_BUNDLE"] = certifi.where()
os.environ["SSL_CERT_FILE"] = certifi.where()


from modules.components.flights import display_flight_results
from modules.components.hotels import display_hotel_results
from modules.components.things_to_do import display_things_to_do_results
from modules.api.amadeus import AmadeusClient

# Import the new LLM itinerary component
from itinerary import display_itinerary, display_itinerary_with_alternatives
import os
os.environ["LANGSMITH_TRACING"] = "true"
os.environ["LANGSMITH_ENDPOINT"] = "https://api.smith.langchain.com"
from config import LANGSMITH_API_KEY 
os.environ["LANGSMITH_API_KEY"] = LANGSMITH_API_KEY
os.environ["LANGSMITH_PROJECT"] = "pr-political-driveway-45"


amadeus_client = AmadeusClient(AMADEUS_API_KEY, AMADEUS_API_SECRET, OPENWEATHER_API_KEY)

# --- Page Configuration ---
st.set_page_config(
    page_title="AI Trip Planner",
    page_icon="✈️",
    layout="wide"
)

# --- App Title ---
st.title("AI Trip Planner 🤖✈️🏨")
st.write("Tell us your travel preferences, and our AI will create a personalized day-by-day itinerary with the perfect flights, hotels, and things to do!")

# --- Session State Initialization ---
if 'search_clicked' not in st.session_state:
    st.session_state.search_clicked = False
if 'trip_details' not in st.session_state:
    st.session_state.trip_details = {}
if 'show_detailed_results' not in st.session_state:
    st.session_state.show_detailed_results = False

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
        value=today,
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
        "Max Flight Budget (INR)",
        min_value=1000,
        max_value=500000,
        value=45000,
        step=1000,
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

# --- Planning Mode Selection ---
col_btn1, col_btn2 = st.columns(2)

with col_btn1:
    if st.button("🤖 AI Smart Planner (Recommended)", type="primary", use_container_width=True):
        st.session_state.trip_details = {
            'departure': departure_loc,
            'destination': destination_loc,
            'destination_display': destination_loc,
            'start_date': start_date.strftime('%Y-%m-%d'),
            'end_date': end_date.strftime('%Y-%m-%d'),
            'duration': duration,
            'adults': num_adults,
            'travel_type': travel_type,
            'hotel_budget': budget_per_night,
            'flight_budget': budget_flight,
            
            ## alt names
            'budget_flight':budget_flight,
            'budget_per_night':budget_per_night,
            'budget_hotel':budget_per_night,
        }
        st.session_state.search_clicked = True
        st.session_state.show_detailed_results = False

with col_btn2:
    if st.button("🔍 Detailed Search View", use_container_width=True):
        st.session_state.trip_details = {
            'departure': departure_loc.upper(),
            'destination': destination_loc.upper(),
            'destination_display': destination_loc,
            'start_date': start_date,
            'end_date': end_date,
            'duration': duration,
            'adults': num_adults,
            'travel_type': travel_type,
            'hotel_budget': budget_per_night,
            'flight_budget': budget_flight,

            ## alt names
            'budget_flight':budget_flight,
            'budget_per_night':budget_per_night,
            'budget_hotel':budget_per_night,
        }
        st.session_state.search_clicked = True
        st.session_state.show_detailed_results = True

# --- Results Display ---
if st.session_state.search_clicked:
    details = st.session_state.trip_details
    
    st.header(f"Your Custom Trip Plan to {details['destination_display']}")
    
    # AI Smart Planner Mode
    if not st.session_state.show_detailed_results:
        st.markdown("---")
        st.subheader("🤖 AI-Generated Personalized Itinerary")
        st.write("Our AI analyzes weather, attractions, and your preferences to create the perfect trip plan.")
        
        # Prepare config for LLM
        llm_config = {
            'GEMINI_API_KEY': GEMINI_API_KEY,
            'OPENWEATHER_API_KEY': OPENWEATHER_API_KEY,
            'SERPAPI_KEY': SERPAPI_KEY,
            'TRIPADVISOR_API_KEY': TRIPADVISOR_API_KEY,
            'AMADEUS_API_KEY': AMADEUS_API_KEY,
            'AMADEUS_API_SECRET': AMADEUS_API_SECRET
        }
        
        # Display the AI-generated itinerary with alternatives
        display_itinerary_with_alternatives(details, llm_config)
        
        st.divider()
        
        # Option to view detailed results
        if st.button("📊 View Detailed Search Results", use_container_width=True):
            st.session_state.show_detailed_results = True
            st.rerun()
    
    # Detailed Search Mode
    else:
        # Construct a more descriptive query for hotels
        hotel_query = f"{details['travel_type']} hotels in {details['destination']}"
        
        # --- Weather Display ---
        st.subheader("🌤️ Weather Forecast")
        from modules.components.weather import display_weather_results
        
        display_weather_results(
            openweather_api_key=OPENWEATHER_API_KEY, 
            location=details['destination_display'],
            start_date=details['start_date'] if isinstance(details['start_date'], str) else details['start_date'].strftime('%Y-%m-%d'),
            end_date=details['end_date'] if isinstance(details['end_date'], str) else details['end_date'].strftime('%Y-%m-%d')
        )
        
        st.divider()
        
        # --- Tabs for other results ---
        flights_tab, hotels_tab, things_to_do_tab = st.tabs(["✈️ Flights", "🏨 Hotels", "🗺️ Things to Do"])

        with flights_tab:
            try:
                departure_iata = amadeus_client.find_nearest_airport(details['departure'], specific_get='iataCode')
                arrival_iata = amadeus_client.find_nearest_airport(details['destination'], specific_get='iataCode')
                
                st.info(f"Flying from {departure_iata} to {arrival_iata}")
                
                display_flight_results(
                    api_key=SERPAPI_KEY,
                    departure_id=departure_iata,
                    arrival_id=arrival_iata,
                    outbound_date=details['start_date'] if isinstance(details['start_date'], str) else details['start_date'],
                    return_date=details['end_date'] if isinstance(details['end_date'], str) else details['end_date'],
                    max_price=details['flight_budget']
                )
            except Exception as e:
                st.error(f"Error finding airports: {e}")
                st.info("Try using airport codes like BLR (Bangalore) or BKK (Bangkok)")

        with hotels_tab:
            display_hotel_results(
                query_input=hotel_query,
                check_in_date=details['start_date'],# if isinstance(details['start_date'], datetime) else datetime.strptime(details['start_date'], '%Y-%m-%d').date(),
                check_out_date=details['end_date'],# if isinstance(details['end_date'], datetime) else datetime.strptime(details['end_date'], '%Y-%m-%d').date(),
                num_adults=details['adults'],
                api_key=SERPAPI_KEY,
                max_price=details['hotel_budget']
            )
        
        with things_to_do_tab:
            display_things_to_do_results(
                query_input=details['destination_display'],
                api_key=TRIPADVISOR_API_KEY
            )
        
        st.divider()
        
        # Option to get AI itinerary
        if st.button("🤖 Generate AI Itinerary from Results", use_container_width=True):
            st.session_state.show_detailed_results = False
            st.rerun()

else:
    st.info("Fill in your travel details above and click 'AI Smart Planner' to get an intelligent, personalized itinerary!")
    
    # Show feature highlights
    st.markdown("### ✨ Features")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        #### 🤖 AI-Powered Planning
        - Day-by-day itineraries
        - Weather-based suggestions
        - Personalized recommendations
        """)
    
    with col2:
        st.markdown("""
        #### 🌤️ Smart Weather Analysis
        - Real-time forecasts
        - Alternative destinations
        - Season-appropriate activities
        """)
    
    with col3:
        st.markdown("""
        #### 💰 Budget Optimization
        - Price comparisons
        - Budget-friendly options
        - Cost breakdowns
        """)