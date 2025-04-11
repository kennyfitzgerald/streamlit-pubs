import streamlit as st
import pandas as pd
import sqlite3
import folium
from folium import CustomIcon
from streamlit_folium import folium_static
import os

def get_geezer_icon():
    icon_path = os.path.join(os.getcwd(), "static", "geezer_icon.png")
    geezer_icon = CustomIcon(icon_image=icon_path, icon_size=(51, 30))
    return geezer_icon

def load_data():
    # Connect to the SQLite database
    conn = sqlite3.connect('geezers.db')
    
    # Fetch the data from the 'pubs' table
    query = "SELECT name, latitude, longitude, rating FROM pubs"
    df = pd.read_sql(query, conn)
    
    # Close the connection
    conn.close()
    
    return df

def add_pub_to_db(name, latitude, longitude, rating):
    # Connect to the SQLite database
    conn = sqlite3.connect('geezers.db')
    c = conn.cursor()
    
    # Insert the new pub into the database
    c.execute("INSERT INTO pubs (name, latitude, longitude, rating) VALUES (?, ?, ?, ?)", 
              (name, latitude, longitude, rating))
    
    # Commit the transaction and close the connection
    conn.commit()
    conn.close()

# Initialize the map with existing pubs
def create_map(df):
    m = folium.Map(location=[51.5074, -0.1278], zoom_start=11)
    for _, row in df.iterrows():
        folium.Marker(
            location=[row["latitude"], row["longitude"]],
            popup=f"{row['name']} - Rating: {row['rating']}",
            icon=get_geezer_icon(),
        ).add_to(m)
    return m

df = load_data()

# Title
st.title("Geezer Pubs of London 🍻")
st.markdown("Fosters, Darts, Pool.")

# Create map if it does not exist in session state
if 'map' not in st.session_state:
    st.session_state.map = create_map(df)

# Display the existing map with new markers (not recreated)
folium_static(st.session_state.map)

# Add a section to submit a new pub
st.header("Submit a New Pub")

with st.form(key="pub_form"):
    name = st.text_input("Pub Name", placeholder="Enter Pub Name")
    
    # Manually input latitude and longitude
    latitude = st.number_input("Latitude", format="%.6f", step=0.0001, placeholder="Enter Latitude")
    longitude = st.number_input("Longitude", format="%.6f", step=0.0001, placeholder="Enter Longitude")
    
    # Rating slider
    rating = st.slider("Rating", 1.0, 5.0, 3.0, step=0.5)  # Rating from 1.0 to 5.0, step of 0.5
    
    submit_button = st.form_submit_button("Submit Pub")
    
    if submit_button:
        if name and latitude and longitude:
            # Add the new pub to the database
            add_pub_to_db(name, latitude, longitude, rating)
            
            # Reload data to update the map
            df = load_data()
            
            # Display success message
            st.success(f"Successfully added '{name}' to the map!")
            
            # Update the markers on the existing map (no new map)
            for _, row in df.iterrows():
                folium.Marker(
                    location=[row["latitude"], row["longitude"]],
                    popup=f"{row['name']} - Rating: {row['rating']}",
                    icon=get_geezer_icon(),
                ).add_to(st.session_state.map)

        else:
            st.error("Please fill in all the fields.")
