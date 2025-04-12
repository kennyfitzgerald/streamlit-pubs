import streamlit as st
import pandas as pd
import sqlite3
import folium
from folium import CustomIcon
from streamlit_folium import folium_static
import os
from geopy.geocoders import Nominatim
from shapely.geometry import Point, Polygon

# --------------------------------------------------
# Define the Greater London Polygon
# --------------------------------------------------
# This is a rough rectangular approximation of Greater London's boundaries.
# For more accurate results, replace with the exact polygon coordinates.
GREATER_LONDON_POLYGON = Polygon([
    (-0.5103, 51.2868),  # Southwest corner
    (0.3340, 51.2868),   # Southeast corner
    (0.3340, 51.6919),   # Northeast corner
    (-0.5103, 51.6919)   # Northwest corner
])

def is_within_greater_london(lat, lon):
    """
    Check if a given latitude and longitude are within the Greater London polygon.
    Note: shapely uses (longitude, latitude) as (x,y).
    """
    point = Point(lon, lat)
    return GREATER_LONDON_POLYGON.contains(point)

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
    """
    Return up to 5 (address, lat, lon) suggestions for a given query using Nominatim,
    but filter out any suggestions outside Greater London.
    """
    geolocator = Nominatim(user_agent="geezer_pubs")
    results = geolocator.geocode(query, exactly_one=False, limit=5)
    london_results = []
    if results:
        for r in results:
            if is_within_greater_london(r.latitude, r.longitude):
                london_results.append((r.address, r.latitude, r.longitude))
    return london_results

