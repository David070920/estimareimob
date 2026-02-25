import streamlit as st
import pandas as pd
import joblib
import folium
from streamlit_folium import st_folium

# 1. Page Config
st.set_page_config(
    page_title="🏢 AI PropTech Evaluator - București",
    layout="wide"
)

st.title("🏢 AI PropTech Evaluator - București")

# 2. UI Layout - Sidebar Inputs
st.sidebar.header("Property Details")
usable_area_sqm = st.sidebar.number_input("Usable Area (sqm)", min_value=15, max_value=250, value=60)
build_year = st.sidebar.slider("Build Year", min_value=1900, max_value=2026, value=1980)
floor = st.sidebar.number_input("Floor (0 for ground floor)", value=1)
total_rooms = st.sidebar.number_input("Total Rooms", min_value=1, max_value=10, value=2)

# 3. Interactive Map (Main Screen)
st.header("📍 Select the exact location of the property on the map.")

# Initialize map centered on Bucharest
m = folium.Map(location=[44.4268, 26.1025], zoom_start=12)

# Render map and capture clicks
map_data = st_folium(m, width=1200, height=500)

# 4. Prediction Logic
if map_data and map_data.get("last_clicked"):
    lat = map_data["last_clicked"]["lat"]
    lng = map_data["last_clicked"]["lng"]
    
    st.write(f"**Selected Coordinates:** Latitude {lat:.6f}, Longitude {lng:.6f}")
    
    if st.button("Predict Price", type="primary", use_container_width=True):
        try:
            # Load the model
            model = joblib.load("xgboost_pricing_model.joblib")
            
            # Create a 1-row DataFrame with the exact 6 columns in the correct order
            input_df = pd.DataFrame([{
                "usable_area_sqm": usable_area_sqm,
                "build_year": build_year,
                "floor": floor,
                "total_rooms": total_rooms,
                "latitude": lat,
                "longitude": lng
            }])
            
            # Call .predict()
            prediction = model.predict(input_df)[0]
            
            # 5. Beautiful Output
            st.success("Prediction successful!")
            st.metric(label="Estimated Price", value=f"€ {prediction:,.0f}")
            
        except FileNotFoundError:
            st.error("Model file 'xgboost_pricing_model.joblib' not found. Please ensure it exists in the same directory.")
        except Exception as e:
            st.error(f"An error occurred during prediction: {e}")
else:
    st.info("Please click on the map to select a location before predicting the price.")
