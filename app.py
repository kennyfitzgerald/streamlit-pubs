import streamlit as st
import pandas as pd
import sqlite3
import folium
from folium import CustomIcon
from streamlit_folium import folium_static
import os
from geopy.geocoders import Nominatim

# --------------------------------------------------
# Database & Geocoding Functions
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

@st.cache_data(ttl=60)
def search_addresses(query):
    """Return up to 5 (address, lat, lon) suggestions for a given query using Nominatim."""
    geolocator = Nominatim(user_agent="geezer_pubs")
    results = geolocator.geocode(query, exactly_one=False, limit=5)
    if results:
        return [(r.address, r.latitude, r.longitude) for r in results]
    return []

# --------------------------------------------------
# Map Utility Functions
# --------------------------------------------------
def get_main_icon():
    """Return a custom icon for confirmed pub markers."""
    icon_path = os.path.join(os.getcwd(), "static", "geezer_icon.png")
    return CustomIcon(icon_image=icon_path, icon_size=(51, 30))

def create_main_map(df, preview_data=None, center=None):
    """
    Build a folium map that shows:
      - Confirmed pubs from the database (df)
      - One optional preview marker if preview_data is provided.
    """
    if center is None:
        center = [51.5074, -0.1278]

    m = folium.Map(location=center, zoom_start=11)

    # Add markers for confirmed pubs
    for _, row in df.iterrows():
        folium.Marker(
            location=[row["latitude"], row["longitude"]],
            popup=f"{row['name']} - Rating: {row['rating']}",
            icon=get_main_icon(),
        ).add_to(m)

    # Optionally add a preview marker (in orange)
    if preview_data:
        lat, lon, text = preview_data
        folium.Marker(
            location=[lat, lon],
            popup=f"Preview: {text}",
            icon=folium.Icon(color="orange", icon="info-sign"),
        ).add_to(m)

    return m

# --------------------------------------------------
# Streamlit App Setup & Session State Initialization
# --------------------------------------------------
st.set_page_config(page_title="Geezer Pubs of London 🍻", page_icon="🍻", layout="wide")
st.title("Geezer Pubs of London 🍻")
st.write("Explore the best pubs in London and easily add your favorites!")

# Use session state to store preview data and the list of confirmed pubs.
if "preview_lat" not in st.session_state:
    st.session_state["preview_lat"] = None
if "preview_lon" not in st.session_state:
    st.session_state["preview_lon"] = None
if "preview_text" not in st.session_state:
    st.session_state["preview_text"] = None
if "preview_rating" not in st.session_state:
    st.session_state["preview_rating"] = 3.0
if "df_pubs" not in st.session_state:
    st.session_state["df_pubs"] = load_data()

# --------------------------------------------------
# Build and Show the Main Map (Only Once)
# --------------------------------------------------
def build_and_show_map():
    """Build the main map (with a preview marker if set) and display it once."""
    center = None
    preview_data = None

    if st.session_state["preview_lat"] and st.session_state["preview_lon"]:
        center = [st.session_state["preview_lat"], st.session_state["preview_lon"]]
        preview_data = (
            st.session_state["preview_lat"],
            st.session_state["preview_lon"],
            st.session_state["preview_text"],
        )
    elif not st.session_state["df_pubs"].empty:
        last_pub = st.session_state["df_pubs"].iloc[-1]
        center = [last_pub["latitude"], last_pub["longitude"]]

    the_map = create_main_map(st.session_state["df_pubs"], preview_data=preview_data, center=center)
    folium_static(the_map)

# --------------------------------------------------
# Sidebar: Auto-Search and Adding a New Pub
# --------------------------------------------------
st.sidebar.header("Add a New Pub")

# Auto-search: as the user types and presses Enter, the script reruns
address_query = st.sidebar.text_input("Search for an Address", placeholder="e.g., The Volunteer, Tottenham")

if address_query:
    suggestions = search_addresses(address_query)
    if suggestions:
        addresses = [addr for (addr, lat, lon) in suggestions]
        selected_address = st.sidebar.selectbox("Select an Address", addresses)
        # Retrieve lat/lon from suggestions and update preview session state.
        for address, lat, lon in suggestions:
            if address == selected_address:
                st.session_state["preview_lat"] = lat
                st.session_state["preview_lon"] = lon
                st.session_state["preview_text"] = selected_address
                break

        st.session_state["preview_rating"] = st.sidebar.slider(
            "Rating",
            min_value=1.0,
            max_value=5.0,
            value=st.session_state["preview_rating"],
            step=0.5,
        )

        # Confirm addition of the pub; no extra map call here.
        if st.sidebar.button("Add Pub"):
            if (st.session_state["preview_lat"] is not None and
                    st.session_state["preview_lon"] is not None and
                    st.session_state["preview_text"]):
                add_pub_to_db(
                    st.session_state["preview_text"],
                    st.session_state["preview_lat"],
                    st.session_state["preview_lon"],
                    st.session_state["preview_rating"],
                )
                st.sidebar.success(f"Pub added: {st.session_state['preview_text']}")
                # Clear the preview data.
                st.session_state["preview_lat"] = None
                st.session_state["preview_lon"] = None
                st.session_state["preview_text"] = None
                # Update confirmed pubs from the database.
                st.session_state["df_pubs"] = load_data()
    else:
        st.sidebar.warning("No matching addresses found.")

if st.sidebar.button("Clear Preview"):
    st.session_state["preview_lat"] = None
    st.session_state["preview_lon"] = None
    st.session_state["preview_text"] = None
    st.sidebar.info("Preview cleared.")

# --------------------------------------------------
# Finally: Render the Single Main Map
# --------------------------------------------------
build_and_show_map()
