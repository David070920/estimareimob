import joblib
import pandas as pd
import sys

def main():
    print("Loading AI Pricing Model...")
    try:
        model = joblib.load('xgboost_pricing_model.joblib')
        print("Model loaded successfully!\n")
    except FileNotFoundError:
        print("Error: 'xgboost_pricing_model.joblib' not found. Please ensure the model is trained and saved.")
        sys.exit(1)

    print("Welcome to the AI Apartment Price Predictor!")
    print("Type 'q' at any prompt to quit.\n")

    while True:
        try:
            # Get Usable Area
            area_input = input("Enter Usable Area (sqm): ")
            if area_input.lower() == 'q':
                break
            usable_area_sqm = float(area_input)

            # Get Build Year
            year_input = input("Enter Build Year (e.g., 2010): ")
            if year_input.lower() == 'q':
                break
            build_year = float(year_input)

            # Get Floor
            floor_input = input("Enter Floor (use 0 for ground floor): ")
            if floor_input.lower() == 'q':
                break
            floor = float(floor_input)

            # Get Total Rooms
            rooms_input = input("Enter Total Rooms: ")
            if rooms_input.lower() == 'q':
                break
            total_rooms = float(rooms_input)

            # Create DataFrame with exact column names used during training
            input_data = pd.DataFrame({
                'usable_area_sqm': [usable_area_sqm],
                'build_year': [build_year],
                'floor': [floor],
                'total_rooms': [total_rooms]
            })

            # Predict
            prediction = model.predict(input_data)[0]

            # Format and print beautifully
            print(f"\n💰 Estimated AI Valuation: €{prediction:,.0f}\n")
            print("-" * 40 + "\n")

        except ValueError:
            print("\n❌ Invalid input! Please enter numeric values only.\n")
        except Exception as e:
            print(f"\n❌ An error occurred: {e}\n")

    print("Exiting predictor. Goodbye!")

if __name__ == "__main__":
    main()
