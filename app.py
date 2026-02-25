import streamlit as st
import pandas as pd
import joblib
import folium
from streamlit_folium import st_folium

# 1. Page Config
st.set_page_config(
    page_title="AI Real Estate Valuator - Romania",
    page_icon="🏠",
    layout="centered"
)

st.title("🏠 AI Real Estate Valuator - Romania")
st.markdown("Estimate the price of an apartment based on its features and location.")

# Load the model (cached to avoid reloading on every interaction)
@st.cache_resource
def load_model():
    return joblib.load("xgboost_pricing_model.joblib")

try:
    model = load_model()
except FileNotFoundError:
    st.error("Model file 'xgboost_pricing_model.joblib' not found. Please ensure it exists in the same directory.")
    st.stop()

# 2. Inputs
st.header("Property Details")
col1, col2 = st.columns(2)

with col1:
    usable_area_sqm = st.number_input("Usable Area (sqm)", min_value=20.0, max_value=300.0, value=50.0, step=1.0)
    floor = st.number_input("Floor (0 for ground floor)", min_value=0, max_value=30, value=2, step=1)
    total_rooms = st.slider("Total Rooms", min_value=1, max_value=10, value=2, step=1)

with col2:
    build_year = st.slider("Build Year", min_value=1900, max_value=2026, value=1980, step=1)

# 3. Map Selection
st.header("Location")
st.info("1. Click on the map to select the exact location of the property.")

# Initialize map centered on Bucharest
m = folium.Map(location=[44.4268, 26.1025], zoom_start=12)

# Render map and capture clicks
map_data = st_folium(m, height=400, width=700)

# 4. Prediction Logic
if map_data and map_data.get("last_clicked"):
    lat = map_data["last_clicked"]["lat"]
    lon = map_data["last_clicked"]["lng"]
    
    st.success(f"Location selected: Latitude {lat:.4f}, Longitude {lon:.4f}")
    
    if st.button("Predict Price", type="primary"):
        with st.spinner("Predicting price..."):
            # Format inputs into a Pandas DataFrame with exact column names
            input_data = pd.DataFrame([{
                "usable_area_sqm": usable_area_sqm,
                "build_year": build_year,
                "floor": floor,
                "total_rooms": total_rooms,
                "latitude": lat,
                "longitude": lon
            }])
            
            # Run prediction
            predicted_price = model.predict(input_data)[0]
            
            # 5. Output
            st.subheader("Estimated Value")
            st.metric(label="Predicted Price", value=f"€ {predicted_price:,.0f}")
