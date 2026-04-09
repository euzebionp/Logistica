import streamlit as st
import db_handler
import utils
from datetime import datetime, timedelta
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
import io

def generate_maintenance_pdf(maintenance_df):
    """Generate PDF report of maintenance history."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    elements = []
    styles = getSampleStyleSheet()
    
    # Title
    elements.append(Paragraph("Relatório de Manutenções", styles['Title']))
    elements.append(Spacer(1, 12))
    
    # Summary
    total_records = len(maintenance_df)
    total_cost = maintenance_df['valor'].sum()
    elements.append(Paragraph(f"Total de Registros: {total_records}", styles['Normal']))
    elements.append(Paragraph(f"Custo Total: R$ {total_cost:,.2f}", styles['Normal']))
    elements.append(Spacer(1, 24))
    
    # Table Data
    data = [['Data', 'Veículo', 'Serviço', 'Km', 'Valor']]
    
    for index, row in maintenance_df.iterrows():
        formatted_date = utils.format_date_br(row['data'])
        data.append([
            formatted_date,
            row['veiculo_placa'],
            row['tipo_servico'],
            f"{row['km_realizado']:.0f} km",
            f"R$ {row['valor']:.2f}"
        ])
    
    # Table Style
    table = Table(data, colWidths=[70, 100, 150, 80, 80])
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

def maintenance_page():
    st.header("Controle de Manutenções")
    
    # Check for alerts
    alerts_df = db_handler.get_maintenance_alerts()
    if not alerts_df.empty:
        st.error(f"⚠️ **ALERTA DE MANUTENÇÃO:** {len(alerts_df)} veículo(s) precisam de atenção!")
        with st.expander("Ver Veículos com Manutenção Próxima/Vencida"):
            for index, row in alerts_df.iterrows():
                km_diff = row['proximo_servico_km'] - row['km_atual']
                status_msg = ""
                if km_diff < 0:
                    status_msg = f"🔴 VENCIDA por {abs(km_diff):.0f} km"
                else:
                    status_msg = f"⚠️ Vence em {km_diff:.0f} km"
                
                st.write(f"**{row['modelo']} ({row['placa']})** - Km Atual: {row['km_atual']:.0f} - Próx. Serviço: {row['proximo_servico_km']:.0f} - **{status_msg}**")

    # Tabs
    tab1, tab2, tab3 = st.tabs(["Registrar Manutenção", "Histórico de Manutenções", "Relatório de Veículos"])
    
    with tab1:
        st.subheader("Nova Manutenção")
        
        vehicles_df = db_handler.get_vehicles()
        if vehicles_df.empty:
            st.warning("Cadastre veículos antes de registrar manutenções.")
        else:
            vehicle_options = {f"{row['placa']} - {row['modelo']}": row['id'] for _, row in vehicles_df.iterrows()}
            
            with st.form("maintenance_form"):
                col1, col2 = st.columns(2)
                with col1:
                    selected_vehicle_label = st.selectbox("Veículo", list(vehicle_options.keys()))
                    data = st.date_input("Data do Serviço")
                    tipo_servico = st.selectbox("Tipo de Serviço", ["Troca de Óleo", "Revisão Geral", "Troca de Pneus", "Freios", "Outros"])
                
                with col2:
                    # Try to get current km of selected vehicle to suggest
                    selected_vehicle_id = vehicle_options[selected_vehicle_label]
                    vehicle_data = db_handler.get_vehicle_by_id(selected_vehicle_id)
                    current_km = vehicle_data['km_atual'] if vehicle_data else 0
                    
                    km_realizado = st.number_input("Quilometragem Atual (Km)", min_value=0.0, value=float(current_km), step=1.0)
                    valor = st.number_input("Valor (R$)", min_value=0.0, step=0.01)
                
                st.markdown("---")
                st.write("**Previsão do Próximo Serviço**")
                
                # Calculate next service km based on service type
                if tipo_servico == "Troca de Óleo":
                    default_next_km = km_realizado + 10000
                    km_help = "Troca de óleo: automaticamente +10.000km"
                elif tipo_servico == "Revisão Geral":
                    default_next_km = km_realizado + 20000
                    km_help = "Revisão geral: sugestão de +20.000km"
                elif tipo_servico == "Troca de Pneus":
                    default_next_km = km_realizado + 40000
                    km_help = "Troca de pneus: sugestão de +40.000km"
                elif tipo_servico == "Freios":
                    default_next_km = km_realizado + 30000
                    km_help = "Freios: sugestão de +30.000km"
                else:
                    default_next_km = km_realizado + 10000
                    km_help = "Defina a quilometragem da próxima revisão"
                
                col3, col4 = st.columns(2)
                with col3:
                    proximo_km = st.number_input("Próxima Revisão (Km)", min_value=0.0, value=float(default_next_km), step=100.0, help=km_help)
                with col4:
                    proximo_data = st.date_input("Data Prevista", value=datetime.now() + timedelta(days=180), help="Estimativa de 6 meses")
                
                descricao = st.text_area("Observações / Detalhes do Serviço")
                
                submit_button = st.form_submit_button("💾 Salvar Manutenção")
                
                if submit_button:
                    if tipo_servico and valor > 0:
                        success, message = db_handler.add_maintenance(
                            selected_vehicle_id, str(data), tipo_servico, descricao, 
                            km_realizado, proximo_km, str(proximo_data), valor
                        )
                        
                        # Also update vehicle km if the input km is greater than current
                        if km_realizado > current_km:
                            db_handler.update_vehicle(
                                vehicle_data['id'], vehicle_data['placa'], vehicle_data['modelo'], 
                                vehicle_data['ano'], vehicle_data['renavam'], km_realizado
                            )
                        
                        if success:
                            st.success(message)
                            st.rerun()
                        else:
                            st.error(message)
                    else:
                        st.warning("Preencha os campos obrigatórios.")

    with tab2:
        st.subheader("Histórico")
        maintenance_df = db_handler.get_maintenances()
        
        if maintenance_df.empty:
            st.info("Nenhuma manutenção registrada.")
        else:
            # Search Bar
            search_query = st.text_input("🔍 Localizar Manutenção", placeholder="Busque por Veículo, Placa ou Serviço...").strip().lower()
            if search_query:
                maintenance_df = maintenance_df[
                    maintenance_df['veiculo_placa'].str.lower().str.contains(search_query) |
                    maintenance_df['veiculo_modelo'].str.lower().str.contains(search_query) |
                    maintenance_df['tipo_servico'].str.lower().str.contains(search_query)
                ]

            if maintenance_df.empty:
                st.info("Nenhuma manutenção encontrada para a busca.")
            else:
                # Print button
                col_print, col_space = st.columns([1, 3])
                with col_print:
                    if st.button("🖨️ Imprimir Relatório", use_container_width=True):
                        pdf_buffer = generate_maintenance_pdf(maintenance_df)
                        st.download_button(
                            label="📥 Baixar PDF",
                            data=pdf_buffer,
                            file_name="relatorio_manutencao.pdf",
                            mime="application/pdf",
                            use_container_width=True
                        )
                
                for index, row in maintenance_df.iterrows():
                    formatted_date = utils.format_date_br(row['data'])
                    window_title = f"🔧 {formatted_date} - {row['veiculo_modelo']} - {row['tipo_servico']}"
                    with st.expander(window_title):
                        col1, col2 = st.columns([3, 1])
                        with col1:
                            st.write(f"**Veículo:** {row['veiculo_placa']} - {row['veiculo_modelo']}")
                            st.write(f"**Serviço:** {row['tipo_servico']}")
                            st.write(f"**Km Realizado:** {row['km_realizado']:.0f} km")
                            st.write(f"**Valor:** R$ {row['valor']:.2f}")
                            st.write(f"**Próxima Revisão:** {row['proximo_servico_km']:.0f} km")
                            st.write(f"**Descrição:** {row['descricao']}")
                        
                        with col2:
                            if st.button("🗑️ Excluir", key=f"del_maint_{row['id']}"):
                                success, msg = db_handler.delete_maintenance(row['id'])
                                if success:
                                    st.success(msg)
                                    st.rerun()
                                else:
                                    st.error(msg)
    
    with tab3:
        st.subheader("Relatório de Veículos e Atualização em Lote")
        
        vehicles_df = db_handler.get_vehicles()
        
        if vehicles_df.empty:
            st.warning("Nenhum veículo cadastrado.")
        else:
            # Get maintenance info for each vehicle
            maintenance_info = []
            for _, vehicle in vehicles_df.iterrows():
                # Get latest maintenance
                conn = db_handler.get_connection()
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT proximo_servico_km, proximo_servico_data, tipo_servico, data
                    FROM manutencoes 
                    WHERE veiculo_id = ?
                    ORDER BY data DESC
                    LIMIT 1
                ''', (vehicle['id'],))
                result = cursor.fetchone()
                conn.close()
                
                if result:
                    maintenance_info.append({
                        'id': vehicle['id'],
                        'placa': vehicle['placa'],
                        'modelo': vehicle['modelo'],
                        'ano': vehicle['ano'],
                        'km_atual': vehicle['km_atual'],
                        'proximo_servico_km': result[0] if result[0] else '',
                        'proximo_servico_data': result[1] if result[1] else '',
                        'ultimo_servico': result[2] if result[2] else '',
                        'data_ultimo_servico': result[3] if result[3] else ''
                    })
                else:
                    maintenance_info.append({
                        'id': vehicle['id'],
                        'placa': vehicle['placa'],
                        'modelo': vehicle['modelo'],
                        'ano': vehicle['ano'],
                        'km_atual': vehicle['km_atual'],
                        'proximo_servico_km': '',
                        'proximo_servico_data': '',
                        'ultimo_servico': 'Sem registro',
                        'data_ultimo_servico': ''
                    })
            
            report_df = pd.DataFrame(maintenance_info)
            
            # Display summary
            st.markdown("### 📊 Resumo")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total de Veículos", len(report_df))
            with col2:
                vehicles_with_maintenance = len(report_df[report_df['proximo_servico_km'] != ''])
                st.metric("Com Manutenção Programada", vehicles_with_maintenance)
            with col3:
                vehicles_without_maintenance = len(report_df[report_df['proximo_servico_km'] == ''])
                st.metric("Sem Manutenção Programada", vehicles_without_maintenance)
            
            st.markdown("---")
            
            # Export/Import section
            col_export, col_import = st.columns(2)
            
            with col_export:
                st.markdown("### 📤 Exportar Modelo CSV")
                st.write("Baixe o arquivo CSV com os dados atuais dos veículos para edição:")
                
                # Prepare CSV for export
                export_df = report_df[['placa', 'modelo', 'ano', 'km_atual', 'proximo_servico_km', 'proximo_servico_data']].copy()
                export_df.columns = ['Placa', 'Modelo', 'Ano', 'KM_Atual', 'Proximo_Servico_KM', 'Proximo_Servico_Data']
                
                csv_buffer = io.StringIO()
                export_df.to_csv(csv_buffer, index=False, encoding='utf-8-sig')
                csv_data = csv_buffer.getvalue()
                
                st.download_button(
                    label="📥 Baixar CSV Modelo",
                    data=csv_data,
                    file_name=f"veiculos_manutencao_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv",
                    use_container_width=True
                )
                
                st.info("""
                **Instruções:**
                1. Baixe o arquivo CSV
                2. Edite as colunas `KM_Atual`, `Proximo_Servico_KM` e `Proximo_Servico_Data`
                3. Salve o arquivo
                4. Importe de volta usando o botão ao lado
                """)
            
            with col_import:
                st.markdown("### 📥 Importar CSV Atualizado")
                st.write("Faça upload do CSV editado para atualizar os dados:")
                
                uploaded_file = st.file_uploader(
                    "Selecione o arquivo CSV",
                    type=['csv'],
                    help="Arquivo CSV com as colunas: Placa, Modelo, Ano, KM_Atual, Proximo_Servico_KM, Proximo_Servico_Data"
                )
                
                if uploaded_file is not None:
                    try:
                        import_df = pd.read_csv(uploaded_file, encoding='utf-8-sig')
                        
                        # Validate columns
                        required_cols = ['Placa', 'KM_Atual']
                        missing_cols = [col for col in required_cols if col not in import_df.columns]
                        
                        if missing_cols:
                            st.error(f"❌ Colunas obrigatórias faltando: {', '.join(missing_cols)}")
                        else:
                            st.success(f"✅ Arquivo carregado com {len(import_df)} registros")
                            
                            # Preview
                            with st.expander("👁️ Visualizar Dados Importados"):
                                st.dataframe(import_df, use_container_width=True)
                            
                            if st.button("🔄 Processar Atualização", type="primary", use_container_width=True):
                                success_count = 0
                                error_count = 0
                                errors = []
                                
                                progress_bar = st.progress(0)
                                status_text = st.empty()
                                
                                for idx, row in import_df.iterrows():
                                    try:
                                        placa = str(row['Placa']).strip().upper()
                                        
                                        # Find vehicle by plate
                                        vehicle = vehicles_df[vehicles_df['placa'].str.upper() == placa]
                                        
                                        if vehicle.empty:
                                            errors.append(f"Placa {placa} não encontrada")
                                            error_count += 1
                                            continue
                                        
                                        vehicle_id = vehicle.iloc[0]['id']
                                        vehicle_data = db_handler.get_vehicle_by_id(vehicle_id)
                                        
                                        # Update km_atual
                                        new_km = float(row['KM_Atual']) if pd.notna(row['KM_Atual']) else vehicle_data['km_atual']
                                        
                                        # Update vehicle
                                        success, msg = db_handler.update_vehicle(
                                            vehicle_id,
                                            vehicle_data['placa'],
                                            vehicle_data['modelo'],
                                            vehicle_data['ano'],
                                            vehicle_data['renavam'],
                                            new_km
                                        )
                                        
                                        if success:
                                            # Check if there's maintenance scheduling info
                                            if 'Proximo_Servico_KM' in import_df.columns and pd.notna(row['Proximo_Servico_KM']):
                                                proximo_km = float(row['Proximo_Servico_KM'])
                                                proximo_data = str(row['Proximo_Servico_Data']) if 'Proximo_Servico_Data' in import_df.columns and pd.notna(row['Proximo_Servico_Data']) else str(datetime.now().date())
                                                
                                                # Add maintenance record for scheduling
                                                db_handler.add_maintenance(
                                                    vehicle_id,
                                                    str(datetime.now().date()),
                                                    "Atualização via CSV",
                                                    f"Atualização em lote - KM: {new_km}",
                                                    new_km,
                                                    proximo_km,
                                                    proximo_data,
                                                    0.0
                                                )
                                            
                                            success_count += 1
                                        else:
                                            errors.append(f"Placa {placa}: {msg}")
                                            error_count += 1
                                        
                                    except Exception as e:
                                        errors.append(f"Linha {idx + 2}: {str(e)}")
                                        error_count += 1
                                    
                                    # Update progress
                                    progress = (idx + 1) / len(import_df)
                                    progress_bar.progress(progress)
                                    status_text.text(f"Processando... {idx + 1}/{len(import_df)}")
                                
                                progress_bar.empty()
                                status_text.empty()
                                
                                # Show results
                                st.markdown("---")
                                st.markdown("### 📊 Resultado da Importação")
                                
                                col_success, col_error = st.columns(2)
                                with col_success:
                                    st.success(f"✅ **{success_count}** registros atualizados com sucesso")
                                with col_error:
                                    if error_count > 0:
                                        st.error(f"❌ **{error_count}** erros encontrados")
                                
                                if errors:
                                    with st.expander("⚠️ Ver Erros"):
                                        for error in errors:
                                            st.write(f"• {error}")
                                
                                if success_count > 0:
                                    st.balloons()
                                    st.info("🔄 Recarregue a página para ver as atualizações")
                    
                    except Exception as e:
                        st.error(f"❌ Erro ao processar arquivo: {str(e)}")
            
            st.markdown("---")
            
            # Display vehicles table
            st.markdown("### 📋 Lista de Veículos")
            
            # Format display dataframe
            display_df = report_df.copy()
            display_df['km_atual'] = display_df['km_atual'].apply(lambda x: f"{x:,.0f} km" if pd.notna(x) else "0 km")
            display_df['proximo_servico_km'] = display_df['proximo_servico_km'].apply(lambda x: f"{x:,.0f} km" if x != '' and pd.notna(x) else "Não programado")
            display_df['data_ultimo_servico'] = display_df['data_ultimo_servico'].apply(lambda x: utils.format_date_br(x) if x != '' else "N/A")
            display_df['proximo_servico_data'] = display_df['proximo_servico_data'].apply(lambda x: utils.format_date_br(x) if x != '' else "N/A")
            
            # Rename columns for display
            display_df = display_df[['placa', 'modelo', 'ano', 'km_atual', 'ultimo_servico', 'data_ultimo_servico', 'proximo_servico_km', 'proximo_servico_data']]
            display_df.columns = ['Placa', 'Modelo', 'Ano', 'KM Atual', 'Último Serviço', 'Data Último Serviço', 'Próximo Serviço (KM)', 'Data Próximo Serviço']
            
            st.dataframe(display_df, use_container_width=True, hide_index=True)

