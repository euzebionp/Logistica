import streamlit as st
from views import login, drivers, vehicles, fines, dashboard, reports, travels, maintenance, fuel_analysis
import db_handler

# Page configuration
st.set_page_config(
    page_title="Sistema de Gestão Logística",
    page_icon="🚗",
    layout="wide"
)

# Hide Streamlit default elements
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .stDeployButton {display:none;}
    </style>
""", unsafe_allow_html=True)

# Initialize Database (applies migrations automatically)
db_handler.init_db()

if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False


def main():
    if not st.session_state['logged_in']:
        login.login_page()
    else:
        sidebar()


def sidebar():
    st.sidebar.title("Menu Principal")

    # Badge de alertas críticos de manutenção
    alertas = db_handler.count_critical_alerts()
    if alertas > 0:
        st.sidebar.error(f"⚠️ {alertas} manutenção(ões) URGENTE(S)")

    page = st.sidebar.radio(
        "Navegação",
        [
            "Dashboard",
            "Cadastro de Motoristas",
            "Cadastro de Veículos",
            "Cadastro de Viagens",
            "Controle de Manutenções",
            "Combustível e Rendimento",
            "Cadastro de Multas",
            "Relatórios",
            "Sair",
        ]
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
    elif page == "Combustível e Rendimento":
        fuel_analysis.fuel_analysis_page()
    elif page == "Cadastro de Multas":
        fines.fines_page()
    elif page == "Relatórios":
        reports.reports_page()
    elif page == "Sair":
        st.session_state['logged_in'] = False
        st.rerun()


if __name__ == "__main__":
    main()
