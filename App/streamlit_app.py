import streamlit as st
import recommendation_system
import sqlite3
import pandas as pd

#streamlit run streamlit_app.py

def recommend_recipe():
    st.title("Recommendation System")
    
    user_id = st.text_input("Enter user id")
    
    if st.button("Get recommendations"):
        if user_id:
            recommendation_system.get_recommendation(user_id)
            
            top_recipe_ids = recommendation_system.df_recipe.nlargest(3, "suggestion_coef")["id"].tolist()
            
            # Connect to the database
            conn = sqlite3.connect('../Data/Supermarket.db')
            
            for recommendation_id in top_recipe_ids:
                # Retrieve the recommended recipe from the database
                query = f"SELECT title, sourceUrl, image, summary, instructions FROM Recipes WHERE id = {recommendation_id};"
                df_recipe = pd.read_sql_query(query, conn)
                
                # Display the recommendation
                if not df_recipe.empty:
                    st.subheader(df_recipe["title"].iloc[0])
                    st.markdown(f"**Source URL:** [{df_recipe['sourceUrl'].iloc[0]}]({df_recipe['sourceUrl'].iloc[0]})")
                    st.image(df_recipe["image"].iloc[0])
                    st.write(df_recipe["summary"].iloc[0], unsafe_allow_html=True)
                    st.empty()  # Add an empty line
                    st.write(df_recipe["instructions"].iloc[0], unsafe_allow_html=True)
                else:
                    st.error("No recommendation found.")
                
                st.markdown("---")  # Add a horizontal line between recommendations
            
            conn.close()
        else:
            st.error("Please enter user id")

# Exécutez l'application Streamlit
if __name__ == "__main__":
    recommend_recipe()
