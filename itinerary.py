"""
Streamlit component for displaying AI-generated itinerary
"""

import streamlit as st
from typing import Dict, Optional
from llm_planner import LLMTripPlanner


def display_itinerary(
    trip_details: Dict,
    config: Dict[str, str],
    show_debug: bool = False
) -> None:
    """
    Display AI-generated trip itinerary in Streamlit
    
    Args:
        trip_details: Dictionary containing:
            - destination (str)
            - departure (str)
            - start_date (str): YYYY-MM-DD format
            - end_date (str): YYYY-MM-DD format
            - duration (int)
            - adults (int)
            - budget_flight (float)
            - budget_hotel (float)
            - travel_type (str)
        config: Dictionary with API keys
        show_debug: Whether to show debug information
    """
    
    # Initialize planner (cached)
    @st.cache_resource
    def get_planner():
        return LLMTripPlanner(config)
    
    try:
        planner = get_planner()
    except Exception as e:
        st.error(f"❌ Failed to initialize planner: {str(e)}")
        return
    
    # Show loading spinner
    with st.spinner("🤖 AI is crafting your perfect itinerary... This may take a minute."):
        try:
            # Run the planning workflow
            result = planner.plan_trip(trip_details)
            
            # Check if replanning needed
            if not result['success']:
                st.warning("⚠️ Weather Alert")
                st.write(f"**Weather Concern:** The weather in {trip_details['destination']} "
                        f"may not be ideal for your travel dates.")
                
                if result['alternate_destinations']:
                    st.info("**🔄 Suggested Alternate Destinations:**")
                    for dest in result['alternate_destinations']:
                        st.write(f"• {dest}")
                    
                    st.write("\n💡 *Tip: Try planning with one of these alternatives for better weather!*")
                else:
                    st.write("Consider adjusting your dates or destination.")
                
                return
            
            # Display main itinerary
            st.markdown("## 🗺️ Your Personalized Itinerary")
            
            # Weather status badge
            col1, col2, col3 = st.columns([1, 1, 2])
            with col1:
                if result['weather_favorable']:
                    st.success("☀️ Good Weather")
                else:
                    st.warning("🌧️ Weather Alert")
            
            with col2:
                if result['budget_feasible']:
                    st.success("💰 Within Budget")
                else:
                    st.info("💵 Budget Check")
            
            # Budget notes
            if result['budget_notes']:
                with st.expander("💰 Budget Analysis"):
                    st.write(result['budget_notes'])
            
            st.divider()
            
            # Display the markdown itinerary
            st.markdown(result['itinerary_markdown'])
            
            st.divider()
            
            # Action buttons
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if st.button("📥 Download Itinerary", use_container_width=True):
                    st.download_button(
                        label="Download as Markdown",
                        data=result['itinerary_markdown'],
                        file_name=f"itinerary_{trip_details['destination'].lower().replace(' ', '_')}.md",
                        mime="text/markdown"
                    )
            
            with col2:
                if st.button("🔄 Regenerate", use_container_width=True):
                    st.cache_resource.clear()
                    st.rerun()
            
            with col3:
                if st.button("📧 Share", use_container_width=True):
                    st.info("📧 Copy the itinerary above to share via email or messaging apps!")
            
            # Debug information (optional)
            if show_debug:
                with st.expander("🔍 Debug Information"):
                    st.json({
                        "messages": result['messages'],
                        "weather_favorable": result['weather_favorable'],
                        "budget_feasible": result['budget_feasible'],
                        "has_flights": result['raw_data']['flights'] is not None,
                        "has_hotels": result['raw_data']['hotels'] is not None,
                        "has_attractions": result['raw_data']['attractions'] is not None
                    })
                    
                    st.subheader("Execution Flow:")
                    for i, msg in enumerate(result['messages'], 1):
                        st.text(f"{i}. {msg}")
        
        except Exception as e:
            st.error("❌ Error Generating Itinerary")
            st.exception(e)
            
            st.info("💡 **Troubleshooting Tips:**")
            st.write("• Check that all API keys are correctly configured")
            st.write("• Ensure the destination name is valid")
            st.write("• Try adjusting the date range")
            st.write("• Check your internet connection")


