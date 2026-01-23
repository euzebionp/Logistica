import streamlit as st
import db_handler
import utils
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
import io


def generate_drivers_pdf(drivers_df):
    """Generate PDF report of all drivers with CNH status."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    elements = []
    styles = getSampleStyleSheet()
    
    # Title
    elements.append(Paragraph("Relatório de Motoristas", styles['Title']))
    elements.append(Spacer(1, 12))
    
    # Summary
    total_drivers = len(drivers_df)
    expired_count = sum(1 for _, row in drivers_df.iterrows() if utils.is_cnh_expired(row['validade_cnh']))
    
    elements.append(Paragraph(f"Total de Motoristas: {total_drivers}", styles['Normal']))
    elements.append(Paragraph(f"CNH Vencidas: {expired_count}", styles['Normal']))
    elements.append(Spacer(1, 24))
    
    # Table Data
    data = [['Nome', 'CPF', 'CNH', 'Validade CNH', 'Status']]
    
    for index, row in drivers_df.iterrows():
        status_text, _, _ = utils.get_cnh_status(row['validade_cnh'])
        formatted_date = utils.format_date_br(row['validade_cnh'])
        
        data.append([
            row['nome'],
            row['cpf'],
            row['cnh'],
            formatted_date,
            status_text
        ])
    
    # Table Style
    table = Table(data, colWidths=[170, 70, 60, 70, 60])
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

def drivers_page():
    st.header("Cadastro de Motoristas")
    
    # Tabs for Add and Manage
    tab1, tab2 = st.tabs(["Adicionar Motorista", "Gerenciar Motoristas"])
    
    with tab1:
        # Add Driver Form
        with st.form("driver_form"):
            nome = st.text_input("Nome Completo")
            cpf = st.text_input("CPF")
            cnh = st.text_input("CNH")
            validade_cnh = st.date_input("Validade da CNH")
            
            submit_button = st.form_submit_button("Salvar")
            
            if submit_button:
                if nome and cpf and cnh and validade_cnh:
                    if db_handler.check_driver_exists(cpf):
                        st.error("Motorista com este CPF já cadastrado!")
                    else:
                        success, message = db_handler.add_driver(nome, cpf, cnh, str(validade_cnh))
                        if success:
                            st.success(message)
                            st.rerun()
                        else:
                            st.error(message)
                else:
                    st.warning("Preencha todos os campos obrigatórios.")
    
    with tab2:
        # Manage Drivers
        drivers_df = db_handler.get_drivers()
        
        if drivers_df.empty:
            st.info("Nenhum motorista cadastrado.")
        else:
            # Show expired CNH alert at the top
            expired_drivers = []
            for index, row in drivers_df.iterrows():
                if utils.is_cnh_expired(row['validade_cnh']):
                    expired_drivers.append(row['nome'])
            
            if expired_drivers:
                st.error(f"⚠️ **ALERTA:** {len(expired_drivers)} motorista(s) com CNH vencida: {', '.join(expired_drivers)}")
            
            # Print button
            st.divider()
            col_print, col_space = st.columns([1, 3])
            with col_print:
                if st.button("🖨️ Imprimir Lista de Motoristas", use_container_width=True):
                    pdf_buffer = generate_drivers_pdf(drivers_df)
                    st.download_button(
                        label="📥 Baixar PDF",
                        data=pdf_buffer,
                        file_name="lista_motoristas.pdf",
                        mime="application/pdf",
                        use_container_width=True
                    )
            st.divider()
            
            st.subheader("Lista de Motoristas")
            
            for index, row in drivers_df.iterrows():
                # Get CNH status
                status_text, status_color, icon = utils.get_cnh_status(row['validade_cnh'])
                
                # Title with status indicator
                title = f"{icon} {row['nome']} - CPF: {row['cpf']}"
                if status_text == "VENCIDA":
                    title += " ⚠️ CNH VENCIDA"
                
                with st.expander(title):
                    col1, col2 = st.columns([3, 1])
                    
                    with col1:
                        st.write(f"**Nome:** {row['nome']}")
                        st.write(f"**CPF:** {row['cpf']}")
                        st.write(f"**CNH:** {row['cnh']}")
                        
                        # Display formatted date with status
                        formatted_date = utils.format_date_br(row['validade_cnh'])
                        if status_text == "VENCIDA":
                            st.markdown(f"**Validade CNH:** :red[{formatted_date}] 🔴 **{status_text}**")
                        elif "Vence em" in status_text and utils.days_until_expiration(row['validade_cnh']) <= 30:
                            st.markdown(f"**Validade CNH:** :orange[{formatted_date}] ⚠️ **{status_text}**")
                        elif "Vence em" in status_text and utils.days_until_expiration(row['validade_cnh']) <= 90:
                            st.markdown(f"**Validade CNH:** :yellow[{formatted_date}] ⚡ **{status_text}**")
                        else:
                            st.markdown(f"**Validade CNH:** :green[{formatted_date}] ✅ **{status_text}**")
                    
                    with col2:
                        # Edit button
                        if st.button("✏️ Editar", key=f"edit_driver_{row['id']}"):
                            st.session_state[f'editing_driver_{row["id"]}'] = True
                            st.rerun()
                        
                        # Delete button
                        if st.button("🗑️ Excluir", key=f"delete_driver_{row['id']}"):
                            success, message = db_handler.delete_driver(row['id'])
                            if success:
                                st.success(message)
                                st.rerun()
                            else:
                                st.error(message)
                    
                    # Edit form (shown when edit button is clicked)
                    if st.session_state.get(f'editing_driver_{row["id"]}', False):
                        st.divider()
                        st.subheader("Editar Motorista")
                        
                        with st.form(f"edit_form_{row['id']}"):
                            edit_nome = st.text_input("Nome Completo", value=row['nome'])
                            edit_cpf = st.text_input("CPF", value=row['cpf'])
                            edit_cnh = st.text_input("CNH", value=row['cnh'])
                            
                            # Parse date string
                            try:
                                date_obj = datetime.strptime(row['validade_cnh'], '%Y-%m-%d').date()
                            except:
                                date_obj = datetime.now().date()
                            
                            edit_validade = st.date_input("Validade da CNH", value=date_obj)
                            
                            col_save, col_cancel = st.columns(2)
                            with col_save:
                                save_button = st.form_submit_button("💾 Salvar Alterações")
                            with col_cancel:
                                cancel_button = st.form_submit_button("❌ Cancelar")
                            
                            if save_button:
                                success, message = db_handler.update_driver(
                                    row['id'], edit_nome, edit_cpf, edit_cnh, str(edit_validade)
                                )
                                if success:
                                    st.success(message)
                                    del st.session_state[f'editing_driver_{row["id"]}']
                                    st.rerun()
                                else:
                                    st.error(message)
                            
                            if cancel_button:
                                del st.session_state[f'editing_driver_{row["id"]}']
                                st.rerun()
