import streamlit as st
import pandas as pd
import sqlite3
import folium
from folium import CustomIcon
from streamlit_folium import folium_static
import os
from geopy.geocoders import Nominatim

# --------------------------------------------------
# Database & Geocoding
# --------------------------------------------------
def load_data():
    """Fetch all pubs from geezers.db into a DataFrame."""
    conn = sqlite3.connect('geezers.db')
    query = "SELECT name, latitude, longitude, rating FROM pubs"
    df = pd.read_sql(query, conn)
    conn.close()
    return df

def add_pub_to_db(name, latitude, longitude, rating):
    """Insert a new pub record into the database."""
    conn = sqlite3.connect('geezers.db')
    c = conn.cursor()
    c.execute(
        "INSERT INTO pubs (name, latitude, longitude, rating) VALUES (?, ?, ?, ?)",
        (name, latitude, longitude, rating)
    )
    conn.commit()
    conn.close()

def search_addresses(query):
    """Return up to 5 (address, lat, lon) suggestions for a given query."""
    geolocator = Nominatim(user_agent="geezer_pubs")
    results = geolocator.geocode(query, exactly_one=False, limit=5)
    if results:
        return [(r.address, r.latitude, r.longitude) for r in results]
    return []

# --------------------------------------------------
# Map Utilities
# --------------------------------------------------
def get_main_icon():
    """Return a custom icon for *confirmed* pub markers."""
    icon_path = os.path.join(os.getcwd(), "static", "geezer_icon.png")
    return CustomIcon(icon_image=icon_path, icon_size=(51, 30))

def create_main_map(df, preview_data=None, center=None):
    """
    Build a single folium map that shows:
    - Confirmed pubs from the database (df)
    - One optional preview marker, if preview_data is set.
    """
    # Default center on London if none provided
    if center is None:
        center = [51.5074, -0.1278]

    # Initialize folium map
    m = folium.Map(location=center, zoom_start=11)

    # Add markers for confirmed pubs (those in the database)
    for _, row in df.iterrows():
        folium.Marker(
            location=[row["latitude"], row["longitude"]],
            popup=f"{row['name']} - Rating: {row['rating']}",
            icon=get_main_icon(),
        ).add_to(m)

    # Optionally add a preview marker (orange) for a new selection
    if preview_data:
        lat, lon, text = preview_data
        folium.Marker(
            location=[lat, lon],
            popup=f"Preview: {text}",
            icon=folium.Icon(color="orange", icon="info-sign"),
        ).add_to(m)

    return m

# --------------------------------------------------
# Streamlit App Setup
# --------------------------------------------------
st.set_page_config(page_title="Geezer Pubs of London 🍻", page_icon="🍻", layout="wide")
st.title("Geezer Pubs of London 🍻")
st.write("Explore the best pubs in London and easily add your favorites!")

# 1) Initialize session state variables for preview
if "preview_lat" not in st.session_state:
    st.session_state["preview_lat"] = None
if "preview_lon" not in st.session_state:
    st.session_state["preview_lon"] = None
if "preview_text" not in st.session_state:
    st.session_state["preview_text"] = None
if "preview_rating" not in st.session_state:
    st.session_state["preview_rating"] = 3.0

# 2) Load the database data
df_pubs = load_data()

# 3) Build a single map at the end, using session state for any preview marker
def build_and_show_map():
    """
    Builds the main map with existing pubs + optional preview marker,
    then displays it exactly once.
    """
    center = None
    preview_data = None

    # If there's a preview lat/lon, center the map on that for clarity.
    if st.session_state["preview_lat"] and st.session_state["preview_lon"]:
        center = [st.session_state["preview_lat"], st.session_state["preview_lon"]]
        preview_data = (
            st.session_state["preview_lat"],
            st.session_state["preview_lon"],
            st.session_state["preview_text"],
        )
    # If no preview location is chosen but we have pubs, we can center on the last pub
    elif not df_pubs.empty:
        last_pub = df_pubs.iloc[-1]
        center = [last_pub["latitude"], last_pub["longitude"]]

    # Create the single map
    the_map = create_main_map(df_pubs, preview_data=preview_data, center=center)
    folium_static(the_map)

# --------------------------------------------------
# Sidebar: Searching and Adding Pubs
# --------------------------------------------------
st.sidebar.header("Add a New Pub")

# --- Step 1: User enters a query
query = st.sidebar.text_input("Search for an Address", placeholder="e.g., The Volunteer Tottenham")

# "Search" button to avoid auto-submitting on Enter
if st.sidebar.button("Search") and query.strip():
    suggestions = search_addresses(query)
    if suggestions:
        # Store them in session state so we can use them outside this if-block
        st.session_state["address_suggestions"] = suggestions
    else:
        st.sidebar.warning("No matching addresses found. Refine your query.")
        if "address_suggestions" in st.session_state:
            del st.session_state["address_suggestions"]

# If we have suggestions stored, present a selectbox
if "address_suggestions" in st.session_state:
    addresses = [addr for (addr, lat, lon) in st.session_state["address_suggestions"]]
    selected_address = st.sidebar.selectbox("Select an Address", addresses)

    # Once selected, retrieve lat/lon
    for address, lat, lon in st.session_state["address_suggestions"]:
        if address == selected_address:
            # Store the preview lat/lon/text in session state
            st.session_state["preview_lat"] = lat
            st.session_state["preview_lon"] = lon
            st.session_state["preview_text"] = selected_address
            break

    # Let the user choose a rating for this pub
    st.session_state["preview_rating"] = st.sidebar.slider(
        "Rating",
        min_value=1.0,
        max_value=5.0,
        value=st.session_state["preview_rating"],
        step=0.5,
    )

    # A button to confirm adding the pub
    if st.sidebar.button("Add Pub"):
        if (st.session_state["preview_lat"] is not None
                and st.session_state["preview_lon"] is not None
                and st.session_state["preview_text"]):
            # Add to DB
            add_pub_to_db(
                st.session_state["preview_text"],
                st.session_state["preview_lat"],
                st.session_state["preview_lon"],
                st.session_state["preview_rating"],
            )
            st.sidebar.success(f"Pub added: {st.session_state['preview_text']}")
            
            # Clear the preview so it doesn't remain orange
            st.session_state["preview_lat"] = None
            st.session_state["preview_lon"] = None
            st.session_state["preview_text"] = None

            # Reload data from DB
            df_pubs = load_data()

            # Clear out the old suggestions
            if "address_suggestions" in st.session_state:
                del st.session_state["address_suggestions"]

        else:
            st.sidebar.error("No valid address selected yet.")

# --------------------------------------------------
# (Optional) Refresh button if you want to reset
# --------------------------------------------------
if st.sidebar.button("Clear Preview"):
    st.session_state["preview_lat"] = None
    st.session_state["preview_lon"] = None
    st.session_state["preview_text"] = None
    if "address_suggestions" in st.session_state:
        del st.session_state["address_suggestions"]
    st.sidebar.info("Preview cleared.")

# --------------------------------------------------
# Finally: Render the Single Map Exactly Once
# --------------------------------------------------
build_and_show_map()
