# ui_components.py
# helper functions for the streamlit UI
# mainly the interactive map for showing the itinerary

import pydeck as pdk
import pandas as pd
import streamlit as st

def render_map(plan):
    # creates an interactive map showing all the stops in the itinerary
    # uses pydeck for the visualization - colored circles based on vibe
    # also draws lines connecting the stops in order

    map_df = pd.DataFrame(plan)

    # make sure we actually have coordinates
    if 'lat' not in map_df.columns or 'lon' not in map_df.columns:
        st.warning("No location data available for map.")
        return

    # colors for each vibe type (RGBA format)
    vibe_colors = {
        'romantic': [255, 105, 180, 200],  # pink
        'outdoor': [34, 139, 34, 200],     # green
        'cozy': [255, 140, 0, 200],        # orange
        'energetic': [255, 215, 0, 200],   # gold
        'fancy': [148, 0, 211, 200],       # purple
        'casual': [30, 144, 255, 200]      # blue
    }

    def get_color(vibe):
        # returns color for a vibe, grey if unknown
        return vibe_colors.get(vibe, [128, 128, 128, 200])

    map_df['color'] = map_df['true_vibe'].apply(get_color)

    # bigger circle = higher rating
    map_df['radius'] = map_df['rating'].fillna(3.0) * 60

    # add stop numbers (1, 2, 3...)
    map_df['label'] = [str(i+1) for i in range(len(map_df))]

    # center the map on the venues
    midpoint = [
        (map_df['lat'].max() + map_df['lat'].min()) / 2,
        (map_df['lon'].max() + map_df['lon'].min()) / 2
    ]

    view_state = pdk.ViewState(
        latitude=midpoint[0],
        longitude=midpoint[1],
        zoom=12,
        pitch=0,
    )

    # the circles for each venue
    layer_points = pdk.Layer(
        "ScatterplotLayer",
        map_df,
        get_position='[lon, lat]',
        get_color='color',
        get_radius='radius',
        radius_min_pixels=20,
        radius_max_pixels=50,
        pickable=True,
    )

    # the numbers on each circle
    layer_text = pdk.Layer(
        "TextLayer",
        map_df,
        get_position='[lon, lat]',
        get_text='label',
        get_color=[0, 0, 0],
        get_size=14,
        get_alignment_baseline="'center'",
        get_text_anchor="'middle'",
        pickable=True,
    )

    # lines connecting the stops
    lines_data = []
    for i in range(len(plan) - 1):
        lines_data.append({
            "start": [plan[i]['lon'], plan[i]['lat']],
            "end": [plan[i+1]['lon'], plan[i+1]['lat']],
            "name": f"Leg {i+1}"
        })

    layer_lines = pdk.Layer(
        "LineLayer",
        lines_data,
        get_source_position="start",
        get_target_position="end",
        get_color=[0, 0, 0],
        get_width=3,
    )

    # put it all together
    st.pydeck_chart(pdk.Deck(
        map_style=None,
        initial_view_state=view_state,
        layers=[layer_lines, layer_points, layer_text],
        tooltip={"text": "{name}\n{type}\n{true_vibe}\nRating: {rating}⭐\nCost: ${cost}"}
    ))
