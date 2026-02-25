import asyncio
import pandas as pd
from sqlalchemy import select, func
from sklearn.model_selection import train_test_split
from sklearn.impute import SimpleImputer
from sklearn.metrics import mean_absolute_error, r2_score
from xgboost import XGBRegressor
import joblib

from database import AsyncSessionLocal
from models import Property, Listing
from config import settings

async def fetch_data():
    async with AsyncSessionLocal() as session:
        stmt = select(
            Listing.asking_price_eur,
            Property.usable_area_sqm,
            Property.build_year,
            Property.floor,
            Property.total_rooms,
            func.ST_Y(Property.location).label('latitude'),
            func.ST_X(Property.location).label('longitude')
        ).join(Property, Listing.property_id == Property.id)
        
        result = await session.execute(stmt)
        rows = result.all()
        
        df = pd.DataFrame(rows, columns=[
            'asking_price_eur', 
            'usable_area_sqm', 
            'build_year', 
            'floor', 
            'total_rooms',
            'latitude',
            'longitude'
        ])
        return df

def main():
    print("Fetching data from database...")
    df = asyncio.run(fetch_data())
    
    if df.empty:
        print("No data found in the database. Please ensure the database is populated.")
        return

    print(f"Fetched {len(df)} rows.")

    # Data Preprocessing
    print("Preprocessing data...")
    original_rows = len(df)

    # Drop rows where target or critical features are missing
    df = df.dropna(subset=['asking_price_eur', 'usable_area_sqm'])
    
    # 1. Hard Boundaries
    df = df[
        (df['asking_price_eur'] >= 20000) & (df['asking_price_eur'] <= 750000) &
        (df['usable_area_sqm'] >= 15) & (df['usable_area_sqm'] <= 250) &
        (df['build_year'].isna() | ((df['build_year'] >= 1900) & (df['build_year'] <= 2026)))
    ]

    # 2. Statistical Outlier Removal (IQR) for asking_price_eur
    Q1 = df['asking_price_eur'].quantile(0.25)
    Q3 = df['asking_price_eur'].quantile(0.75)
    IQR = Q3 - Q1
    lower_bound = Q1 - 1.5 * IQR
    upper_bound = Q3 + 1.5 * IQR
    
    df = df[(df['asking_price_eur'] >= lower_bound) & (df['asking_price_eur'] <= upper_bound)]

    final_rows = len(df)
    dropped_rows = original_rows - final_rows
    print(f"Original rows: {original_rows}. Dropped {dropped_rows} outliers. Training on {final_rows} rows.")

    if df.empty:
        print("No data left after cleaning and outlier removal.")
        return

    # Define features and target
    X = df[['usable_area_sqm', 'build_year', 'floor', 'total_rooms', 'latitude', 'longitude']].copy()
    y = df['asking_price_eur']

    # Impute missing values for build_year, floor, total_rooms, latitude, longitude with median
    imputer = SimpleImputer(strategy='median')
    X_imputed = imputer.fit_transform(X)
    
    # Convert back to DataFrame to keep column names
    X = pd.DataFrame(X_imputed, columns=X.columns)

    # Model Training
    print("Splitting data and training model...")
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    model = XGBRegressor(random_state=42)
    model.fit(X_train, y_train)

    # Evaluation
    print("Evaluating model...")
    y_pred = model.predict(X_test)
    
    mae = mean_absolute_error(y_test, y_pred)
    r2 = r2_score(y_test, y_pred)

    print(f"Mean Absolute Error: €{mae:,.0f}")
    print(f"R-squared (R2) Score: {r2:.4f}")

    # Model Serialization
    model_filename = settings.MODEL_SAVE_PATH
    print(f"Saving model to {model_filename}...")
    joblib.dump(model, model_filename)
    print("Done!")

if __name__ == "__main__":
    main()
