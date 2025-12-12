# app.py - main streamlit app for the Ottawa Date Planner
# this is what the user sees and interacts with
# connects the NLP parser to the planners and displays results
# NOW USES POSTGRESQL DATABASE INSTEAD OF CSV

import streamlit as st
import pandas as pd
import spacy_parser
import heuristic_planner
import ga_planner
import nlp_classifier
import fetch_real_data
import db_manager
import ui_components
from datetime import datetime

# cached so we dont reload the database every time the user clicks something
@st.cache_data
def load_data():
    # loads venue data from PostgreSQL database
    # falls back to CSV if database is not available
    try:
        db_manager.init_db_pool()
        df = db_manager.get_all_venues()
        if df is not None and not df.empty:
            return df
    except Exception as e:
        st.warning(f"Database connection failed: {e}. Trying CSV fallback...")

    # Fallback to CSV
    try:
        df = pd.read_csv('ottawa_venues.csv')
        return df
    except FileNotFoundError:
        return pd.DataFrame()

@st.cache_resource
def load_classifier(df):
    # trains the vibe classifier - cached so we dont retrain every run
    # this was super slow before we added caching
    try:
        vectorizer, clf = nlp_classifier.train_vibe_classifier(df)
        return vectorizer, clf
    except Exception:
        return None, None

def main():
    st.set_page_config(page_title="Ottawa Date Planner", page_icon="❤️")
    
    st.title("Ottawa Date Planner")
    st.markdown("Just tell us what kind of date you want!")

    # sidebar stuff
    st.sidebar.header("Settings")
    planner_type = st.sidebar.radio("Algorithm", ["Heuristic (Greedy)", "Genetic Algorithm"])
    hidden_gem_mode = st.sidebar.checkbox("Hidden gems only", help="Less popular but highly rated spots")

    randomness = st.sidebar.slider(
        "Randomness",
        min_value=0.0,
        max_value=1.0,
        value=0.2,
        step=0.1,
        help="Higher = more variety in results"
    )

    st.subheader("What are you looking for?")

    # some example queries to try
    example_prompts = [
        "romantic dinner under $100",
        "coffee and a museum",
        "casual drinks in the market",
        "fancy french restaurant",
        "something outdoors then lunch"
    ]

    selected_prompt = st.selectbox("Try an example:", [""] + example_prompts)
    
    default_input = "romantic dinner under $100"
    if selected_prompt:
        default_input = selected_prompt

    user_query = st.text_input("Your request:", value=default_input)

    if st.button("Go"):
        with st.spinner("Planning..."):
            # 1. Parse User Request using SpaCy
            try:
                parsed_req = spacy_parser.parse_with_spacy(user_query)
                
                # Format types for display
                target_types_str = ", ".join(parsed_req['target_types']) if parsed_req['target_types'] else "Any"
                target_vibes_str = ", ".join(parsed_req['target_vibes']) if parsed_req['target_vibes'] else "Any"
                
                st.success(
                    f"**Understood:** Vibes=`{target_vibes_str}` | "
                    f"Budget=`${parsed_req['budget_limit']}` | "
                    f"Location=`{parsed_req['location']}` | "
                    f"Stops=`{parsed_req['itinerary_length']}` | "
                    f"Types=`{target_types_str}`"
                )
                
                # Extract parameters for the planner
                target_vibes = parsed_req['target_vibes']
                budget_limit = parsed_req['budget_limit']
                itinerary_length = parsed_req['itinerary_length']
                target_types = parsed_req['target_types']
                location_filter = parsed_req['location']
                semantic_query = parsed_req['semantic_query']
                
                # 2. Load Venue Data
                df = load_data()
                if df.empty:
                    st.error("No data available. Please fetch data first.")
                    return
                
                # 3. Run Selected Planner
                current_dt = datetime.now()
                st.caption(f"Planning for: {current_dt.strftime('%A, %B %d at %I:%M %p')}")
                
                with st.spinner("Searching..."):
                    if planner_type == "Heuristic (Greedy)":
                        plan = heuristic_planner.run_heuristic_search(
                            df, target_vibes, budget_limit,
                            itinerary_length=itinerary_length,
                            location_filter=location_filter,
                            target_types=target_types,
                            hidden_gem=hidden_gem_mode,
                            current_dt=current_dt,
                            semantic_query=semantic_query,
                            randomness=randomness
                        )
                    else:
                        plan = ga_planner.run_genetic_algorithm(
                            df, target_vibes, budget_limit,
                            itinerary_length=itinerary_length,
                            location_filter=location_filter,
                            target_types=target_types,
                            hidden_gem=hidden_gem_mode,
                            current_dt=current_dt,
                            semantic_query=semantic_query,
                            randomness=randomness
                        )
                
                # 4. Display Results
                if not plan:
                    st.warning("Couldn't find anything that fits. Try a higher budget or different vibe?")
                else:
                    st.subheader("Here's what we found")
                    
                    # Calculate total cost
                    total_cost = sum(stop['cost'] for stop in plan)
                    
                    # Budget Progress Bar
                    budget_percent = min(total_cost / budget_limit, 1.0)
                    st.progress(budget_percent)
                    if total_cost > budget_limit:
                        st.warning(f"⚠️ This plan is ${total_cost - budget_limit} over your budget.")
                    
                    # Render Interactive Map
                    ui_components.render_map(plan)

                    # Display Itinerary Timeline
                    for i, stop in enumerate(plan):
                        with st.container():
                            col1, col2 = st.columns([1, 3])
                            with col1:
                                st.markdown(f"### Stop {i+1}")
                                st.caption(stop['type'].upper())
                            with col2:
                                st.markdown(f"**{stop['name']}**")
                                
                                # Display Description or Review Fallback
                                desc = stop['description']
                                if pd.isna(desc) or desc == "No description available.":
                                    if 'review' in stop and not pd.isna(stop['review']) and stop['review'] != "No review available.":
                                        # Truncate review for cleaner display
                                        review_text = stop['review'][:200].replace("\n", " ").strip()
                                        st.write(f"_{review_text}..._ (Review)")
                                    else:
                                        st.write("_No description available._")
                                else:
                                    desc_text = str(desc).replace("\n", " ").strip()
                                    st.write(f"_{desc_text}_")

                                # Display Selection Reason if available
                                if 'selection_reason' in stop:
                                    st.caption(f"**Why here:** {stop['selection_reason']}")

                                st.markdown(f"**Vibe:** {stop['true_vibe']} | **Cost:** ${stop['cost']} | **Rating:** {stop['rating']}⭐")
                            
                        st.divider()
                    
                    st.info(f"**Total Estimated Cost:** ${total_cost}")

            except Exception as e:
                st.error(f"An error occurred: {e}")

    # raw data for debugging
    with st.expander("Show all venues"):
        df = load_data()
        if not df.empty:
            st.dataframe(df)
        else:
            st.write("No data yet")

if __name__ == "__main__":
    main()
