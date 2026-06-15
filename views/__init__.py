"""View layer for the Streamlit app — one module per dashboard tab.

Each tab module exposes a ``render()`` function that draws that tab. Shared
optimisation state (current result, supply/demand/cost used, CO₂ matrix) is read
from ``st.session_state``; ``app.py`` is responsible for populating it.
"""
