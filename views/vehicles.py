import streamlit as st
import db_handler
import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
import io


def generate_vehicles_pdf(vehicles_df):
    """Generate PDF report of all vehicles."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    elements = []
    styles = getSampleStyleSheet()
    
    # Title
    elements.append(Paragraph("Relatório de Veículos", styles['Title']))
    elements.append(Spacer(1, 12))
    
    # Summary
    total_vehicles = len(vehicles_df)
    elements.append(Paragraph(f"Total de Veículos: {total_vehicles}", styles['Normal']))
    elements.append(Spacer(1, 24))
    
    # Table Data
    data = [['Placa', 'Modelo', 'Ano', 'Renavam']]
    
    for index, row in vehicles_df.iterrows():
        data.append([
            row['placa'],
            row['modelo'],
            str(row['ano']),
            row['renavam']
        ])
    
    # Table Style
    table = Table(data, colWidths=[100, 150, 80, 110])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
    ]))
    
    elements.append(table)
    doc.build(elements)
    buffer.seek(0)
    return buffer

def vehicles_page():
    st.header("Cadastro de Veículos")
    
    # Tabs for Add and Manage
    tab1, tab2 = st.tabs(["Adicionar Veículo", "Gerenciar Veículos"])
    
    with tab1:
        # Add Vehicle Form
        with st.form("vehicle_form"):
            placa = st.text_input("Placa")
            modelo = st.text_input("Modelo")
            ano = st.number_input("Ano", min_value=1900, max_value=datetime.datetime.now().year + 1, step=1)
            renavam = st.text_input("Renavam")
            km_atual = st.number_input("Quilometragem Atual (Km)", min_value=0.0, step=1.0)
            
            submit_button = st.form_submit_button("Salvar")
            
            if submit_button:
                if placa and modelo and ano and renavam:
                    if db_handler.check_vehicle_exists(placa):
                         st.error("Veículo com esta placa já cadastrado!")
                    else:
                        success, message = db_handler.add_vehicle(placa, modelo, int(ano), renavam, km_atual)
                        if success:
                            st.success(message)
                            st.rerun()
                        else:
                            st.error(message)
                else:
                    st.warning("Preencha todos os campos obrigatórios.")
    
    with tab2:
        # Manage Vehicles
        vehicles_df = db_handler.get_vehicles()
        
        if vehicles_df.empty:
            st.info("Nenhum veículo cadastrado.")
        else:
            # Print button
            st.divider()
            col_print, col_space = st.columns([1, 3])
            with col_print:
                if st.button("🖨️ Imprimir Lista de Veículos", use_container_width=True):
                    pdf_buffer = generate_vehicles_pdf(vehicles_df)
                    st.download_button(
                        label="📥 Baixar PDF",
                        data=pdf_buffer,
                        file_name="lista_veiculos.pdf",
                        mime="application/pdf",
                        use_container_width=True
                    )
            st.divider()
            
            st.subheader("Lista de Veículos")
            
            for index, row in vehicles_df.iterrows():
                with st.expander(f"🚙 {row['modelo']} - Placa: {row['placa']}"):
                    col1, col2 = st.columns([3, 1])
                    
                    with col1:
                        st.write(f"**Placa:** {row['placa']}")
                        st.write(f"**Modelo:** {row['modelo']}")
                        st.write(f"**Ano:** {row['ano']}")
                        st.write(f"**Renavam:** {row['renavam']}")
                        st.write(f"**Km Atual:** {row['km_atual']:.0f} km")
                    
                    with col2:
                        # Edit button
                        if st.button("✏️ Editar", key=f"edit_vehicle_{row['id']}"):
                            st.session_state[f'editing_vehicle_{row["id"]}'] = True
                            st.rerun()
                        
                        # Delete button
                        if st.button("🗑️ Excluir", key=f"delete_vehicle_{row['id']}"):
                            success, message = db_handler.delete_vehicle(row['id'])
                            if success:
                                st.success(message)
                                st.rerun()
                            else:
                                st.error(message)
                    
                    # Edit form (shown when edit button is clicked)
                    if st.session_state.get(f'editing_vehicle_{row["id"]}', False):
                        st.divider()
                        st.subheader("Editar Veículo")
                        
                        with st.form(f"edit_form_{row['id']}"):
                            edit_placa = st.text_input("Placa", value=row['placa'])
                            edit_modelo = st.text_input("Modelo", value=row['modelo'])
                            edit_ano = st.number_input("Ano", min_value=1900, max_value=datetime.datetime.now().year + 1, step=1, value=int(row['ano']))
                            edit_renavam = st.text_input("Renavam", value=row['renavam'])
                            edit_km = st.number_input("Quilometragem Atual", min_value=0.0, step=1.0, value=float(row['km_atual']) if pd.notna(row['km_atual']) else 0.0)
                            
                            col_save, col_cancel = st.columns(2)
                            with col_save:
                                save_button = st.form_submit_button("💾 Salvar Alterações")
                            with col_cancel:
                                cancel_button = st.form_submit_button("❌ Cancelar")
                            
                            if save_button:
                                success, message = db_handler.update_vehicle(
                                    row['id'], edit_placa, edit_modelo, int(edit_ano), edit_renavam, edit_km
                                )
                                if success:
                                    st.success(message)
                                    del st.session_state[f'editing_vehicle_{row["id"]}']
                                    st.rerun()
                                else:
                                    st.error(message)
                            
                            if cancel_button:
                                del st.session_state[f'editing_vehicle_{row["id"]}']
                                st.rerun()
