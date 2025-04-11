import streamlit as st
import pandas as pd
import sqlite3
import folium
from folium import CustomIcon
from streamlit_folium import folium_static
import os

def load_data():
    # Connect to the SQLite database
    conn = sqlite3.connect('geezers.db')
    
    # Fetch the data from the 'pubs' table
    query = "SELECT name, latitude, longitude, rating FROM pubs"
    df = pd.read_sql(query, conn)
    
    # Close the connection
    conn.close()
    
    return df

df = load_data()

st.title("London Pubs Map 🍻")
st.markdown("An interactive map displaying selected pubs in London.")

# Create a custom icon with the local image
icon_path = os.path.join(os.getcwd(), "static", "geezer_icon.png")

# Create the map centered on London
m = folium.Map(location=[51.5074, -0.1278], zoom_start=11)

# Add markers for each pub
for _, row in df.iterrows():
    geezer_icon = CustomIcon(icon_image=icon_path, icon_size=(51, 30))
    folium.Marker(
        location=[row["latitude"], row["longitude"]],
        popup=f"{row['name']} - Rating: {row['rating']}",
        icon=geezer_icon,  # Use the custom icon
    ).add_to(m)

# Display the map in Streamlit
folium_static(m)

# Show the data table if the checkbox is checked
if st.checkbox("Show Data Table"):
    st.dataframe(df)
