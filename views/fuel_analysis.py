import streamlit as st
import db_handler
import pandas as pd
import io
from datetime import datetime, date

# ─── Referências de rendimento por combustível ───────────────────────────────
RENDIMENTO_REF = {
    'flex':        {'esperado': 12.0, 'alerta': 8.0,  'label': 'Flex'},
    'gasolina':    {'esperado': 12.0, 'alerta': 8.0,  'label': 'Gasolina'},
    'etanol':      {'esperado': 8.5,  'alerta': 6.0,  'label': 'Etanol'},
    'diesel_s10':  {'esperado': 14.0, 'alerta': 10.0, 'label': 'Diesel S10'},
    'diesel_s500': {'esperado': 12.0, 'alerta': 8.0,  'label': 'Diesel S500'},
    'gnv':         {'esperado': 11.0, 'alerta': 7.0,  'label': 'GNV'},
}

# Mapeamento de colunas tolerante a variações do sistema de abastecimento
COL_MAP = {
    'data':            ['Data', 'DATA', 'data'],
    'identificacao':   ['Identificação', 'Identificacao', 'IDENTIFICACAO', 'Placa', 'PLACA', 'ID', 'id'],
    'numero_frota':    ['Frota', 'FROTA', 'Num.Frota', 'NumFrota'],
    'tipo_combustivel':['Combustível', 'Combustivel', 'COMBUSTIVEL', 'Tipo'],
    'volume_litros':   ['Qt. Litros', 'Qt.Litros', 'QtLitros', 'Litros', 'Volume', 'LITROS', 'QT. LITROS'],
    'preco_litro':     ['Preco', 'Preço', 'PRECO', 'Preco_Litro', 'PreçoLitro'],
    'valor_total':     ['Total', 'TOTAL', 'Valor_Total', 'ValorTotal'],
    'km_anterior':     ['Km Anterior', 'KmAnterior', 'KM ANTERIOR', 'KM_ANTERIOR'],
    'km_atual':        ['Km Atual', 'KmAtual', 'KM ATUAL', 'KM_ATUAL', 'KM BOMBA'],
}


def _find_col(df_cols, candidates):
    """Find the first matching column name."""
    for c in candidates:
        if c in df_cols:
            return c
    return None


def _parse_number(val):
    """Parse Brazilian number format (comma as decimal)."""
    if pd.isna(val):
        return None
    s = str(val).strip().replace(' ', '').replace('.', '').replace(',', '.')
    try:
        return float(s)
    except ValueError:
        return None


def _normalize_combustivel(val):
    """Normalize fuel type string from spreadsheet."""
    if not val:
        return 'diesel_s10'
    v = str(val).strip().lower()
    if 's10' in v:
        return 'diesel_s10'
    if 's500' in v or 's 500' in v:
        return 'diesel_s500'
    if 'diesel' in v:
        return 'diesel_s10'
    if 'gasolina' in v or 'gasol' in v:
        return 'gasolina'
    if 'etanol' in v or 'alcool' in v or 'álcool' in v:
        return 'etanol'
    if 'gnv' in v or 'gas' in v:
        return 'gnv'
    return 'flex'