def parse_pub_name_from_address(full_address):
    """
    Return just the portion of the address before the first comma.
    If there's no comma, return the full address.
    """
    if "," in full_address:
        return full_address.split(",")[0].strip()
    return full_address.strip()

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
        center = [51.5074, -0.1278]  # Default to central London

    m = folium.Map(location=center, zoom_start=11)

    # Add markers for confirmed pubs with visually appealing popups.
    for _, row in df.iterrows():
        try:
            pint_price_val = float(row['pint_price'])
        except (ValueError, TypeError):
            pint_price_val = 0.0

        popup_html = f"""
        <table style="border: none; border-collapse: collapse; width: 100%; font-family: Arial, sans-serif; font-size:14px;">
            <thead>
                <tr>
                    <th colspan="2" style="text-align:left; background-color: #f8f9fa; padding: 5px; border-bottom: 1px solid #ccc;">
                        {row['name']}
                    </th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td style="padding: 5px;"><strong>Pool Table:</strong></td>
                    <td style="padding: 5px;">{row['pool_table']}</td>
                </tr>
                <tr>
                    <td style="padding: 5px;"><strong>Darts:</strong></td>
                    <td style="padding: 5px;">{row['darts']}</td>
                </tr>
                <tr>
                    <td style="padding: 5px;"><strong>Commentary:</strong></td>
                    <td style="padding: 5px;">{row['commentary']}</td>
                </tr>
                <tr>
                    <td style="padding: 5px;"><strong>Fosters/Carling:</strong></td>
                    <td style="padding: 5px;">{row['fosters_carling']}</td>
                </tr>
                <tr>
                    <td style="padding: 5px;"><strong>Pint Price:</strong></td>
                    <td style="padding: 5px;">£{pint_price_val:.2f}</td>
                </tr>
                <tr>
                    <td style="padding: 5px;"><strong>Lock-ins:</strong></td>
                    <td style="padding: 5px;">{row['lock_ins']}</td>
                </tr>
            </tbody>
        </table>
        """
        # Wrap the table in an IFrame to control its size.
        popup = folium.Popup(
            folium.IFrame(html=popup_html, width=250, height=200),
            max_width=300
        )
        
        folium.Marker(
            location=[row["latitude"], row["longitude"]],
            popup=popup,
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
st.title("Geezer Pubs")
st.write("YOU'RE JUST A BAR IN DISGUISE, BAR IN DISGUIIIISEEE")

# Initialize session state variables
if "preview_lat" not in st.session_state:
    st.session_state["preview_lat"] = None
if "preview_lon" not in st.session_state:
    st.session_state["preview_lon"] = None
if "preview_text" not in st.session_state:   # full address
    st.session_state["preview_text"] = None
if "suggested_pub_name" not in st.session_state:
    st.session_state["suggested_pub_name"] = None
if "df_pubs" not in st.session_state:
    st.session_state["df_pubs"] = load_data()
if "new_pub_center" not in st.session_state:
    st.session_state["new_pub_center"] = None
if "confirmed_address" not in st.session_state:  # will store just the suggested pub name
    st.session_state["confirmed_address"] = None

# --------------------------------------------------
# Build and Show the Main Map
# --------------------------------------------------
def build_and_show_map():
    """Build the main map (with a preview marker if set) and display it."""
    center = None
    preview_data = None

    # If a new pub was just added, center on that pub.
    if st.session_state.get("new_pub_center"):
        center = st.session_state["new_pub_center"]
        st.session_state.pop("new_pub_center")
    # If there is still a preview, center on that preview.
    elif st.session_state["preview_lat"] and st.session_state["preview_lon"]:
        center = [st.session_state["preview_lat"], st.session_state["preview_lon"]]
        preview_data = (
            st.session_state["preview_lat"],
            st.session_state["preview_lon"],
            st.session_state["preview_text"],  # full address in preview
        )
    # Otherwise, center on the last confirmed pub.
    elif not st.session_state["df_pubs"].empty:
        last_pub = st.session_state["df_pubs"].iloc[-1]
        center = [last_pub["latitude"], last_pub["longitude"]]

    the_map = create_main_map(
        st.session_state["df_pubs"], 
        preview_data=preview_data, 
        center=center
    )
    folium_static(the_map)

# --------------------------------------------------
# Sidebar: Step 1 - Search and Confirm Address
# --------------------------------------------------
st.sidebar.header("Submit a Geezery Pub")

address_query = st.sidebar.text_input(
    "Search Address",
    placeholder="e.g., The Volunteer, Tottenham"
)

if address_query:
    suggestions = search_addresses(address_query)
    if suggestions:
        addresses = [addr for (addr, lat, lon) in suggestions]
        selected_address = st.sidebar.selectbox("Select an Address", addresses)
        # Update preview session state with the selected address.
        for address, lat, lon in suggestions:
            if address == selected_address:
                st.session_state["preview_lat"] = lat
                st.session_state["preview_lon"] = lon
                st.session_state["preview_text"] = address  # full address
                # Suggest pub name from just the first part of the address
                st.session_state["suggested_pub_name"] = parse_pub_name_from_address(address)
                break
    else:
        st.sidebar.warning("No matching addresses found.")

if st.sidebar.button("Confirm Address"):
    if st.session_state.get("preview_text"):
        # Optionally, check here whether the address is within Greater London.
        if is_within_greater_london(st.session_state["preview_lat"], st.session_state["preview_lon"]):
            # Save the suggested pub name as the "confirmed address"
            st.session_state["confirmed_address"] = st.session_state["suggested_pub_name"]
            st.sidebar.success(f"Address confirmed for: {st.session_state['confirmed_address']}")
        else:
            st.sidebar.error("The selected address is outside Greater London. Please try a different address.")
    else:
        st.sidebar.error("Please select an address before confirming.")

# --------------------------------------------------
# Sidebar: Step 2 - Add Pub Details
# --------------------------------------------------
if st.session_state.get("confirmed_address"):
    st.sidebar.header("Step 2: Add Pub Details")
    pub_name = st.sidebar.text_input(
        "Pub Name (edit if necessary)",
        value=st.session_state["confirmed_address"]
    )
    pool_table = st.sidebar.radio("Pool Table", ("Yes", "No"), index=1)
    darts = st.sidebar.radio("Darts", ("Yes", "No"), index=1)
    commentary = st.sidebar.radio(
        "Commentary",
        ("They get it", "Occasional", "Muted with Shit music on"),
        index=0
    )
    fosters_carling = st.sidebar.radio("Fosters / Carling", ("Yes", "No"), index=1)
    pint_price = st.sidebar.number_input(
        "Price of a Pint",
        value=5.00,
        min_value=0.0,
        step=0.01,
        format="%.2f"
    )
    lock_ins = st.sidebar.radio("Lock-ins", ("Yes", "No"), index=1)
    
    if st.sidebar.button("Add Pub"):
        # Before adding a pub, ensure that the selected location is within Greater London
        if st.session_state["preview_lat"] is None or st.session_state["preview_lon"] is None or not pub_name:
            st.sidebar.error("Error adding pub. Please ensure all necessary info is provided.")
        elif not is_within_greater_london(st.session_state["preview_lat"], st.session_state["preview_lon"]):
            st.sidebar.error("The selected address is outside Greater London. Pub not added.")
        else:
            st.session_state["new_pub_center"] = [
                st.session_state["preview_lat"], 
                st.session_state["preview_lon"]
            ]
            add_pub_to_db(
                pub_name,
                st.session_state["preview_lat"],
                st.session_state["preview_lon"],
                pool_table,
                darts,
                commentary,
                fosters_carling,
                pint_price,
                lock_ins,
            )
            st.sidebar.success(f"Pub added: {pub_name}")
            # Clear everything so the UI resets
            st.session_state["preview_lat"] = None
            st.session_state["preview_lon"] = None
            st.session_state["preview_text"] = None
            st.session_state["suggested_pub_name"] = None
            st.session_state["confirmed_address"] = None
            st.session_state["df_pubs"] = load_data()
            st.rerun()  # Refresh the app
    
    if st.sidebar.button("Clear Preview"):
        st.session_state["preview_lat"] = None
        st.session_state["preview_lon"] = None
        st.session_state["preview_text"] = None
        st.session_state["suggested_pub_name"] = None
        st.session_state["confirmed_address"] = None
        st.sidebar.info("Preview cleared.")

# --------------------------------------------------
# Finally: Render the Main Map
# --------------------------------------------------
build_and_show_map()
