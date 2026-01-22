# ui/login_view.py
import streamlit as st
from core.ui_helpers import submit


def inject_login_css(hero_url: str):
    st.markdown(
        f"""
        <style>
          /* hide chrome */
          #MainMenu {{visibility: hidden;}}
          footer {{visibility: hidden;}}
          header {{visibility: hidden;}}
          section[data-testid="stSidebar"] {{ display:none; }}

          /* background */
          div[data-testid="stAppViewContainer"] {{
            background:
              radial-gradient(1200px 700px at 20% 10%, rgba(255,255,255,0.06), transparent 55%),
              #0b0f14;
          }}

          /* IMPORTANT: center whole login page vertically (desktop) */
          section.main > div.block-container {{
            padding-top: 16px !important;
            padding-bottom: 16px !important;
            height: 100dvh;
            display: flex;
            flex-direction: column;
            justify-content: center;
          }}

          /* avoid horizontal scroll */
          html, body {{ overflow-x: hidden; }}

          /* hero block */
          .mz-hero {{
            height: calc(100dvh - 32px);   /* 16px top + 16px bottom */
            border-radius: 18px;
            border: 1px solid rgba(255,255,255,0.08);
            background-image:
              linear-gradient(0deg, rgba(0,0,0,0.55), rgba(0,0,0,0.25)),
              url('{hero_url}');
            background-size: cover;
            background-position: center;
          }}

          .mz-brand {{
            display:flex; align-items:center; gap:10px; font-weight:700;
            margin-bottom: 14px;
          }}
          .mz-badge {{
            width: 28px; height: 28px; border-radius: 8px;
            display:flex; align-items:center; justify-content:center;
            background: #3b82f6; color:white; font-weight: 900;
          }}

          /* input styling */
          div[data-testid="stTextInput"] input {{
            border-radius: 12px !important;
            padding: 12px 12px !important;
          }}

          /* MOBILE: allow scroll + hide hero */
          @media (max-width: 1100px) {{
            section.main > div.block-container {{
              height: auto;
              display: block;
              padding-top: 12px !important;
              padding-bottom: 24px !important;
            }}
            .mz-hero {{
              display:none;
            }}
          }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_login_page(brand: str, hero_url: str):
    inject_login_css(hero_url)

    # pure Streamlit layout (NO html wrapper that tries to contain widgets)
    colL, colR = st.columns([0.42, 0.58], gap="large")

    with colR:
        st.markdown("<div class='mz-hero'></div>", unsafe_allow_html=True)

    with colL:
        st.markdown(
            f"""
            <div class="mz-brand">
              <div class="mz-badge">MZ</div>
              <div>{brand}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        with st.container(border=True):
            st.markdown("## Login to your account")
            st.caption("Enter your username & password to continue")

            with st.form("login_form", clear_on_submit=False):
                u = st.text_input("Username", value="", key="login_user")
                p = st.text_input("Password", value="", type="password", key="login_pass")
                remember = st.checkbox("Remember me", value=True, key="login_remember")
                do_login = submit("Login", stretch=True)

    return u, p, remember, do_login
