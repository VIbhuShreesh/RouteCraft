from flask import Flask, render_template, request, jsonify
import pandas as pd
import traceback
import re

app = Flask(__name__)

# Function to parse max from range (e.g., "3-5" -> 5)
def parse_max(value):
    try:
        if pd.isna(value) or str(value).strip().lower() in ['na', 'n/a', '', '-']:
            return None

        # Extract all numeric groups (e.g., 4000 and 7000 from '₹4000–7000')
        nums = re.findall(r'\d+', str(value))
        nums = [int(n) for n in nums]

        return max(nums) if nums else None
    except Exception as e:
        print(f"⚠️ Failed to parse max from: {value} -> {e}")
        return None


# Load and preprocess dataset
try:
    travel_data = pd.read_csv("travel_data2.csv", encoding='ISO-8859-1')

    # Clean column names and string data
    travel_data.columns = travel_data.columns.str.strip()
    for col in travel_data.select_dtypes(include=['object']).columns:
        travel_data[col] = travel_data[col].str.strip()

    # Replace '-' with NaN for cost and days
    travel_data['Estimated_Cost_INR'].replace('-', pd.NA, inplace=True)
    travel_data['Recommended_Days'].replace('-', pd.NA, inplace=True)

    # Drop rows with missing essential fields
    required_columns = ['Destination', 'Nearby_Places', 'Estimated_Cost_INR', 'Recommended_Days', 'Type', 'State']
    travel_data.dropna(subset=required_columns, inplace=True)

    # Normalize destination names
    travel_data['normalized_dest'] = travel_data['Destination'].str.lower().str.strip()
    travel_data['normalized_dest'] = travel_data['normalized_dest'].apply(lambda x: re.sub(r'\s+', ' ', x))

    # Get sorted unique destination list for dropdown
    all_destinations = sorted(travel_data['Destination'].unique().tolist())

    print("✅ Travel data loaded successfully.")

except Exception as e:
    print("❌ Error loading dataset:", e)
    travel_data = pd.DataFrame()
    all_destinations = []

# Home route
@app.route('/')
def home():
    print("Rendering with destinations:", all_destinations)
    return render_template('index.html', destinations=all_destinations)

# Recommendation route
@app.route('/get_recommendations', methods=['POST'])
def get_recommendations():
    try:
        if travel_data.empty:
            return jsonify({'error': 'Travel data is not available.'}), 500

        data = request.get_json()
        destination_input = data.get('destination', '')
        people = data.get('people', '')

        if not destination_input.strip() or not people.strip():
            return jsonify({'error': 'Please provide both destination and number of people.'}), 400

        destination_name = re.sub(r'\s+', ' ', destination_input.strip().lower())
        match = travel_data[travel_data['normalized_dest'] == destination_name]

        if match.empty:
            return jsonify({'error': f"Destination '{destination_input}' not found."}), 404

        result = match.iloc[0]

        # Parse max values from cost and days
        max_cost = parse_max(result['Estimated_Cost_INR'])
        max_days = parse_max(result['Recommended_Days'])

        recommendation = {
            'City': str(result['Destination']),
            'Nearby Tourist Places': str(result['Nearby_Places']),
            'Overall Cost (INR)': f"₹{max_cost}" if max_cost else "Not available",
            'Days': max_days if max_days else "Not available",
            'Type of Place': str(result['Type']),
            'State': str(result['State'])
        }

        return jsonify(recommendation)

    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': f'Internal Server Error: {str(e)}'}), 500

if __name__ == '__main__':
    app.run(debug=True)
