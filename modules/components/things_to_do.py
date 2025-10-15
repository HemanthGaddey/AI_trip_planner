import streamlit as st
from modules.api.tripadvisor import TripadvisorClient
from config import TRIPADVISOR_API_KEY

def display_things_to_do_results(query_input: str, api_key: str):
    """
    Initializes the TripadvisorClient, fetches data for a given query,
    and displays the results in a formatted, scrollable Streamlit component.

    Args:
        query_input: The location to search for (e.g., "Bangalore").
        api_key: The SerpApi key for authentication.
    """
    if not query_input:
        st.info("Please enter a location to see things to do.")
        return

    # Show a loading spinner while fetching data
    with st.spinner(f"Finding amazing things to do in {query_input}..."):
        try:
            # 1. Initialize the client
            client = TripadvisorClient(api_key=api_key)
            
            # 2. Get the data
            results = client.get_things_to_do(query_input)
            print(results)
            # 3. Process and display the results
            if not results:
                st.error(f"Sorry, we couldn't find any results for '{query_input}'. Please check the spelling or try a different location.")
                return

            attractions = results.get("locations", [])
            
            if not attractions:
                st.warning(f"No specific 'things to do' were found for '{query_input}'.")
                return

            st.subheader(f"Top Attractions in {query_input.title()}", divider="rainbow")

            # Loop through each result and display it in a formatted card
            for item in attractions:
                with st.container(border=True):
                    col1, col2 = st.columns([1, 3])

                    # --- Image Column ---
                    with col1:  
                        if item.get("thumbnail"):
                            st.image(item["thumbnail"], caption=item.get("title", ""), use_container_width=True)

                    # --- Details Column ---
                    with col2:
                        st.subheader(item.get("title", "No Title Available"))
                        
                        # Display rating and reviews side-by-side
                        sub_col1, sub_col2 = st.columns(2)
                        rating = item.get('rating')
                        if rating:
                            sub_col1.markdown(f"**Rating:** {rating} ⭐")
                        
                        reviews = item.get('reviews')
                        if reviews:
                            sub_col2.markdown(f"**Reviews:** {reviews:,}") # Format with comma

                        # Display categories (types)
                        types = item.get('type', [])
                        if types:
                            st.caption(" &bull; ".join(types))

                        # Display description
                        description=item.get("description", "")
                        if(not description): description = "No description available."
                        with st.expander("Description"):
                            st.write(description)

                        # Display address
                        address = item.get("address")
                        if address:
                             st.markdown(f"📍 *{address}*")
                        
                        # Display link to TripAdvisor page
                        link = item.get("link")
                        if link:
                            st.link_button("View on TripAdvisor", link)

        except Exception as e:
            st.error(f"An unexpected error occurred: {e}")

# # Example usage
# # --- Main Streamlit App Interface ---
# if __name__ == "__main__":
#     st.set_page_config(page_title="TripAdvisor Explorer", layout="centered")

#     st.title("🗺️ TripAdvisor Explorer")
#     st.markdown("Discover the best things to do in any city!")

#     # User input for the location
#     location_query = st.text_input(
#         "Enter a city or location:", 
#         placeholder="e.g., Paris, Bangalore, New York City"
#     )

#     if location_query:
#         # Call the function to display results
#         display_things_to_do_results(query_input=location_query, api_key=TRIPADVISOR_API_KEY)
