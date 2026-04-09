import streamlit as st
import db_handler
import datetime
import pandas as pd
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
            col1, col2 = st.columns(2)
            with col1:
                placa = st.text_input("Placa *")
                modelo = st.text_input("Modelo *")
                ano = st.number_input("Ano *", min_value=1900,
                                      max_value=datetime.datetime.now().year + 1, step=1)
                renavam = st.text_input("Renavam *")
            with col2:
                km_atual = st.number_input("Quilometragem Atual (Km)", min_value=0.0, step=1.0)
                tipo_combustivel = st.selectbox(
                    "Tipo de Combustível",
                    ['flex', 'gasolina', 'etanol', 'diesel_s10', 'diesel_s500', 'gnv'],
                    format_func=lambda x: {
                        'flex': 'Flex (Gasolina/Etanol)',
                        'gasolina': 'Gasolina',
                        'etanol': 'Etanol',
                        'diesel_s10': 'Diesel S10',
                        'diesel_s500': 'Diesel S500',
                        'gnv': 'GNV'
                    }.get(x, x)
                )
                numero_frota = st.text_input("Número da Frota", help="Código interno da frota (opcional)")
                hodometro_horas = st.number_input("Horas do Motor", min_value=0.0, step=1.0,
                                                  help="Para veículos diesel: horas de trabalho do motor")

            submit_button = st.form_submit_button("Salvar")

            if submit_button:
                if placa and modelo and ano and renavam:
                    if db_handler.check_vehicle_exists(placa):
                        st.error("Veículo com esta placa já cadastrado!")
                    elif db_handler.check_renavam_exists(renavam):
                        st.error("Veículo com este Renavam já cadastrado!")
                    else:
                        success, message = db_handler.add_vehicle(
                            placa.upper(), modelo, int(ano), renavam, km_atual,
                            tipo_combustivel, numero_frota or None, hodometro_horas
                        )
                        if success:
                            st.success(message)
                            st.rerun()
                        else:
                            st.error(message)
                else:
                    st.warning("Preencha todos os campos obrigatórios (*)")
    
    with tab2:
        # Manage Vehicles
        vehicles_df = db_handler.get_vehicles()
        
        if vehicles_df.empty:
            st.info("Nenhum veículo cadastrado.")
        else:
            # Search Bar
            search_query = st.text_input("🔍 Localizar Veículo", placeholder="Busque por Placa ou Modelo...").strip().lower()
            if search_query:
                vehicles_df = vehicles_df[
                    vehicles_df['placa'].str.lower().str.contains(search_query) |
                    vehicles_df['modelo'].str.lower().str.contains(search_query)
                ]

            if vehicles_df.empty:
                 st.info("Nenhum veículo encontrado para a busca.")
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
                    comb_label = {
                        'flex': 'Flex', 'gasolina': 'Gasolina', 'etanol': 'Etanol',
                        'diesel_s10': 'Diesel S10', 'diesel_s500': 'Diesel S500', 'gnv': 'GNV'
                    }.get(str(row.get('tipo_combustivel', 'flex')), 'Flex')

                    with st.expander(f"🚙 {row['modelo']} - Placa: {row['placa']} | Frota: {row.get('numero_frota', '—') or '—'}"):
                        col1, col2 = st.columns([3, 1])

                        with col1:
                            c1, c2, c3 = st.columns(3)
                            with c1:
                                st.write(f"**Placa:** {row['placa']}")
                                st.write(f"**Modelo:** {row['modelo']}")
                                st.write(f"**Ano:** {row['ano']}")
                            with c2:
                                st.write(f"**Renavam:** {row['renavam']}")
                                st.write(f"**Frota:** {row.get('numero_frota', '—') or '—'}")
                                st.write(f"**Combustível:** {comb_label}")
                            with c3:
                                st.write(f"**Km Atual:** {float(row['km_atual'] or 0):,.0f} km")
                                horas = float(row.get('hodometro_horas') or 0)
                                if horas > 0:
                                    st.write(f"**Horas Motor:** {horas:,.0f} h")

                        with col2:
                            if st.button("✏️ Editar", key=f"edit_vehicle_{row['id']}"):
                                st.session_state[f'editing_vehicle_{row["id"]}'] = True
                                st.rerun()
                            if st.button("🗑️ Excluir", key=f"delete_vehicle_{row['id']}"):
                                success, message = db_handler.delete_vehicle(row['id'])
                                if success:
                                    st.success(message)
                                    st.rerun()
                                else:
                                    st.error(message)

                        if st.session_state.get(f'editing_vehicle_{row["id"]}', False):
                            st.divider()
                            st.subheader("Editar Veículo")
                            comb_options = ['flex', 'gasolina', 'etanol', 'diesel_s10', 'diesel_s500', 'gnv']
                            comb_current = str(row.get('tipo_combustivel', 'flex') or 'flex')
                            comb_idx = comb_options.index(comb_current) if comb_current in comb_options else 0

                            with st.form(f"edit_form_{row['id']}"):
                                ec1, ec2 = st.columns(2)
                                with ec1:
                                    edit_placa = st.text_input("Placa", value=row['placa'])
                                    edit_modelo = st.text_input("Modelo", value=row['modelo'])
                                    edit_ano = st.number_input("Ano", min_value=1900,
                                        max_value=datetime.datetime.now().year + 1,
                                        step=1, value=int(row['ano']))
                                    edit_renavam = st.text_input("Renavam", value=row['renavam'])
                                with ec2:
                                    edit_km = st.number_input("Quilometragem Atual", min_value=0.0,
                                        step=1.0, value=float(row['km_atual'] or 0))
                                    edit_comb = st.selectbox("Combustível", comb_options,
                                        index=comb_idx,
                                        format_func=lambda x: {
                                            'flex': 'Flex', 'gasolina': 'Gasolina',
                                            'etanol': 'Etanol', 'diesel_s10': 'Diesel S10',
                                            'diesel_s500': 'Diesel S500', 'gnv': 'GNV'
                                        }.get(x, x))
                                    edit_frota = st.text_input("Número da Frota",
                                        value=str(row.get('numero_frota', '') or ''))
                                    edit_horas = st.number_input("Horas do Motor", min_value=0.0,
                                        step=1.0, value=float(row.get('hodometro_horas') or 0))

                                col_save, col_cancel = st.columns(2)
                                with col_save:
                                    save_button = st.form_submit_button("💾 Salvar Alterações")
                                with col_cancel:
                                    cancel_button = st.form_submit_button("❌ Cancelar")

                                if save_button:
                                    success, message = db_handler.update_vehicle(
                                        row['id'], edit_placa, edit_modelo, int(edit_ano),
                                        edit_renavam, edit_km,
                                        edit_comb, edit_frota or None, edit_horas
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
