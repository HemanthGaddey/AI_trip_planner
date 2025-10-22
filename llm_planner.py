"""
AI Trip Planner using LangGraph and Gemini Flash 2.0
Implements weather-based decision nodes, API integrations, and structured itinerary generation
"""

import os
from typing import TypedDict, List, Dict, Annotated, Optional
from datetime import datetime, timedelta
import json

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StructuredOutputParser, ResponseSchema
from langchain_core.output_parsers.pydantic import PydanticOutputParser
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from pydantic import BaseModel, Field

# Import API clients
from modules.api.open_meteo import WeatherClient
from modules.api.google_flights import SerpApiFlightClient
from modules.api.google_hotels import SerpApiHotelClient
from modules.api.tripadvisor import TripadvisorClient
from modules.api.amadeus import AmadeusClient


# ===================== STATE DEFINITION =====================

class TripState(TypedDict):
    """State object that flows through the graph"""
    # User inputs
    destination: str
    departure: str
    start_date: str
    end_date: str
    duration: int
    adults: int
    budget_flight: float
    budget_hotel: float
    travel_type: str
    
    # Weather data
    weather_data: Optional[Dict]
    weather_favorable: bool
    weather_analysis: str
    alternate_destinations: List[str]
    
    # Search results
    flights: Optional[Dict]
    hotels: Optional[Dict]
    attractions: Optional[Dict]
    
    # Budget analysis
    budget_feasible: bool
    budget_notes: str
    
    # Final itinerary
    itinerary: str
    itinerary_markdown: str
    
    # Control flow
    current_step: str
    messages: List[str]
    needs_replanning: bool


# ===================== PYDANTIC MODELS =====================

class WeatherAnalysis(BaseModel):
    """Weather analysis output"""
    is_favorable: bool = Field(description="Whether weather is favorable for travel")
    summary: str = Field(description="Brief weather summary")
    concerns: List[str] = Field(description="Weather concerns if any")
    recommendations: str = Field(description="Recommendations based on weather")


class AlternateDestinations(BaseModel):
    """Alternate destination suggestions"""
    destinations: List[str] = Field(description="List of 3-5 alternate destinations")
    reasons: List[str] = Field(description="Reasons for each suggestion")


class DayActivity(BaseModel):
    """Single day activity"""
    time: str = Field(description="Time of activity")
    activity: str = Field(description="Activity description")
    location: str = Field(description="Location name")
    duration: str = Field(description="Expected duration")
    notes: str = Field(description="Additional notes or tips")


class DayItinerary(BaseModel):
    """Itinerary for one day"""
    day: int = Field(description="Day number")
    date: str = Field(description="Date in YYYY-MM-DD format")
    theme: str = Field(description="Theme of the day")
    activities: List[DayActivity] = Field(description="List of activities")
    meals: Dict[str, str] = Field(description="Meal suggestions")
    estimated_cost: float = Field(description="Estimated cost for the day")


class FullItinerary(BaseModel):
    """Complete trip itinerary"""
    trip_title: str = Field(description="Trip title")
    destination: str = Field(description="Destination")
    duration: int = Field(description="Number of days")
    daily_plans: List[DayItinerary] = Field(description="Day-wise itinerary")
    total_estimated_cost: float = Field(description="Total estimated cost")
    important_notes: List[str] = Field(description="Important travel notes")


# ===================== LLM PLANNER CLASS =====================

