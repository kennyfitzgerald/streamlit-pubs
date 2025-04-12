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
    query = """
    SELECT name, latitude, longitude, pool_table, darts, commentary, fosters_carling, pint_price, lock_ins 
    FROM pubs
    """
    df = pd.read_sql(query, conn)
    conn.close()
    return df

def add_pub_to_db(name, latitude, longitude, pool_table, darts, commentary, fosters_carling, pint_price, lock_ins):
    """Insert a new pub record into the database."""
    conn = sqlite3.connect('geezers.db')
    c = conn.cursor()
    c.execute(
        "INSERT INTO pubs (name, latitude, longitude, pool_table, darts, commentary, fosters_carling, pint_price, lock_ins) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (name, latitude, longitude, pool_table, darts, commentary, fosters_carling, pint_price, lock_ins)
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
        # Safely convert pint_price to a float; if conversion fails, default to 0.0
        try:
            pint_price_val = float(row['pint_price'])
        except (ValueError, TypeError):
            pint_price_val = 0.0

        popup_text = f"""
        <b>{row['name']}</b><br>
        Pool Table: {row['pool_table']}<br>
        Darts: {row['darts']}<br>
        Commentary: {row['commentary']}<br>
        Fosters/Carling: {row['fosters_carling']}<br>
        Price of a Pint: {pint_price_val:.2f}<br>
        Lock-ins: {row['lock_ins']}
        """
        folium.Marker(
            location=[row["latitude"], row["longitude"]],
            popup=popup_text,
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
st.title("Actual Pubs")
st.write("YOU'RE JUST A BAR IN DISGUISE, BAR IN DISGUIIIISEEE")

# Initialize session state for preview data, confirmed pubs, and new pub center.
if "preview_lat" not in st.session_state:
    st.session_state["preview_lat"] = None
if "preview_lon" not in st.session_state:
    st.session_state["preview_lon"] = None
if "preview_text" not in st.session_state:
    st.session_state["preview_text"] = None
if "df_pubs" not in st.session_state:
    st.session_state["df_pubs"] = load_data()
if "new_pub_center" not in st.session_state:
    st.session_state["new_pub_center"] = None

# --------------------------------------------------
# Build and Show the Main Map (Only Once)
# --------------------------------------------------
def build_and_show_map():
    """Build the main map (with a preview marker if set) and display it once."""
    center = None
    preview_data = None

    # If a new pub was just added, center on that pub.
    if st.session_state.get("new_pub_center"):
        center = st.session_state["new_pub_center"]
        # Clear it once used so that subsequent map builds use the default flow.
        st.session_state.pop("new_pub_center")
    # If there is still a preview, center on that preview.
    elif st.session_state["preview_lat"] and st.session_state["preview_lon"]:
        center = [st.session_state["preview_lat"], st.session_state["preview_lon"]]
        preview_data = (
            st.session_state["preview_lat"],
            st.session_state["preview_lon"],
            st.session_state["preview_text"],
        )
    # Otherwise, center on the last confirmed pub.
    elif not st.session_state["df_pubs"].empty:
        last_pub = st.session_state["df_pubs"].iloc[-1]
        center = [last_pub["latitude"], last_pub["longitude"]]

    the_map = create_main_map(st.session_state["df_pubs"], preview_data=preview_data, center=center)
    folium_static(the_map)

# --------------------------------------------------
# Sidebar: Auto-Search and Adding a New Pub
# --------------------------------------------------
st.sidebar.header("Add a New Pub")

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
    else:
        st.sidebar.warning("No matching addresses found.")

# Wrap the pub details in a form
with st.sidebar.form(key="add_pub_form"):
    pool_table = st.radio("Pool Table", ("Yes", "No"), index=1)
    darts = st.radio("Darts", ("Yes", "No"), index=1)
    commentary = st.radio("Commentary", ("They get it", "Occasional", "Muted with Shit music on"), index=0)
    fosters_carling = st.radio("Fosters / Carling", ("Yes", "No"), index=1)
    pint_price = st.number_input("Price of a Pint", value=5.00, min_value=0.0, step=0.01, format="%.2f")
    lock_ins = st.radio("Lock-ins", ("Yes", "No"), index=1)
    submit_button = st.form_submit_button("Add Pub")

    if submit_button:
        if st.session_state["preview_lat"] is not None and st.session_state["preview_lon"] is not None and st.session_state["preview_text"]:
            # Set the new pub center so that the map recenters on this pub.
            st.session_state["new_pub_center"] = [st.session_state["preview_lat"], st.session_state["preview_lon"]]
            add_pub_to_db(
                st.session_state["preview_text"],
                st.session_state["preview_lat"],
                st.session_state["preview_lon"],
                pool_table,
                darts,
                commentary,
                fosters_carling,
                pint_price,
                lock_ins,
            )
            st.sidebar.success(f"Pub added: {st.session_state['preview_text']}")
            # Clear the preview data from session state to reset the form
            st.session_state["preview_lat"] = None
            st.session_state["preview_lon"] = None
            st.session_state["preview_text"] = None
            # Update confirmed pubs from the database.
            st.session_state["df_pubs"] = load_data()
            # Rerun the app to reset form inputs and update the map
            st.rerun()
        else:
            st.sidebar.error("Please select an address first.")

if st.sidebar.button("Clear Preview"):
    st.session_state["preview_lat"] = None
    st.session_state["preview_lon"] = None
    st.session_state["preview_text"] = None
    st.sidebar.info("Preview cleared.")

# --------------------------------------------------
# Finally: Render the Single Main Map
# --------------------------------------------------
build_and_show_map()
