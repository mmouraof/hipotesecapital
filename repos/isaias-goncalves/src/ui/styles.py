import streamlit as st
from config import CHART_COLOR_PRIMARY, CHART_COLOR_SECONDARY


def apply_custom_styles():
    """
    Aplica refinamentos estéticos que o Streamlit não cobre nativamente.
    Combina 'Playfair Display' (Serif) para títulos e 'Source Sans Pro' (Sans) para corpo.
    """
    st.markdown(f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,400;0,700;1,400&family=Source+Sans+Pro:wght@400;600&display=swap');

        /* --- TIPOGRAFIA DE AUTORIDADE (SERIF) --- */
        h1, h2, h3, .stTitle, [data-testid="stMetricValue"]  {{
            font-family: 'Playfair Display', serif !important;
            font-weight: 700 !important;
        }}
        
        /* Ajuste fino para métricas (Rótulos em Sans para clareza) */
        [data-testid="stMetricLabel"] {{
            font-family: 'Source Sans Pro', sans-serif !important;
            text-transform: uppercase;
            letter-spacing: 1.2px;
            font-size: 0.75rem !important;
            opacity: 0.8;
        }}

        /* --- POLIMENTO VISUAL --- */
        .stButton > button {{
            border-radius: 4px !important;
            text-transform: uppercase;
            letter-spacing: 1px;
            font-weight: 600 !important;
            transition: all 0.3s ease;
        }}
        
        .stButton > button:hover {{
            box-shadow: 0 4px 15px rgba(102, 11, 5, 0.4);
            border-color: {CHART_COLOR_SECONDARY} !important;
        }}

        [data-testid="stMetric"] {{
            border: 1px solid rgba(255, 240, 196, 0.1) !important;
            padding: 15px !important;
            border-radius: 8px !important;
            background-color: rgba(255, 240, 196, 0.02) !important;
        }}

        /* Ajuste de cor para links (evitar azul padrão que distoa do vermelho) */
        a {{
            color: {CHART_COLOR_SECONDARY} !important;
            text-decoration: none;
            font-weight: 600;
        }}
        a:hover {{
            text-decoration: underline;
        }}

        </style>
        """, unsafe_allow_html=True)