class LLMTripPlanner:
    """Main trip planner orchestrator using LangGraph"""
    
    def __init__(self, config: Dict[str, str]):
        """Initialize with API keys from config"""
        self.gemini_api_key = config.get('GEMINI_API_KEY')
        self.openweather_key = config.get('OPENWEATHER_API_KEY')
        self.serpapi_key = config.get('SERPAPI_KEY')
        self.tripadvisor_key = config.get('TRIPADVISOR_API_KEY')
        self.amadeus_key = config.get('AMADEUS_API_KEY')
        self.amadeus_secret = config.get('AMADEUS_API_SECRET')
        
        # Initialize LLM
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash",
            google_api_key=self.gemini_api_key,
            temperature=0.7
        )
        
        # Initialize API clients
        self.weather_client = WeatherClient(
            openweather_api_key=self.openweather_key,
            api_key=self.openweather_key
        )
        self.flight_client = SerpApiFlightClient(api_key=self.serpapi_key)
        self.hotel_client = SerpApiHotelClient(api_key=self.serpapi_key)
        self.tripadvisor_client = TripadvisorClient(api_key=self.tripadvisor_key)
        self.amadeus_client = AmadeusClient(
            api_key=self.amadeus_key,
            api_secret=self.amadeus_secret,
            open_weather_api_key=self.openweather_key
        )
        
        # Build the graph
        self.graph = self._build_graph()
    
    # ===================== NODE FUNCTIONS =====================
    
    def fetch_weather_node(self, state: TripState) -> TripState:
        """Node: Fetch weather data for destination"""
        print(f"🌤️ Fetching weather for {state['destination']}...")
        
        try:
            # Fetch forecast data
            result = self.weather_client.fetch_forecast_data(
                location=state['destination'],
                start_date=state['start_date'],
                end_date=state['end_date']
            )
            
            state['weather_data'] = result
            state['messages'].append(f"Weather data fetched: {result.get('remarks', 'Success')}")
            state['current_step'] = 'weather_fetched'
            
        except Exception as e:
            state['messages'].append(f"Weather fetch error: {str(e)}")
            state['weather_data'] = None
        
        return state
    
    def analyze_weather_node(self, state: TripState) -> TripState:
        """Node: Analyze weather using LLM"""
        print("🤔 Analyzing weather conditions...")
        
        weather_data = state.get('weather_data')
        if not weather_data or not weather_data.get('data'):
            state['weather_favorable'] = True  # Default to favorable if no data
            state['weather_analysis'] = "Weather data unavailable, proceeding with planning."
            return state
        
        # Create weather summary for LLM
        weather_summary = self._summarize_weather(weather_data['data'])
        
        # LLM prompt for weather analysis
        parser = PydanticOutputParser(pydantic_object=WeatherAnalysis)
        
        prompt = ChatPromptTemplate.from_template(
            """You are a travel weather analyst. Analyze the following weather forecast for a trip.
            
Destination: {destination}
Travel Dates: {start_date} to {end_date}
Travel Type: {travel_type}

Weather Data:
{weather_summary}

Determine if the weather is favorable for this trip. Consider:
- Temperature extremes
- Precipitation
- Severe weather alerts
- Suitability for the travel type (e.g., outdoor activities in rain)

{format_instructions}
"""
        )
        
        chain = prompt | self.llm | parser
        
        try:
            analysis = chain.invoke({
                "destination": state['destination'],
                "start_date": state['start_date'],
                "end_date": state['end_date'],
                "travel_type": state['travel_type'],
                "weather_summary": weather_summary,
                "format_instructions": parser.get_format_instructions()
            })
            
            state['weather_favorable'] = analysis.is_favorable
            state['weather_analysis'] = analysis.summary
            state['messages'].append(f"Weather analysis: {analysis.summary}")
            
        except Exception as e:
            print(f"Weather analysis error: {e}")
            state['weather_favorable'] = True
            state['weather_analysis'] = "Could not analyze weather, proceeding with planning."
        
        state['current_step'] = 'weather_analyzed'
        return state
    
    def suggest_alternates_node(self, state: TripState) -> TripState:
        """Node: Suggest alternate destinations if weather is bad"""
        print("🔄 Suggesting alternate destinations...")
        
        prompt = ChatPromptTemplate.from_template(
            """You are a travel expert. The weather in {destination} is unfavorable during {start_date} to {end_date}.

Weather concerns: {weather_analysis}

Travel preferences:
- Travel type: {travel_type}
- Duration: {duration} days
- Departure from: {departure}

Suggest 3-5 alternate destinations that:
1. Have better weather during these dates
2. Match the travel type and preferences
3. Are accessible from {departure}
4. Offer similar experiences
5. give just city names and no country or anything and that too only in lower case.

Provide the destinations as a JSON list with reasons.

Output format:
{{
    "destinations": ["Destination 1", "Destination 2", ...],
    "reasons": ["Reason for dest 1", "Reason for dest 2", ...]
}}
"""
        )
        
        parser = PydanticOutputParser(pydantic_object=AlternateDestinations)
        chain = prompt | self.llm | parser
        
        try:
            alternates = chain.invoke({
                "destination": state['destination'],
                "start_date": state['start_date'],
                "end_date": state['end_date'],
                "weather_analysis": state['weather_analysis'],
                "travel_type": state['travel_type'],
                "duration": state['duration'],
                "departure": state['departure']
            })
            
            state['alternate_destinations'] = alternates.destinations
            state['messages'].append(f"Suggested alternates: {', '.join(alternates.destinations)}")
            
        except Exception as e:
            print(f"Alternate suggestion error: {e}")
            state['alternate_destinations'] = []
        
        state['needs_replanning'] = True
        state['current_step'] = 'alternates_suggested'
        return state
    
    def search_flights_node(self, state: TripState) -> TripState:
        """Node: Search for flights"""
        print("✈️ Searching for flights...")
        
        try:
            # Get airport codes
            dep_iata = self.amadeus_client.find_nearest_airport(
                state['departure'], 
                specific_get='iataCode'
            )
            arr_iata = self.amadeus_client.find_nearest_airport(
                state['destination'], 
                specific_get='iataCode'
            )
            
            # Search flights
            flight_data = self.flight_client.get_flight_data(
                departure_id=dep_iata,
                arrival_id=arr_iata,
                outbound_date=state['start_date'],
                return_date=state['end_date']
            )
            
            state['flights'] = flight_data
            state['messages'].append(f"Found flights from {dep_iata} to {arr_iata}")
            
        except Exception as e:
            print(f"Flight search error: {e}")
            state['flights'] = None
            state['messages'].append(f"Flight search failed: {str(e)}")
        
        state['current_step'] = 'flights_searched'
        return state
    
    def search_hotels_node(self, state: TripState) -> TripState:
        """Node: Search for hotels"""
        print("🏨 Searching for hotels...")
        
        try:
            query = f"{state['travel_type']} hotels in {state['destination']}"
            
            hotel_data = self.hotel_client.get_hotel_data(
                query=query,
                check_in=datetime.strptime(state['start_date'], '%Y-%m-%d').date(),
                check_out=datetime.strptime(state['end_date'], '%Y-%m-%d').date(),
                adults=state['adults']
            )
            
            state['hotels'] = hotel_data
            state['messages'].append(f"Found hotels in {state['destination']}")
            
        except Exception as e:
            print(f"Hotel search error: {e}")
            state['hotels'] = None
            state['messages'].append(f"Hotel search failed: {str(e)}")
        
        state['current_step'] = 'hotels_searched'
        return state
    
    def search_attractions_node(self, state: TripState) -> TripState:
        """Node: Search for attractions and things to do"""
        print("🗺️ Searching for attractions...")
        
        try:
            attractions_data = self.tripadvisor_client.get_things_to_do(
                query=state['destination']
            )
            
            state['attractions'] = attractions_data
            state['messages'].append(f"Found attractions in {state['destination']}")
            
        except Exception as e:
            print(f"Attractions search error: {e}")
            state['attractions'] = None
            state['messages'].append(f"Attractions search failed: {str(e)}")
        
        state['current_step'] = 'attractions_searched'
        return state
    
    def check_budget_node(self, state: TripState) -> TripState:
        """Node: Check if options fit within budget"""
        print("💰 Checking budget feasibility...")
        
        budget_analysis = []
        total_estimated = 0
        
        # Analyze flight costs
        if state.get('flights'):
            try:
                flights = state['flights'].get('best_flights', [])
                if flights and len(flights) > 0:
                    cheapest_flight = min(flights, key=lambda x: x.get('price', float('inf')))
                    flight_price = cheapest_flight.get('price', 0)
                    total_estimated += flight_price
                    
                    if flight_price > state['budget_flight']:
                        budget_analysis.append(f"Flight cost (₹{flight_price}) exceeds budget (₹{state['budget_flight']})")
                    else:
                        budget_analysis.append(f"Flights within budget: ₹{flight_price}")
            except:
                pass
        
        # Analyze hotel costs
        if state.get('hotels'):
            try:
                hotels = state['hotels'].get('properties', [])
                if hotels and len(hotels) > 0:
                    cheapest_hotel = min(hotels, key=lambda x: x.get('rate_per_night', {}).get('extracted_lowest', float('inf')))
                    hotel_price = cheapest_hotel.get('rate_per_night', {}).get('extracted_lowest', 0)
                    total_hotel = hotel_price * state['duration']
                    total_estimated += total_hotel
                    
                    if hotel_price > state['budget_hotel']:
                        budget_analysis.append(f"Hotel cost (${hotel_price}/night) exceeds budget (${state['budget_hotel']}/night)")
                    else:
                        budget_analysis.append(f"Hotels within budget: ${hotel_price}/night")
            except:
                pass
        
        state['budget_feasible'] = len([a for a in budget_analysis if 'exceeds' in a]) == 0
        state['budget_notes'] = "; ".join(budget_analysis) if budget_analysis else "Budget analysis pending"
        state['messages'].append(f"Budget check: {state['budget_notes']}")
        state['current_step'] = 'budget_checked'
        
        return state
    
    def generate_itinerary_node(self, state: TripState) -> TripState:
        """Node: Generate final itinerary using LLM"""
        print("📝 Generating personalized itinerary...")
        
        # Prepare context for LLM
        context = self._prepare_itinerary_context(state)
        
        prompt = ChatPromptTemplate.from_template(
            """You are an expert travel planner. Create a detailed day-by-day itinerary for the following trip:

{context}

Create a comprehensive itinerary that includes:
1. Day-wise activities with timings
2. Recommended restaurants for meals
3. Travel tips and important notes
4. Estimated costs per day
5. Backup plans for bad weather days

Make it engaging, practical, and tailored to the traveler's preferences.

Write the itinerary in a friendly, informative markdown format suitable for a travel guide.
Include emojis where appropriate to make it visually appealing.
"""
        )
        
        chain = prompt | self.llm
        
        try:
            itinerary = chain.invoke({"context": context})
            state['itinerary_markdown'] = itinerary.content
            state['messages'].append("Itinerary generated successfully")
            
        except Exception as e:
            print(f"Itinerary generation error: {e}")
            state['itinerary_markdown'] = "# Error generating itinerary\n\nPlease try again."
            state['messages'].append(f"Itinerary generation failed: {str(e)}")
        
        state['current_step'] = 'itinerary_generated'
        return state
    
    # ===================== DECISION FUNCTIONS =====================
    
    def should_suggest_alternates(self, state: TripState) -> str:
        """Decision: Check if weather is favorable"""
        if state.get('weather_favorable', True):
            return "proceed_to_search"
        else:
            return "suggest_alternates"
    
    def should_proceed_with_plan(self, state: TripState) -> str:
        """Decision: Check if budget is feasible"""
        # For now, always proceed to generate itinerary
        # In production, you might want to add user confirmation
        return "generate_itinerary"
    
    # ===================== HELPER FUNCTIONS =====================
    
    def _summarize_weather(self, weather_data: Dict) -> str:
        """Create human-readable weather summary"""
        try:
            daily = weather_data.get('daily', {})
            hourly = weather_data.get('hourly', {})
            
            summary_parts = []
            
            if 'temperature_2m_max' in daily:
                temps = daily['temperature_2m_max']
                summary_parts.append(f"Temperatures: {min(temps):.1f}°C to {max(temps):.1f}°C")
            
            if 'rain' in hourly:
                total_rain = sum(hourly['rain'])
                summary_parts.append(f"Total precipitation: {total_rain:.1f}mm")
            
            if 'precipitation_hours' in daily:
                rain_hours = sum(daily['precipitation_hours'])
                summary_parts.append(f"Rainy hours: {rain_hours}")
            
            return "\n".join(summary_parts) if summary_parts else "Weather data summary unavailable"
            
        except Exception as e:
            return f"Weather summary error: {str(e)}"
    
    def _prepare_itinerary_context(self, state: TripState) -> str:
        """Prepare context for itinerary generation"""
        context_parts = [
            f"Destination: {state['destination']}",
            f"Duration: {state['duration']} days ({state['start_date']} to {state['end_date']})",
            f"Travelers: {state['adults']} adults",
            f"Travel Type: {state['travel_type']}",
            f"Budget: Flights ₹{state['budget_flight']}, Hotels ${state['budget_hotel']}/night",
            f"\nWeather: {state.get('weather_analysis', 'Not analyzed')}"
        ]
        
        # Add attractions info
        if state.get('attractions'):
            try:
                attractions = state['attractions'].get('results', [])[:10]
                attr_names = [a.get('title', 'Unknown') for a in attractions]
                context_parts.append(f"\nTop Attractions: {', '.join(attr_names)}")
            except:
                pass
        
        # Add budget notes
        if state.get('budget_notes'):
            context_parts.append(f"\nBudget Analysis: {state['budget_notes']}")
        
        return "\n".join(context_parts)
    
    # ===================== GRAPH BUILDER =====================
    
    def _build_graph(self) -> StateGraph:
        """Build the LangGraph workflow"""
        workflow = StateGraph(TripState)
        
        # Add nodes
        workflow.add_node("fetch_weather", self.fetch_weather_node)
        workflow.add_node("analyze_weather", self.analyze_weather_node)
        workflow.add_node("suggest_alternates", self.suggest_alternates_node)
        workflow.add_node("search_flights", self.search_flights_node)
        workflow.add_node("search_hotels", self.search_hotels_node)
        workflow.add_node("search_attractions", self.search_attractions_node)
        workflow.add_node("check_budget", self.check_budget_node)
        workflow.add_node("generate_itinerary", self.generate_itinerary_node)
        
        # Define edges
        workflow.set_entry_point("fetch_weather")
        
        workflow.add_edge("fetch_weather", "analyze_weather")
        
        # Conditional: weather decision
        workflow.add_conditional_edges(
            "analyze_weather",
            self.should_suggest_alternates,
            {
                "suggest_alternates": "suggest_alternates",
                "proceed_to_search": "search_flights"
            }
        )
        
        # If alternates suggested, end (in production, loop back with new destination)
        workflow.add_edge("suggest_alternates", END)
        
        # Search flow
        workflow.add_edge("search_flights", "search_hotels")
        workflow.add_edge("search_hotels", "search_attractions")
        workflow.add_edge("search_attractions", "check_budget")
        
        # Conditional: budget decision
        workflow.add_conditional_edges(
            "check_budget",
            self.should_proceed_with_plan,
            {
                "generate_itinerary": "generate_itinerary"
            }
        )
        
        workflow.add_edge("generate_itinerary", END)
        
        return workflow.compile()
    
    # ===================== PUBLIC API =====================
    
    def plan_trip(self, trip_details: Dict) -> Dict:
        """
        Main entry point to plan a trip
        
        Args:
            trip_details: Dictionary containing trip parameters
            
        Returns:
            Dictionary with itinerary and metadata
        """
        # Initialize state
        initial_state: TripState = {
            "destination": trip_details['destination'],
            "departure": trip_details['departure'],
            "start_date": trip_details['start_date'],
            "end_date": trip_details['end_date'],
            "duration": trip_details['duration'],
            "adults": trip_details['adults'],
            "budget_flight": trip_details['budget_flight'],
            "budget_hotel": trip_details['budget_hotel'],
            "travel_type": trip_details['travel_type'],
            "weather_data": None,
            "weather_favorable": True,
            "weather_analysis": "",
            "alternate_destinations": [],
            "flights": None,
            "hotels": None,
            "attractions": None,
            "budget_feasible": True,
            "budget_notes": "",
            "itinerary": "",
            "itinerary_markdown": "",
            "current_step": "initialized",
            "messages": [],
            "needs_replanning": False
        }
        
        # Execute graph
        print("🚀 Starting trip planning workflow...")
        final_state = self.graph.invoke(initial_state)
        
        return {
            "success": not final_state.get('needs_replanning', False),
            "itinerary_markdown": final_state.get('itinerary_markdown', ''),
            "weather_favorable": final_state.get('weather_favorable', True),
            "alternate_destinations": final_state.get('alternate_destinations', []),
            "budget_feasible": final_state.get('budget_feasible', True),
            "budget_notes": final_state.get('budget_notes', ''),
            "messages": final_state.get('messages', []),
            "raw_data": {
                "weather": final_state.get('weather_data'),
                "flights": final_state.get('flights'),
                "hotels": final_state.get('hotels'),
                "attractions": final_state.get('attractions')
            }
        }