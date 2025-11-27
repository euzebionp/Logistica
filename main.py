import streamlit as st
from views import login, drivers, vehicles, fines, dashboard, reports, travels, maintenance
import db_handler

# Page configuration
st.set_page_config(
    page_title="Sistema de Gestão Logistica",
    page_icon="🚗",
    layout="wide"
)

# Hide Streamlit Style Elements
hide_st_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            header {visibility: hidden;}
            .stDeployButton {display:none;}
            </style>
            """
st.markdown(hide_st_style, unsafe_allow_html=True)

# Initialize Database
# Always run init_db to ensure migrations are applied
db_handler.init_db()

# Session State for Login
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

def main():
    if not st.session_state['logged_in']:
        login.login_page()
    else:
        sidebar()

def sidebar():
    st.sidebar.title("Menu Principal")
    page = st.sidebar.radio(
        "Navegação",
        ["Dashboard", "Cadastro de Motoristas", "Cadastro de Veículos", "Cadastro de Viagens", "Controle de Manutenções", "Cadastro de Multas", "Relatórios", "Sair"]
    )
    
    if page == "Dashboard":
        dashboard.dashboard_page()
    elif page == "Cadastro de Motoristas":
        drivers.drivers_page()
    elif page == "Cadastro de Veículos":
        vehicles.vehicles_page()
    elif page == "Cadastro de Viagens":
        travels.travels_page()
    elif page == "Controle de Manutenções":
        maintenance.maintenance_page()
    elif page == "Cadastro de Multas":
        fines.fines_page()
    elif page == "Relatórios":
        reports.reports_page()
    elif page == "Sair":
        st.session_state['logged_in'] = False
        st.rerun()

if __name__ == "__main__":
    main()
