
import streamlit as st
import db_handler
import utils
import pandas as pd
from datetime import datetime, time, timedelta
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
import io
import utils_geo


def generate_travels_pdf(travels_df):
    """Generate PDF report of all travels."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    elements = []
    styles = getSampleStyleSheet()
    
    # Title
    elements.append(Paragraph("Relatório de Viagens", styles['Title']))
    elements.append(Spacer(1, 12))
    
    # Summary
    total_travels = len(travels_df)
    elements.append(Paragraph(f"Total de Viagens: {total_travels}", styles['Normal']))
    elements.append(Spacer(1, 24))
    
    # Table Data
    data = [['Data', 'Hora', 'Origem', 'Destino', 'Motorista', 'Veículo']]
    
    for index, row in travels_df.iterrows():
        formatted_date = utils.format_date_br(row['data'])
        veiculo_info = f"{row['veiculo_placa']} - {row['veiculo_modelo']}"
        
        data.append([
            formatted_date,
            row['hora_saida'],
            row.get('origem', '-'),
            row['destino'],
            row['motorista'],
            veiculo_info
        ])
    
    # Table Style
    table = Table(data, colWidths=[60, 50, 100, 100, 100, 100])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
    ]))
    
    elements.append(table)
    doc.build(elements)
    buffer.seek(0)
    return buffer


def travels_page():
    st.header("Cadastro de Viagens")
    
    # Tabs for Add and Manage
    tab1, tab2 = st.tabs(["Adicionar Viagem", "Gerenciar Viagens"])
    
    with tab1:
        # Add Travel Form
        with st.form("travel_form"):
            st.subheader("Nova Viagem")
            
            # Date and Time
            col1, col2 = st.columns(2)
            with col1:
                data = st.date_input("Data da Viagem")
            with col2:
                hora_saida = st.time_input("Hora de Saída", value=time(8, 0))
            
            # Origin and Destination
            col_origem, col_dest = st.columns(2)
            with col_origem:
                origem = st.text_input("Cidade de Origem")
            with col_dest:
                destino = st.text_input("Cidade de Destino")
            
            # Auto-calculate distance
            calculated_distance = 0.0
            if origem and destino:
                # Use session state to store last calculation to avoid re-fetching on every rerun if not needed
                # But for simplicity and responsiveness, we'll try to calculate if it looks like a new pair
                key = f"{origem}-{destino}"
                if st.session_state.get('last_calc_key') != key:
                    with st.spinner("Calculando distância..."):
                        dist = utils_geo.calculate_distance(origem, destino)
                        if dist:
                            st.session_state['last_calc_dist'] = dist
                            st.session_state['last_calc_key'] = key
                            st.toast(f"Distância calculada: {dist} km")
                        else:
                            st.warning("Não foi possível calcular a distância automaticamente.")
            
            # Distance
            default_dist = st.session_state.get('last_calc_dist', 0.0) if (origem and destino and st.session_state.get('last_calc_key') == f"{origem}-{destino}") else 0.0
            distancia = st.number_input("Distância Percorrida (Km)", min_value=0.0, step=1.0, value=float(default_dist))
            
            # Driver Selection
            drivers_df = db_handler.get_drivers()
            if drivers_df.empty:
                st.warning("⚠️ Nenhum motorista cadastrado. Cadastre um motorista primeiro.")
                driver_options = []
            else:
                driver_options = {f"{row['nome']} - CPF: {row['cpf']}": row['id'] 
                                for _, row in drivers_df.iterrows()}
            
            selected_driver = st.selectbox(
                "Motorista",
                options=list(driver_options.keys()) if driver_options else ["Nenhum motorista disponível"],
                disabled=len(driver_options) == 0
            )
            
            # Vehicle Selection
            vehicles_df = db_handler.get_vehicles()
            if vehicles_df.empty:
                st.warning("⚠️ Nenhum veículo cadastrado. Cadastre um veículo primeiro.")
                vehicle_options = []
            else:
                vehicle_options = {f"{row['placa']} - {row['modelo']} ({row['ano']})": row['id'] 
                                 for _, row in vehicles_df.iterrows()}
            
            selected_vehicle = st.selectbox(
                "Veículo",
                options=list(vehicle_options.keys()) if vehicle_options else ["Nenhum veículo disponível"],
                disabled=len(vehicle_options) == 0
            )
            
            submit_button = st.form_submit_button("🚗 Cadastrar Viagem", use_container_width=True)
            
            if submit_button:
                if not driver_options or not vehicle_options:
                    st.error("Cadastre motoristas e veículos antes de registrar uma viagem.")
                elif destino and data and hora_saida:
                    motorista_id = driver_options[selected_driver]
                    veiculo_id = vehicle_options[selected_vehicle]
                    hora_saida_str = hora_saida.strftime("%H:%M")
                    
                    success, message = db_handler.add_travel(
                        str(data), motorista_id, veiculo_id, origem, destino, hora_saida_str, distancia
                    )
                    if success:
                        st.success(message)
                        st.rerun()
                    else:
                        st.error(message)
                else:
                    st.warning("Preencha todos os campos obrigatórios.")
    
    with tab2:
        # Manage Travels
        travels_df = db_handler.get_travels()
        
        # Filters
        st.subheader("Filtros e Pesquisa")
        col_filter1, col_filter2 = st.columns(2)
        
        with col_filter1:
            # Date Filter
            today = datetime.now().date()
            last_30 = today - timedelta(days=30)
            date_range = st.date_input(
                "Filtrar por Data",
                value=(last_30, today),
                format="DD/MM/YYYY"
            )
        
        with col_filter2:
            # Sort/Group Filter
            sort_option = st.selectbox(
                "Agrupar/Ordenar por",
                ["Data (Mais recente)", "Cidade Destino", "Cidade Origem", "Motorista"]
            )

        # Apply Filters
        if not travels_df.empty:
            # Date Filter
            if isinstance(date_range, tuple) and len(date_range) == 2:
                start_date, end_date = date_range
                travels_df['data_dt'] = pd.to_datetime(travels_df['data']).dt.date
                travels_df = travels_df[
                    (travels_df['data_dt'] >= start_date) & 
                    (travels_df['data_dt'] <= end_date)
                ]
            
            # Sorting
            if sort_option == "Cidade Destino":
                travels_df = travels_df.sort_values(by='destino')
            elif sort_option == "Cidade Origem":
                # Handle potential missing 'origem' in old records if not handled by DB default
                if 'origem' in travels_df.columns:
                    travels_df = travels_df.sort_values(by='origem')
            elif sort_option == "Motorista":
                travels_df = travels_df.sort_values(by='motorista')
            else: # Data
                travels_df = travels_df.sort_values(by=['data', 'hora_saida'], ascending=[False, False])
        
        if travels_df.empty:
            st.info("Nenhuma viagem cadastrada.")
        else:
            # Print button
            st.divider()
            col_print, col_space = st.columns([1, 3])
            with col_print:
                if st.button("🖨️ Imprimir Lista de Viagens", use_container_width=True):
                    pdf_buffer = generate_travels_pdf(travels_df)
                    st.download_button(
                        label="📥 Baixar PDF",
                        data=pdf_buffer,
                        file_name="lista_viagens.pdf",
                        mime="application/pdf",
                        use_container_width=True
                    )
            st.divider()
            
            st.subheader("Lista de Viagens")
            
            # Display statistics
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total de Viagens", len(travels_df))
            with col2:
                unique_drivers = travels_df['motorista'].nunique()
                st.metric("Motoristas Ativos", unique_drivers)
            with col3:
                total_km = travels_df['distancia'].sum() if 'distancia' in travels_df.columns else 0
                st.metric("Km Total Percorrido", f"{total_km:.0f} km")
            
            st.divider()
            
            for index, row in travels_df.iterrows():
                # Format date for display
                formatted_date = utils.format_date_br(row['data'])
                
                # Title with travel info
                origem_txt = row.get('origem', '-')
                title = f"🚗 {formatted_date} | {origem_txt} ➝ {row['destino']} | {row['motorista']}"
                
                with st.expander(title):
                    col1, col2 = st.columns([3, 1])
                    
                    with col1:
                        st.write(f"**📅 Data:** {formatted_date}")
                        st.write(f"**🕐 Hora de Saída:** {row['hora_saida']}")
                        st.write(f"**📍 Origem:** {row.get('origem', '-')}")
                        st.write(f"**📍 Destino:** {row['destino']}")
                        st.write(f"**📏 Distância:** {row['distancia']:.0f} km" if pd.notna(row['distancia']) else "**📏 Distância:** 0 km")
                        st.write(f"**👤 Motorista:** {row['motorista']}")
                        st.write(f"**🚙 Veículo:** {row['veiculo_placa']} - {row['veiculo_modelo']}")
                    
                    with col2:
                        # Edit button
                        if st.button("✏️ Editar", key=f"edit_travel_{row['id']}"):
                            st.session_state[f'editing_travel_{row["id"]}'] = True
                            st.rerun()
                        
                        # Delete button
                        if st.button("🗑️ Excluir", key=f"delete_travel_{row['id']}"):
                            success, message = db_handler.delete_travel(row['id'])
                            if success:
                                st.success(message)
                                st.rerun()
                            else:
                                st.error(message)
                    
                    # Edit form (shown when edit button is clicked)
                    if st.session_state.get(f'editing_travel_{row["id"]}', False):
                        st.divider()
                        st.subheader("Editar Viagem")
                        
                        # Get full travel data
                        travel_data = db_handler.get_travel_by_id(row['id'])
                        
                        with st.form(f"edit_form_{row['id']}"):
                            # Date and Time
                            col1, col2 = st.columns(2)
                            with col1:
                                try:
                                    date_obj = datetime.strptime(travel_data['data'], '%Y-%m-%d').date()
                                except:
                                    date_obj = datetime.now().date()
                                edit_data = st.date_input("Data da Viagem", value=date_obj)
                            
                            with col2:
                                try:
                                    time_obj = datetime.strptime(travel_data['hora_saida'], '%H:%M').time()
                                except:
                                    time_obj = time(8, 0)
                                edit_hora_saida = st.time_input("Hora de Saída", value=time_obj)
                            
                            # Origin and Destination
                            edit_origem = st.text_input("Origem", value=travel_data.get('origem', ''))
                            edit_destino = st.text_input("Destino", value=travel_data['destino'])
                            
                            # Auto-calc logic for edit
                            if edit_origem and edit_destino:
                                key_edit = f"edit-{edit_origem}-{edit_destino}"
                                if st.session_state.get('last_calc_key_edit') != key_edit:
                                     # Only auto-calc if user changed something, otherwise keep DB value
                                     # This is tricky in Edit mode. We don't want to overwrite manual edits unless requested.
                                     # Let's add a button for explicit calc in edit mode
                                     pass
                            
                            if st.button("🔄 Recalcular Distância", key=f"recalc_{row['id']}"):
                                dist = utils_geo.calculate_distance(edit_origem, edit_destino)
                                if dist:
                                    st.session_state[f"calc_dist_{row['id']}"] = dist
                                    st.toast(f"Distância recalculada: {dist} km")
                            
                            val_dist = st.session_state.get(f"calc_dist_{row['id']}", float(travel_data['distancia']))
                            
                            # Distance
                            edit_distancia = st.number_input("Distância Percorrida (Km)", min_value=0.0, step=1.0, value=val_dist)
                            
                            # Driver Selection
                            drivers_df = db_handler.get_drivers()
                            driver_options = {f"{row['nome']} - CPF: {row['cpf']}": row['id'] 
                                            for _, row in drivers_df.iterrows()}
                            
                            # Find current driver index
                            current_driver_idx = 0
                            for idx, (key, value) in enumerate(driver_options.items()):
                                if value == travel_data['motorista_id']:
                                    current_driver_idx = idx
                                    break
                            
                            edit_selected_driver = st.selectbox(
                                "Motorista",
                                options=list(driver_options.keys()),
                                index=current_driver_idx
                            )
                            
                            # Vehicle Selection
                            vehicles_df = db_handler.get_vehicles()
                            vehicle_options = {f"{row['placa']} - {row['modelo']} ({row['ano']})": row['id'] 
                                             for _, row in vehicles_df.iterrows()}
                            
                            # Find current vehicle index
                            current_vehicle_idx = 0
                            for idx, (key, value) in enumerate(vehicle_options.items()):
                                if value == travel_data['veiculo_id']:
                                    current_vehicle_idx = idx
                                    break
                            
                            edit_selected_vehicle = st.selectbox(
                                "Veículo",
                                options=list(vehicle_options.keys()),
                                index=current_vehicle_idx
                            )
                            
                            col_save, col_cancel = st.columns(2)
                            with col_save:
                                save_button = st.form_submit_button("💾 Salvar Alterações")
                            with col_cancel:
                                cancel_button = st.form_submit_button("❌ Cancelar")
                            
                            if save_button:
                                motorista_id = driver_options[edit_selected_driver]
                                veiculo_id = vehicle_options[edit_selected_vehicle]
                                hora_saida_str = edit_hora_saida.strftime("%H:%M")
                                
                                success, message = db_handler.update_travel(
                                    row['id'], str(edit_data), motorista_id, veiculo_id, 
                                    edit_origem, edit_destino, hora_saida_str, edit_distancia
                                )
                                if success:
                                    st.success(message)
                                    del st.session_state[f'editing_travel_{row["id"]}']
                                    st.rerun()
                                else:
                                    st.error(message)
                            
                            if cancel_button:
                                del st.session_state[f'editing_travel_{row["id"]}']
                                st.rerun()
