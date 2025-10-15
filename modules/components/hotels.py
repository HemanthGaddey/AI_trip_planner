import streamlit as st
import requests
from datetime import datetime, timedelta

from modules.api.google_hotels import SerpApiHotelClient

# --- NEW: HELPER FUNCTION TO FIND THE BEST IMAGE ---
def get_stable_image_url(hotel: dict) -> str:
    """
    Intelligently finds the most stable image URL for a hotel.
    
    Args:
        hotel (dict): The hotel data dictionary.

    Returns:
        str: The best available image URL.
    """
    # 1. Prioritize a stable 'original_image' from a known CDN
    for image_data in hotel.get("images", []):
        original_image = image_data.get("original_image")
        if original_image and "googleusercontent.com" not in original_image:
            return original_image  # Found a good, stable URL

    # 2. Fallback to the first available thumbnail in the 'images' list
    # if hotel.get("images"):
    #     first_image = hotel["images"][0]
    #     if first_image.get("thumbnail"):
    #         return first_image["thumbnail"]

    #3. Fallback to the top-level 'thumbnail' (often used in 'ads')
    top_level_thumbnail = hotel.get("thumbnail")
    if top_level_thumbnail:
        return top_level_thumbnail

    # 4. If all else fails, use a generic placeholder
    return "https://static.airasia.com/snap/images/hotel_image_holder.svg"


# --- 2. STREAMLIT DISPLAY COMPONENT (MODIFIED) ---
def display_hotel_results(
        query_input: str,
        check_in_date: datetime.date,
        check_out_date: datetime.date,
        num_adults: int,
        api_key: str,
        max_price: float = None
):
    """
    A self-contained Streamlit component to filter, sort, and display hotel results
    that are stored in st.session_state.
    """
    client = SerpApiHotelClient(api_key=api_key)
    
    with st.spinner(f"Searching for '{query_input}'..."):
        data = client.get_hotel_data(
                query=query_input,
                check_in=check_in_date,
                check_out=check_out_date,
                adults=num_adults
        )
    if not data:
        st.warning("No data to display. Please perform a search.")
        return

    all_properties = data.get("properties", []) + data.get("ads", [])
    if not all_properties:
        st.info("No hotel results found for your search criteria.")
        return
        
    # params = data.get("search_parameters", {})
    # st.header(f"Results for: {params.get('q', 'Your Search')}")
    # st.caption(f"Dates: {params.get('check_in_date')} to {params.get('check_out_date')} for {params.get('adults', 2)} adults.")
    st.divider()

    unique_amenities = set()
    for hotel in all_properties:
        unique_amenities.update(hotel.get("amenities", []))
    sorted_amenities = sorted(list(unique_amenities))

    col1, col2 = st.columns([1, 3])
    with col1:
        sort_option = st.selectbox(
            "Sort by",
            ["Recommended", "Price (Low to High)", "Price (High to Low)", "Rating (High to Low)"],
            key='sort_option'
        )
    with col2:
        selected_amenities = st.multiselect(
            "Filter by amenities (must have all selected)",
            options=sorted_amenities,
            key='amenity_filter'
        )

    def get_price(hotel):
        price_info = hotel.get("rate_per_night", hotel)
        price = price_info.get("extracted_lowest", price_info.get("extracted_price"))
        if(price is None):
            return float('inf')
        return price

    if selected_amenities:
        filtered_list = [
            hotel for hotel in all_properties 
            if set(selected_amenities).issubset(set(hotel.get("amenities", [])))
        ]
    else:
        filtered_list = all_properties

    if sort_option == "Price (Low to High)":
        sorted_list = sorted(filtered_list, key=lambda h: get_price(h) if get_price(h) is not None else float('inf'))
    elif sort_option == "Price (High to Low)":
        sorted_list = sorted(filtered_list, key=lambda h: get_price(h) if get_price(h) is not None else 0, reverse=True)
    elif sort_option == "Rating (High to Low)":
        sorted_list = sorted(filtered_list, key=lambda h: h.get("overall_rating", 0) or 0, reverse=True)
    else:
        sorted_list = filtered_list


    if max_price is not None:
        sorted_list = [
            hotel for hotel in sorted_list
            if (get_price(hotel)!=None and get_price(hotel) <= max_price) or (get_price(hotel)==None)
        ]

    if not sorted_list:
        st.warning("No hotels match your current filter selection.")
        return

    with st.container(border=True, height=800):
        for hotel in sorted_list:
            name = hotel.get("name", "N/A")
            rating = hotel.get("overall_rating")
            reviews = hotel.get("reviews", 0)
            price = get_price(hotel)
            if(price==float('inf')):
                price = None            
            # --- MODIFIED LINE: Use the new helper function ---
            thumbnail_url = get_stable_image_url(hotel)

            with st.container(border=True):
                col1, col2 = st.columns([1, 3])
                with col1:
                    st.image(thumbnail_url, use_column_width='auto', caption=name[:50] + "...")
                    if price:
                        st.metric(label="Price/night", value=f"${price:,.0f}")
                    else:
                        st.metric(label="Price/night", value="N/A")
                with col2:
                    st.subheader(name)
                    if rating and reviews:
                        stars = "⭐" * int(round(rating or 0))
                        st.markdown(f"**{rating:.1f} {stars}** ({reviews:,} reviews)")
                    else:
                        st.caption("No rating available")
                    
                    st.markdown(f"_{hotel.get('description', 'No description available.')}_")
                    amenities = hotel.get("amenities", [])
                    if amenities:
                        with st.expander("View Amenities"):
                            amenity_cols = st.columns(3)
                            for i, amenity in enumerate(amenities[:9]):
                                amenity_cols[i % 3].write(f"• {amenity}")
                st.link_button("View Deal", url=hotel.get("link", "#"))

# --- 3. MAIN STREAMLIT APP ---
# # This section remains unchanged
# st.set_page_config(layout="wide")
# st.title("🏨 Hotel Search Pro")
# st.write("Find the best hotels for your next trip using the power of SerpApi.")

# try:
#     from config import SERPAPI_KEY as API_KEY
# except (KeyError, FileNotFoundError):
#     st.error("SerpApi API key is not found. Please create a .streamlit/secrets.toml file with your key.")
#     st.stop()

# if 'hotel_data' not in st.session_state:
#     st.session_state['hotel_data'] = None

# st.sidebar.header("Find a Hotel")
# query_input = st.sidebar.text_input("Destination or Hotel Name", "Resorts in Bali")
# today = datetime.now().date()
# default_checkin = today + timedelta(days=90)
# default_checkout = default_checkin + timedelta(days=5)

# check_in_date = st.sidebar.date_input("Check-in Date", default_checkin)
# check_out_date = st.sidebar.date_input("Return Date", default_checkout)

# if check_in_date >= check_out_date:
#     st.sidebar.error("Check-out date must be after check-in date.")
#     st.stop()


# display_hotel_results(
#     query_input,
#     check_in_date,
#     check_out_date,
#     num_adults=2,
#     api_key=API_KEY,
# )

# # I want display_hotel_results to be standalone function with all inputs as arguments so that i can just give location, and  currency and everything inlucding using api class, requesting sorting getting hotel components and displaying is all done by single function which i will append as component in my main streamlit application