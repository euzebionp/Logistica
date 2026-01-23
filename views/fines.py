import streamlit as st
import db_handler
import utils
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
import io


def generate_fines_pdf(fines_df):
    """Generate PDF report of all fines."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    elements = []
    styles = getSampleStyleSheet()
    
    # Title
    elements.append(Paragraph("Relatório de Multas", styles['Title']))
    elements.append(Spacer(1, 12))
    
    # Summary
    total_fines = len(fines_df)
    total_value = fines_df['valor'].sum()
    elements.append(Paragraph(f"Total de Multas: {total_fines}", styles['Normal']))
    elements.append(Paragraph(f"Valor Total: R$ {total_value:,.2f}", styles['Normal']))
    elements.append(Spacer(1, 24))
    
    # Table Data
    data = [['Data', 'Motorista', 'Veículo', 'Tipo', 'Valor']]
    
    for index, row in fines_df.iterrows():
        formatted_date = utils.format_date_br(row['data'])
        data.append([
            formatted_date,
            row['motorista'],
            f"{row['veiculo_modelo']}\n{row['veiculo_placa']}",
            row['tipo_infracao'],
            f"R$ {row['valor']:.2f}"
        ])
    
    # Table Style
    table = Table(data, colWidths=[60, 100, 100, 70, 70])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('FONTSIZE', (0, 1), (-1, -1), 7),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    
    elements.append(table)
    doc.build(elements)
    buffer.seek(0)
    return buffer


def fines_page():
    st.header("Cadastro de Multas")
    
    # Load data for selectboxes
    drivers_df = db_handler.get_drivers()
    vehicles_df = db_handler.get_vehicles()
    
    if drivers_df.empty or vehicles_df.empty:
        st.warning("Cadastre motoristas e veículos antes de registrar multas.")
        return
    
    # Tabs for Add and Manage
    tab1, tab2 = st.tabs(["Adicionar Multa", "Gerenciar Multas"])
    
    with tab1:
        # Add Fine Form
        driver_options = {f"{row['nome']} (CPF: {row['cpf']})": row['id'] for index, row in drivers_df.iterrows()}
        vehicle_options = {f"{row['modelo']} - {row['placa']}": row['id'] for index, row in vehicles_df.iterrows()}
        
        with st.form("fine_form"):
            data = st.date_input("Data da Infração")
            local = st.text_input("Local")
            tipo_infracao = st.selectbox("Tipo de Infração", ["Leve", "Média", "Grave", "Gravíssima"])
            descricao = st.text_area("Descrição")
            valor = st.number_input("Valor (R$)", min_value=0.0, step=0.01)
            
            selected_driver_label = st.selectbox("Motorista", list(driver_options.keys()))
            selected_vehicle_label = st.selectbox("Veículo", list(vehicle_options.keys()))
            
            submit_button = st.form_submit_button("Salvar")
            
            if submit_button:
                if local and descricao and valor > 0:
                    motorista_id = driver_options[selected_driver_label]
                    veiculo_id = vehicle_options[selected_vehicle_label]
                    
                    success, message = db_handler.add_fine(
                        str(data), local, tipo_infracao, descricao, motorista_id, veiculo_id, valor
                    )
                    if success:
                        st.success(message)
                        st.rerun()
                    else:
                        st.error(message)
                else:
                    st.warning("Preencha todos os campos obrigatórios.")
    
    with tab2:
        # Manage Fines
        fines_df = db_handler.get_fines_df()
        
        if fines_df.empty:
            st.info("Nenhuma multa cadastrada.")
        else:
            # Search Bar
            search_query = st.text_input("🔍 Localizar Multa", placeholder="Busque por Motorista, Veículo ou Placa...").strip().lower()
            if search_query:
                fines_df = fines_df[
                    fines_df['motorista'].str.lower().str.contains(search_query) |
                    fines_df['veiculo_placa'].str.lower().str.contains(search_query) |
                    fines_df['veiculo_modelo'].str.lower().str.contains(search_query)
                ]

            if fines_df.empty:
                st.info("Nenhuma multa encontrada para a busca.")
            else:
                # Print button
                st.divider()
                col_print, col_space = st.columns([1, 3])
                with col_print:
                    if st.button("🖨️ Imprimir Lista de Multas", use_container_width=True):
                        pdf_buffer = generate_fines_pdf(fines_df)
                        st.download_button(
                            label="📥 Baixar PDF",
                            data=pdf_buffer,
                            file_name="lista_multas.pdf",
                            mime="application/pdf",
                            use_container_width=True
                        )
                st.divider()
                
                st.subheader("Lista de Multas")
                
                for index, row in fines_df.iterrows():
                    # Format date for display
                    formatted_date = utils.format_date_br(row['data'])
                    
                    with st.expander(f"🚨 {row['tipo_infracao']} - {row['motorista']} - {formatted_date}"):
                        col1, col2 = st.columns([3, 1])
                        
                        with col1:
                            st.write(f"**Data:** {formatted_date}")
                            st.write(f"**Local:** {row['local']}")
                            st.write(f"**Tipo:** {row['tipo_infracao']}")
                            st.write(f"**Descrição:** {row['descricao']}")
                            st.write(f"**Motorista:** {row['motorista']}")
                            st.write(f"**Veículo:** {row['veiculo_modelo']} ({row['veiculo_placa']})")
                            st.write(f"**Valor:** R$ {row['valor']:.2f}")
                        
                        with col2:
                            # Edit button
                            if st.button("✏️ Editar", key=f"edit_fine_{row['id']}"):
                                st.session_state[f'editing_fine_{row["id"]}'] = True
                                st.rerun()
                            
                            # Delete button
                            if st.button("🗑️ Excluir", key=f"delete_fine_{row['id']}"):
                                success, message = db_handler.delete_fine(row['id'])
                                if success:
                                    st.success(message)
                                    st.rerun()
                                else:
                                    st.error(message)
                        
                        # Edit form (shown when edit button is clicked)
                        if st.session_state.get(f'editing_fine_{row["id"]}', False):
                            st.divider()
                            st.subheader("Editar Multa")
                            
                            # Get the full fine data
                            fine_data = db_handler.get_fine_by_id(row['id'])
                            
                            # Rebuild driver and vehicle options
                            driver_options_edit = {f"{r['nome']} (CPF: {r['cpf']})": r['id'] for i, r in drivers_df.iterrows()}
                            vehicle_options_edit = {f"{r['modelo']} - {r['placa']}": r['id'] for i, r in vehicles_df.iterrows()}
                            
                            # Find current selections
                            try:
                                current_driver_label = [k for k, v in driver_options_edit.items() if v == fine_data['motorista_id']][0]
                                current_vehicle_label = [k for k, v in vehicle_options_edit.items() if v == fine_data['veiculo_id']][0]
                            except IndexError:
                                # Handle case where driver/vehicle might be deleted or not found
                                current_driver_label = list(driver_options_edit.keys())[0] if driver_options_edit else ""
                                current_vehicle_label = list(vehicle_options_edit.keys())[0] if vehicle_options_edit else ""

                            
                            with st.form(f"edit_form_{row['id']}"):
                                # Parse date string
                                try:
                                    date_obj = datetime.strptime(fine_data['data'], '%Y-%m-%d').date()
                                except:
                                    date_obj = datetime.now().date()
                                
                                edit_data = st.date_input("Data da Infração", value=date_obj)
                                edit_local = st.text_input("Local", value=fine_data['local'])
                                edit_tipo = st.selectbox("Tipo de Infração", ["Leve", "Média", "Grave", "Gravíssima"], 
                                                         index=["Leve", "Média", "Grave", "Gravíssima"].index(fine_data['tipo_infracao']))
                                edit_descricao = st.text_area("Descrição", value=fine_data['descricao'])
                                edit_valor = st.number_input("Valor (R$)", min_value=0.0, step=0.01, value=float(fine_data['valor']))
                                
                                edit_driver = st.selectbox("Motorista", list(driver_options_edit.keys()), 
                                                           index=list(driver_options_edit.keys()).index(current_driver_label) if current_driver_label in driver_options_edit else 0)
                                edit_vehicle = st.selectbox("Veículo", list(vehicle_options_edit.keys()), 
                                                            index=list(vehicle_options_edit.keys()).index(current_vehicle_label) if current_vehicle_label in vehicle_options_edit else 0)
                                
                                col_save, col_cancel = st.columns(2)
                                with col_save:
                                    save_button = st.form_submit_button("💾 Salvar Alterações")
                                with col_cancel:
                                    cancel_button = st.form_submit_button("❌ Cancelar")
                                
                                if save_button:
                                    motorista_id = driver_options_edit[edit_driver]
                                    veiculo_id = vehicle_options_edit[edit_vehicle]
                                    
                                    success, message = db_handler.update_fine(
                                        row['id'], str(edit_data), edit_local, edit_tipo, edit_descricao, 
                                        motorista_id, veiculo_id, edit_valor
                                    )
                                    if success:
                                        st.success(message)
                                        del st.session_state[f'editing_fine_{row["id"]}']
                                        st.rerun()
                                    else:
                                        st.error(message)
                                
                                if cancel_button:
                                    del st.session_state[f'editing_fine_{row["id"]}']
                                    st.rerun()
