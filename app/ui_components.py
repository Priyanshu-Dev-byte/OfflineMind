"""
OfflineMind - UI Components & Custom Styling
Provides clean, modern styles, badges, and cards for the Streamlit desktop application.
"""

import streamlit as st


def apply_custom_css():
    """Injects high-end, responsive CSS styling into the Streamlit application."""
    st.markdown("""
        <style>
            /* Main container typography and padding */
            .main .block-container {
                padding-top: 1.8rem;
                padding-bottom: 3rem;
                max-width: 1200px;
            }

            /* Header Title */
            .app-title {
                font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
                font-weight: 800;
                font-size: 2.3rem;
                letter-spacing: -0.03em;
                margin-bottom: 0.2rem;
                background: linear-gradient(135deg, #0284C7 0%, #2563EB 50%, #DC2626 100%);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
            }

            .app-subtitle {
                font-size: 1.05rem;
                color: #64748B;
                margin-bottom: 1.2rem;
            }

            /* Hardware Acceleration Badges */
            .badge-npu {
                display: inline-flex;
                align-items: center;
                background: linear-gradient(135deg, rgba(16, 185, 129, 0.15) 0%, rgba(5, 150, 105, 0.25) 100%);
                color: #059669;
                border: 1px solid rgba(16, 185, 129, 0.4);
                padding: 5px 12px;
                border-radius: 9999px;
                font-weight: 600;
                font-size: 0.85rem;
                letter-spacing: 0.02em;
            }

            .badge-cpu {
                display: inline-flex;
                align-items: center;
                background: rgba(245, 158, 11, 0.12);
                color: #D97706;
                border: 1px solid rgba(245, 158, 11, 0.35);
                padding: 5px 12px;
                border-radius: 9999px;
                font-weight: 600;
                font-size: 0.85rem;
            }

            /* Metric Card */
            .metric-card {
                background: #F8FAFC;
                border: 1px solid #E2E8F0;
                border-radius: 10px;
                padding: 14px 18px;
                margin-bottom: 12px;
            }

            .metric-title {
                font-size: 0.78rem;
                text-transform: uppercase;
                letter-spacing: 0.05em;
                color: #64748B;
                font-weight: 600;
            }

            .metric-val {
                font-size: 1.4rem;
                font-weight: 700;
                color: #0F172A;
                margin-top: 2px;
            }

            /* Note Card in Library */
            .note-card {
                background: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-radius: 12px;
                padding: 18px;
                margin-bottom: 16px;
                box-shadow: 0 1px 3px rgba(0,0,0,0.05);
                transition: transform 0.15s ease, box-shadow 0.15s ease;
            }

            .note-card:hover {
                transform: translateY(-2px);
                box-shadow: 0 4px 12px rgba(0,0,0,0.08);
                border-color: #CBD5E1;
            }

            .tag-pill {
                display: inline-block;
                background: #F1F5F9;
                color: #475569;
                border-radius: 6px;
                padding: 2px 8px;
                font-size: 0.75rem;
                font-weight: 500;
                margin-right: 6px;
            }
        </style>
    """, unsafe_allow_html=True)


def render_hardware_badge(badge_info: dict):
    """Displays the active inference backend badge."""
    if badge_info.get("status") == "active_npu":
        st.markdown(f"""
            <div class="badge-npu" title="{badge_info.get('tooltip')}">
                {badge_info.get('label')}
            </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
            <div class="badge-cpu" title="{badge_info.get('tooltip')}">
                {badge_info.get('label')}
            </div>
        """, unsafe_allow_html=True)