def display_itinerary_with_alternatives(
    trip_details: Dict,
    config: Dict[str, str]
) -> None:
    """
    Enhanced display that shows alternatives when weather is unfavorable
    
    This version automatically fetches alternatives and displays them alongside
    the main itinerary
    """
    
    st.markdown("## 🧠 AI Trip Planning Assistant")
    
    # Initialize planner
    @st.cache_resource
    def get_planner():
        return LLMTripPlanner(config)
    
    planner = get_planner()
    
    # Create tabs for main plan vs alternatives
    tab1, tab2 = st.tabs(["🎯 Your Itinerary", "🔄 Alternative Options"])
    
    with tab1:
        display_itinerary(trip_details, config, show_debug=False)
    
    with tab2:
        st.write("### Weather-Based Alternatives")
        st.info("If weather conditions aren't ideal, here are some alternative destinations:")
        
        with st.spinner("Finding alternatives..."):
            result = planner.plan_trip(trip_details)
            
            if result.get('alternate_destinations'):
                for dest in result['alternate_destinations']:
                    with st.container():
                        st.write(f"#### 📍 {dest}")
                        if st.button(f"Plan trip to {dest}", key=f"alt_{dest}"):
                            # Update trip details with new destination
                            new_details = trip_details.copy()
                            new_details['destination'] = dest
                            st.session_state.trip_details = new_details
                            st.rerun()
            else:
                st.write("No alternatives needed - weather looks great! ☀️")


def display_compact_itinerary(
    trip_details: Dict,
    config: Dict[str, str]
) -> str:
    """
    Generate and return itinerary as markdown string without full UI
    Useful for integration into other components
    
    Returns:
        str: Markdown formatted itinerary
    """
    planner = LLMTripPlanner(config)
    result = planner.plan_trip(trip_details)
    return result.get('itinerary_markdown', '# Error generating itinerary')


# ===================== HELPER COMPONENTS =====================

def show_planning_progress():
    """Display a progress indicator during planning"""
    progress_steps = [
        "🌤️ Checking weather conditions...",
        "✈️ Finding best flights...",
        "🏨 Searching for hotels...",
        "🗺️ Discovering attractions...",
        "💰 Analyzing budget...",
        "📝 Crafting your itinerary..."
    ]
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    import time
    for i, step in enumerate(progress_steps):
        status_text.text(step)
        progress_bar.progress((i + 1) / len(progress_steps))
        time.sleep(0.5)
    
    status_text.text("✅ Complete!")
    time.sleep(0.5)
    progress_bar.empty()
    status_text.empty()


def display_weather_alert(weather_analysis: str, is_favorable: bool):
    """Display weather alert component"""
    if is_favorable:
        st.success(f"☀️ **Good Weather Ahead!**\n\n{weather_analysis}")
    else:
        st.warning(f"🌧️ **Weather Advisory**\n\n{weather_analysis}")
        st.info("💡 *We've prepared alternatives for you in the 'Alternative Options' tab.*")


def display_budget_breakdown(budget_notes: str, is_feasible: bool):
    """Display budget breakdown component"""
    with st.expander("💰 Budget Breakdown", expanded=not is_feasible):
        if is_feasible:
            st.success("✅ Your trip fits within budget!")
        else:
            st.warning("⚠️ Some options exceed your budget")
        
        st.write(budget_notes)
        
        st.write("\n**Budget Tips:**")
        st.write("• Book flights 2-3 months in advance for better prices")
        st.write("• Consider traveling during shoulder season")
        st.write("• Look for package deals combining flights + hotels")
        st.write("• Use price comparison tools and set price alerts")


# ===================== EXAMPLE USAGE =====================

if __name__ == "__main__":
    # Example configuration
    from config import (
        GEMINI_API_KEY, 
        OPENWEATHER_API_KEY, 
        SERPAPI_KEY,
        TRIPADVISOR_API_KEY,
        AMADEUS_API_KEY,
        AMADEUS_API_SECRET
    )
    
    config = {
        'GEMINI_API_KEY': GEMINI_API_KEY,
        'OPENWEATHER_API_KEY': OPENWEATHER_API_KEY,
        'SERPAPI_KEY': SERPAPI_KEY,
        'TRIPADVISOR_API_KEY': TRIPADVISOR_API_KEY,
        'AMADEUS_API_KEY': AMADEUS_API_KEY,
        'AMADEUS_API_SECRET': AMADEUS_API_SECRET
    }
    
    # Example trip details
    trip_details = {
        'destination': 'Bangkok',
        'departure': 'Bangalore',
        'start_date': '2025-11-01',
        'end_date': '2025-11-08',
        'duration': 7,
        'adults': 2,
        'budget_flight': 45000,
        'budget_hotel': 250,
        'travel_type': 'Sightseeing'
    }
    
    # Display the itinerary
    display_itinerary(trip_details, config, show_debug=True)