def fuel_analysis_page():
    st.header("⛽ Combustível e Rendimento")

    tab1, tab2, tab3 = st.tabs([
        "📥 Importar Planilha",
        "📊 Análise por Veículo",
        "🏭 Painel da Frota",
    ])

    # ─────────────────────────────────────────────────────────────────────────
    with tab1:
        st.subheader("Importar Planilha de Abastecimento")

        col_info, col_modelo = st.columns([2, 1])
        with col_info:
            st.info("""
**Formato esperado da planilha:**

| Data | Identificação | Frota | Combustível | Qt. Litros | Preco | Total | Km Anterior | Km Atual |
|---|---|---|---|---|---|---|---|---|
| 19/03/2026 00:06 | UAB2G88 | 67 | DIESEL S10 | 119,96 | 5,779 | 693,25 | 1115 | 11316 |

O sistema aceita arquivos **.CSV** e **.XLSX** (Excel).
""")
        with col_modelo:
            # Generate template CSV
            template_data = {
                'Data': ['19/03/2026 00:06', '19/03/2026 00:11'],
                'Identificação': ['PLACA001', 'PLACA002'],
                'Frota': [67, 66],
                'Combustível': ['DIESEL S10', 'GASOLINA'],
                'Qt. Litros': ['119,96', '88,11'],
                'Preco': ['5,779', '5,890'],
                'Total': ['693,25', '519,20'],
                'Km Anterior': [1115, 10384],
                'Km Atual': [11316, 10562],
            }
            tpl_df = pd.DataFrame(template_data)
            buf = io.StringIO()
            tpl_df.to_csv(buf, index=False, sep=';', encoding='utf-8-sig')
            st.download_button(
                "📥 Baixar Modelo CSV",
                data=buf.getvalue(),
                file_name="modelo_abastecimento.csv",
                mime="text/csv",
                use_container_width=True
            )

        st.divider()

        uploaded = st.file_uploader(
            "Selecione o arquivo da planilha de abastecimento",
            type=['csv', 'xlsx', 'xls'],
            help="Arquivos gerados pelo sistema de abastecimento"
        )

        if uploaded:
            try:
                # ── Read file ─────────────────────────────────────────────
                if uploaded.name.endswith(('.xlsx', '.xls')):
                    raw_df = pd.read_excel(uploaded, dtype=str)
                else:
                    # Try different separators
                    content = uploaded.read()
                    for sep in [';', ',', '\t']:
                        try:
                            raw_df = pd.read_csv(io.BytesIO(content), sep=sep,
                                                  dtype=str, encoding='utf-8-sig')
                            if len(raw_df.columns) > 3:
                                break
                        except Exception:
                            continue

                st.success(f"✅ Arquivo lido: **{len(raw_df)} registros** | Colunas: {', '.join(raw_df.columns.tolist())}")

                # ── Map columns ───────────────────────────────────────────
                col_map_found = {}
                for field, candidates in COL_MAP.items():
                    found = _find_col(raw_df.columns.tolist(), candidates)
                    col_map_found[field] = found

                missing = [f for f, c in col_map_found.items()
                           if c is None and f in ('identificacao', 'km_atual', 'volume_litros')]
                if missing:
                    st.error(f"❌ Colunas obrigatórias não encontradas: {missing}")
                    st.write("Colunas no arquivo:", raw_df.columns.tolist())
                    st.stop()

                # ── Build normalized dataframe ────────────────────────────
                rows = []
                vehicles_df = db_handler.get_vehicles()
                lote = f"lote_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

                for _, r in raw_df.iterrows():
                    identificacao = str(r.get(col_map_found.get('identificacao', ''), '') or '').strip()
                    if not identificacao or identificacao.lower() in ('nan', ''):
                        continue

                    frota_raw = str(r.get(col_map_found.get('numero_frota', ''), '') or '').strip()
                    data_raw   = str(r.get(col_map_found.get('data', ''), '') or '').strip()
                    comb_raw   = str(r.get(col_map_found.get('tipo_combustivel', ''), '') or '').strip()
                    litros     = _parse_number(r.get(col_map_found.get('volume_litros', ''), 0))
                    preco      = _parse_number(r.get(col_map_found.get('preco_litro', ''), 0))
                    total      = _parse_number(r.get(col_map_found.get('valor_total', ''), 0))
                    km_ant     = _parse_number(r.get(col_map_found.get('km_anterior', ''), 0)) or 0
                    km_now     = _parse_number(r.get(col_map_found.get('km_atual', ''), 0))

                    if km_now is None or litros is None or litros <= 0:
                        continue

                    comb_norm = _normalize_combustivel(comb_raw)
                    km_rod = km_now - km_ant if km_ant and km_ant > 0 else None
                    rendimento = round(km_rod / litros, 2) if km_rod and km_rod > 0 and litros > 0 else None

                    # Find vehicle in DB
                    veiculo_id = db_handler.get_vehicle_by_placa_or_frota(identificacao, frota_raw)

                    # Validation
                    alertas = []
                    if km_ant > 0 and km_now < km_ant:
                        alertas.append("⚠️ KM atual < KM anterior")
                    if km_rod and km_rod > 1500:
                        alertas.append("⚠️ KM rodados muito alto (possível erro)")
                    if rendimento and rendimento < 2:
                        alertas.append("⚠️ Rendimento suspeito (<2 km/L)")
                    if not veiculo_id:
                        alertas.append("❓ Veículo não cadastrado no sistema")

                    placa_display = identificacao
                    modelo_display = '—'
                    if veiculo_id:
                        v = vehicles_df[vehicles_df['id'] == veiculo_id]
                        if not v.empty:
                            placa_display = v.iloc[0]['placa']
                            modelo_display = v.iloc[0]['modelo']

                    rows.append({
                        'identificacao': identificacao,
                        'placa': placa_display,
                        'modelo': modelo_display,
                        'frota': frota_raw,
                        'data': data_raw,
                        'combustivel': comb_raw,
                        'comb_norm': comb_norm,
                        'litros': litros,
                        'preco': preco or 0,
                        'total': total or (litros * (preco or 0)),
                        'km_anterior': km_ant,
                        'km_atual': km_now,
                        'km_rodados': km_rod,
                        'rendimento': rendimento,
                        'veiculo_id': veiculo_id,
                        'alertas': ' | '.join(alertas) if alertas else '✅ OK',
                        'lote': lote,
                    })

                if not rows:
                    st.warning("Nenhum registro válido encontrado no arquivo.")
                    st.stop()

                preview_df = pd.DataFrame(rows)

                # ── Preview ───────────────────────────────────────────────
                st.markdown("### 👁️ Preview — Dados a Importar")

                # Summary metrics
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Total de Registros", len(preview_df))
                c2.metric("Veículos Identificados",
                          int(preview_df['veiculo_id'].notna().sum()))
                c3.metric("Não Cadastrados",
                          int(preview_df['veiculo_id'].isna().sum()))
                ok_count = int((preview_df['alertas'] == '✅ OK').sum())
                c4.metric("Com Alertas", len(preview_df) - ok_count)

                # Preview table
                display_cols = ['placa', 'modelo', 'frota', 'data', 'combustivel',
                                'litros', 'total', 'km_anterior', 'km_atual',
                                'km_rodados', 'rendimento', 'alertas']
                disp = preview_df[display_cols].copy()
                disp.columns = ['Placa', 'Modelo', 'Frota', 'Data', 'Combustível',
                                'Litros', 'Total R$', 'Km Ant.', 'Km Atual',
                                'Km Rodados', 'km/L', 'Status']

                def highlight_alert(row):
                    if row['Status'] != '✅ OK':
                        return ['background-color: #fff3cd'] * len(row)
                    return [''] * len(row)

                st.dataframe(disp.style.apply(highlight_alert, axis=1),
                             use_container_width=True, hide_index=True)

                # ── Import button ──────────────────────────────────────────
                st.divider()
                col_btn, col_opt = st.columns([1, 2])
                with col_opt:
                    import_invalid = st.checkbox(
                        "Importar também registros com alertas",
                        value=True,
                        help="Desmarcando, apenas registros '✅ OK' serão importados"
                    )

                with col_btn:
                    if st.button("🔄 Confirmar Importação", type="primary",
                                 use_container_width=True):
                        success_count = 0
                        error_count = 0
                        progress = st.progress(0)
                        status = st.empty()

                        rows_to_import = preview_df if import_invalid else \
                            preview_df[preview_df['alertas'] == '✅ OK']

                        for i, (_, rec) in enumerate(rows_to_import.iterrows()):
                            ok, _ = db_handler.add_abastecimento(
                                veiculo_id=rec['veiculo_id'],
                                identificacao=rec['identificacao'],
                                numero_frota=rec['frota'],
                                data=rec['data'],
                                tipo_combustivel=rec['comb_norm'],
                                volume_litros=rec['litros'],
                                preco_litro=rec['preco'],
                                valor_total=rec['total'],
                                km_anterior=rec['km_anterior'],
                                km_atual_bomba=rec['km_atual'],
                                lote_importacao=rec['lote']
                            )
                            if ok:
                                success_count += 1
                            else:
                                error_count += 1
                            progress.progress((i + 1) / len(rows_to_import))
                            status.text(f"Processando {i + 1}/{len(rows_to_import)}…")

                        progress.empty()
                        status.empty()
                        st.success(f"✅ **{success_count}** registros importados com sucesso!")
                        if error_count:
                            st.error(f"❌ {error_count} registros com erro.")
                        st.balloons()

            except Exception as e:
                st.error(f"Erro ao processar arquivo: {e}")
                import traceback
                st.code(traceback.format_exc())

    # ─────────────────────────────────────────────────────────────────────────
    with tab2:
        st.subheader("Análise por Veículo")

        vehicles_df = db_handler.get_vehicles()
        if vehicles_df.empty:
            st.info("Nenhum veículo cadastrado.")
        else:
            all_df = db_handler.get_abastecimentos()
            if all_df.empty:
                st.info("Nenhum abastecimento importado ainda.")
            else:
                vehicle_options = {
                    f"{row['placa']} - {row['modelo']}": row['id']
                    for _, row in vehicles_df.iterrows()
                }
                sel_label = st.selectbox("Selecione o Veículo", list(vehicle_options.keys()))
                sel_id = vehicle_options[sel_label]

                vdf = db_handler.get_abastecimentos(veiculo_id=sel_id)

                if vdf.empty:
                    st.info("Nenhum abastecimento registrado para este veículo.")
                else:
                    valid = vdf[vdf['rendimento_kml'].notna() & (vdf['rendimento_kml'] > 0)]

                    # Get vehicle fuel type for reference
                    v_data = db_handler.get_vehicle_by_id(sel_id)
                    comb_key = (v_data or {}).get('tipo_combustivel', 'flex') or 'flex'
                    ref = RENDIMENTO_REF.get(comb_key, RENDIMENTO_REF['flex'])

                    # Metrics
                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("Total Abastecimentos", len(vdf))
                    c2.metric("Total Litros", f"{vdf['volume_litros'].sum():,.1f} L")
                    c3.metric("Gasto Total", f"R$ {vdf['valor_total'].sum():,.2f}")
                    med_rend = valid['rendimento_kml'].mean() if not valid.empty else 0
                    delta_rend = f"{med_rend - ref['esperado']:+.1f} vs ref."
                    c4.metric("Média km/L", f"{med_rend:.2f}", delta_rend)

                    if not valid.empty:
                        # Alert band
                        if med_rend < ref['alerta']:
                            st.error(f"🔴 Rendimento CRÍTICO! Média {med_rend:.2f} km/L abaixo do alerta ({ref['alerta']} km/L)")
                        elif med_rend < ref['esperado']:
                            st.warning(f"🟡 Rendimento abaixo do esperado ({ref['esperado']} km/L para {ref['label']})")
                        else:
                            st.success(f"🟢 Rendimento dentro do esperado para {ref['label']}")

                        # History table
                        st.markdown("#### Histórico de Abastecimentos")
                        hist = vdf[['data', 'tipo_combustivel', 'volume_litros',
                                    'valor_total', 'km_anterior', 'km_atual',
                                    'km_rodados', 'rendimento_kml']].copy()
                        hist.columns = ['Data', 'Combustível', 'Litros', 'Total R$',
                                        'Km Ant.', 'Km Atual', 'Km Rodados', 'km/L']
                        st.dataframe(hist, use_container_width=True, hide_index=True)

    # ─────────────────────────────────────────────────────────────────────────
    with tab3:
        st.subheader("🏭 Painel Geral da Frota")

        summary_df = db_handler.get_fleet_fuel_summary()

        if summary_df.empty:
            st.info("Nenhum dado de abastecimento disponível. Importe uma planilha primeiro.")
        else:
            # Fleet totals
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Veículos com Dados", len(summary_df))
            c2.metric("Total Litros", f"{summary_df['total_litros'].sum():,.0f} L")
            c3.metric("Gasto Total", f"R$ {summary_df['total_gasto'].sum():,.2f}")
            c4.metric("Total KM Rodados", f"{summary_df['total_km_rodados'].sum():,.0f} km")

            st.divider()
            st.markdown("#### 📋 Tabela Comparativa de Rendimento")

            # Build display table with status
            rows_display = []
            for _, r in summary_df.iterrows():
                comb_key = str(r.get('combustivel', 'flex') or 'flex').lower()
                # Normalize
                if 's10' in comb_key:
                    comb_key = 'diesel_s10'
                elif 'diesel' in comb_key:
                    comb_key = 'diesel_s10'
                elif 'gasolina' in comb_key:
                    comb_key = 'gasolina'
                ref = RENDIMENTO_REF.get(comb_key, RENDIMENTO_REF['flex'])
                med = r['media_rendimento']

                if pd.isna(med) or med == 0:
                    status = '⚪ Sem dados'
                elif med < ref['alerta']:
                    status = '🔴 Crítico'
                elif med < ref['esperado']:
                    status = '🟡 Atenção'
                else:
                    status = '🟢 OK'

                rows_display.append({
                    'Frota': r.get('frota', '—') or '—',
                    'Placa': r.get('placa', '—'),
                    'Modelo': r.get('modelo', '—'),
                    'Combustível': r.get('combustivel', '—'),
                    'Abastec.': int(r.get('total_abastecimentos', 0) or 0),
                    'Total L': f"{r['total_litros']:,.1f}" if pd.notna(r['total_litros']) else '—',
                    'Gasto R$': f"{r['total_gasto']:,.2f}" if pd.notna(r['total_gasto']) else '—',
                    'KM Rodados': f"{r['total_km_rodados']:,.0f}" if pd.notna(r['total_km_rodados']) else '—',
                    'Média km/L': f"{med:.2f}" if pd.notna(med) else '—',
                    'Status': status,
                })

            disp_df = pd.DataFrame(rows_display)
            st.dataframe(disp_df, use_container_width=True, hide_index=True)

            # Rankings
            st.divider()
            col_best, col_worst = st.columns(2)
            valid_summary = summary_df.dropna(subset=['media_rendimento'])
            valid_summary = valid_summary[valid_summary['media_rendimento'] > 0]

            with col_best:
                st.markdown("#### 🏆 Mais Eficientes")
                if not valid_summary.empty:
                    top = valid_summary.nlargest(5, 'media_rendimento')[['placa', 'modelo', 'media_rendimento']]
                    top.columns = ['Placa', 'Modelo', 'km/L']
                    top['km/L'] = top['km/L'].apply(lambda x: f"{x:.2f}")
                    st.dataframe(top, use_container_width=True, hide_index=True)

            with col_worst:
                st.markdown("#### ⚠️ Menos Eficientes")
                if not valid_summary.empty:
                    bot = valid_summary.nsmallest(5, 'media_rendimento')[['placa', 'modelo', 'media_rendimento']]
                    bot.columns = ['Placa', 'Modelo', 'km/L']
                    bot['km/L'] = bot['km/L'].apply(lambda x: f"{x:.2f}")
                    st.dataframe(bot, use_container_width=True, hide_index=True)
