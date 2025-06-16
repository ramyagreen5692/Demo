import pandas as pd
import pickle
import streamlit as st
from sklearn.metrics.pairwise import cosine_similarity

# Load data
cleaned_df = pd.read_csv(r"D:\Swiggy\data\cleaned_data.csv")
encoded_df = pd.read_csv(r"D:\Swiggy\data\encoded_data.csv")

# Load encoder
with open(r"D:\Swiggy\data\encoder.pkl", 'rb') as f:
    city_encoder = pickle.load(f)

# List of unique cuisines
all_cuisines = sorted(set(','.join(cleaned_df['cuisine'].dropna()).split(',')))

# Set Streamlit page config
st.set_page_config(page_title="🍽️ Restaurant Recommender", layout="wide")

# Main title
st.markdown("<h1 style='text-align: center; color: #EF476F;'>🍴 Smart Restaurant Recommender</h1>", unsafe_allow_html=True)
st.markdown("<h4 style='text-align: center; color: #06D6A0;'>Discover your next favorite meal</h4>", unsafe_allow_html=True)
st.markdown("---")

# Sidebar
st.sidebar.markdown("## 🎯 Customize Your Preferences")

selected_city = st.sidebar.selectbox("🏙️ Select City", sorted(cleaned_df['city'].dropna().unique()))
selected_cuisines = st.sidebar.multiselect("🍲 Preferred Cuisines", all_cuisines)
min_rating = st.sidebar.slider("⭐ Minimum Rating", 0.0, 5.0, 3.5, 0.1)
max_cost = st.sidebar.slider("💰 Maximum Cost", 50, 2000, 500, 50)
top_n = st.sidebar.slider("🔝 Number of Recommendations", 1, 20, 5)

# Recommendation logic
# Updated recommendation logic with fallback
def recommend(city, cuisines, rating, cost, top_n):
    try:
        city_encoded = city_encoder.transform([[city]])
    except:
        return pd.DataFrame()

    city_df = pd.DataFrame(city_encoded, columns=city_encoder.get_feature_names_out(['city']))
    cuisine_cols = [col for col in encoded_df.columns if col not in ['rating', 'cost'] and not col.startswith("city_")]
    cuisine_vec = [1 if c in cuisines else 0 for c in cuisine_cols]
    cuisine_df = pd.DataFrame([cuisine_vec], columns=cuisine_cols)

    user_input = pd.DataFrame({'rating': [rating], 'cost': [cost]})
    user_vector = pd.concat([user_input, city_df, cuisine_df], axis=1)
    user_vector = user_vector.reindex(columns=encoded_df.columns, fill_value=0)

    similarity = cosine_similarity(user_vector, encoded_df)[0]
    top_indices = similarity.argsort()[::-1]

    recommended = []
    for idx in top_indices:
        row = cleaned_df.iloc[idx]
        if row['city'] == city and any(c in row['cuisine'] for c in cuisines):
            recommended.append(idx)
        if len(recommended) == top_n:
            break

    return cleaned_df.iloc[recommended][['name', 'city', 'rating', 'cost', 'cuisine', 'address']]

# Display results
if st.sidebar.button("🔍 Recommend"):
    with st.spinner("Finding delicious options for you... 🍽️"):
        results = recommend(selected_city, selected_cuisines, min_rating, max_cost, top_n)

    st.markdown("### 📌 Top Recommended Restaurants:")
    if not results.empty:
        for _, row in results.iterrows():
            st.markdown(f"""
            <div style='background-color:#f2f2f2; padding:15px; border-radius:10px; margin-bottom:15px;
                         box-shadow:2px 2px 8px rgba(0,0,0,0.1); color:black;'>
                <h4 style='color:#0077b6;'>{row['name']}</h4>
                <p><b>📍 Location:</b> {row['city']}<br>
                <b>🍛 Cuisine:</b> {row['cuisine']}<br>
                <b>⭐ Rating:</b> {row['rating']} | <b>💵 Cost for Two:</b> ₹{row['cost']}<br>
                <b>📫 Address:</b> {row['address']}</p>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.warning("⚠️ No matching restaurants found. Try adjusting your preferences.")
