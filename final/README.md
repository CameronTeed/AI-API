# Ottawa Date Planner AI

An intelligent itinerary generation system for Ottawa, using Genetic Algorithms and NLP to plan the perfect date based on "vibes", budget, and constraints.

## Features
*   **Natural Language Interface**: Describe your ideal date (e.g., "Romantic Italian dinner under $100").
*   **Two Planning Algorithms**:
    *   **Heuristic (Greedy)**: Fast, budget-strict planning.
    *   **Genetic Algorithm (GA)**: Global optimization for better "vibe" matching and flow.
*   **Vibe Classification**: Uses Machine Learning to tag venues with vibes (romantic, cozy, energetic, etc.).
*   **Interactive UI**: Built with Streamlit for easy interaction and map visualization.

## Prerequisites
*   Python 3.8+
*   pip

## Installation

1.  **Navigate to the project directory**.

2.  **Install dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

3.  **Download the SpaCy model**:
    ```bash
    python -m spacy download en_core_web_md
    ```

## Running the Application

1.  **Start the Streamlit app**:
    ```bash
    streamlit run app.py
    ```

2.  The application will open in your default web browser (usually at `http://localhost:8501`).

## Project Structure
*   `app.py`: Main Streamlit application entry point.
*   `ga_planner.py`: Genetic Algorithm implementation.
*   `heuristic_planner.py`: Greedy heuristic planner implementation.
*   `nlp_classifier.py`: Vibe classification logic (ML + Keywords).
*   `spacy_parser.py`: NLP pipeline for parsing user queries.
*   `planner_utils.py`: Shared utility functions (distance, scoring, data loading).
*   `ottawa_venues.csv`: Dataset of Ottawa venues.
*   `fetch_real_data.py`: Script to fetch/update venue data (requires API key).
