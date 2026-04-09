import streamlit as st
import db_handler
import pandas as pd
import io
from datetime import datetime

# ─── Referências de rendimento por combustível ────────────────────────────────
RENDIMENTO_REF = {
    'flex':        {'esperado': 12.0, 'alerta': 8.0,  'label': 'Flex'},
    'gasolina':    {'esperado': 12.0, 'alerta': 8.0,  'label': 'Gasolina'},
    'etanol':      {'esperado': 8.5,  'alerta': 6.0,  'label': 'Etanol'},
    'diesel_s10':  {'esperado': 14.0, 'alerta': 10.0, 'label': 'Diesel S10'},
    'diesel_s500': {'esperado': 12.0, 'alerta': 8.0,  'label': 'Diesel S500'},
    'gnv':         {'esperado': 11.0, 'alerta': 7.0,  'label': 'GNV'},
}

# Mapeamento tolerante de colunas do sistema de abastecimento
COL_MAP = {
    'data':             ['Data', 'DATA', 'data', 'DT'],
    'identificacao':    ['Identificação', 'Identificacao', 'IDENTIFICACAO',
                         'Placa', 'PLACA', 'ID', 'id', 'PLACA/ID'],
    'numero_frota':     ['Frota', 'FROTA', 'Num.Frota', 'NumFrota',
                         'Nº Frota', 'N.Frota', 'NUMERO_FROTA'],
    'tipo_combustivel': ['Combustível', 'Combustivel', 'COMBUSTIVEL', 'Tipo',
                         'TIPO_COMBUST'],
    'volume_litros':    ['Qt. Litros', 'Qt.Litros', 'QtLitros', 'Litros',
                         'Volume', 'LITROS', 'QT. LITROS', 'Quantidade'],
    'preco_litro':      ['Preco', 'Preço', 'PRECO', 'Preco_Litro', 'PreçoLitro',
                         'Preço/L', 'VL_UNITARIO'],
    'valor_total':      ['Total', 'TOTAL', 'Valor_Total', 'ValorTotal',
                         'VL_TOTAL', 'Valor'],
    'km_anterior':      ['Km Anterior', 'KmAnterior', 'KM ANTERIOR',
                         'KM_ANTERIOR', 'KM_ANT'],
    'km_atual':         ['Km Atual', 'KmAtual', 'KM ATUAL', 'KM_ATUAL',
                         'KM BOMBA', 'KM_BOMBA', 'Hodometro', 'HODOMETRO'],
}


def _find_col(df_cols, candidates):
    for c in candidates:
        if c in df_cols:
            return c
    df_lower = {col.lower(): col for col in df_cols}
    for c in candidates:
        if c.lower() in df_lower:
            return df_lower[c.lower()]
    return None


def _parse_number(val):
    if pd.isna(val):
        return None
    s = str(val).strip().replace(' ', '').replace('.', '').replace(',', '.')
    try:
        return float(s)
    except ValueError:
        return None


def _normalize_combustivel(val):
    if not val:
        return 'diesel_s10'
    v = str(val).strip().lower()
    if 's10' in v:      return 'diesel_s10'
    if 's500' in v:     return 'diesel_s500'
    if 'diesel' in v:   return 'diesel_s10'
    if 'gasolina' in v: return 'gasolina'
    if 'etanol' in v or 'alcool' in v or 'álcool' in v: return 'etanol'
    if 'gnv' in v:      return 'gnv'
    return 'flex'


def _sync_frota_number(veiculo_id, frota_raw, vehicles_df):
    """Atualiza o número de frota do veículo se ele ainda não tiver um."""
    if not frota_raw or str(frota_raw) in ('nan', ''):
        return False
    v_row = vehicles_df[vehicles_df['id'] == veiculo_id]
    if v_row.empty:
        return False
    row = v_row.iloc[0]
    current_frota = str(row.get('numero_frota', '') or '')
    if current_frota in ('', 'nan'):
        db_handler.update_vehicle(
            veiculo_id,
            row['placa'], row['modelo'], int(row['ano']),
            row['renavam'], float(row['km_atual'] or 0),
            tipo_combustivel=str(row.get('tipo_combustivel', 'flex') or 'flex'),
            numero_frota=frota_raw,
            hodometro_horas=float(row.get('hodometro_horas') or 0)
        )
        return True
    return False


def _build_rows(raw_df, col_map_found, vehicles_df, lote):
    """Parse all rows from the raw dataframe into normalized records."""
    rows = []
    for _, r in raw_df.iterrows():
        identificacao = str(
            r.get(col_map_found.get('identificacao', ''), '') or ''
        ).strip()
        if not identificacao or identificacao.lower() in ('nan', ''):
            continue

        frota_raw = str(
            r.get(col_map_found.get('numero_frota', ''), '') or ''
        ).strip()
        if frota_raw.endswith('.0'):
            frota_raw = frota_raw[:-2]

        data_raw = str(r.get(col_map_found.get('data', ''),            '') or '').strip()
        comb_raw = str(r.get(col_map_found.get('tipo_combustivel', ''), '') or '').strip()
        litros   = _parse_number(r.get(col_map_found.get('volume_litros', ''), 0))
        preco    = _parse_number(r.get(col_map_found.get('preco_litro',   ''), 0))
        total    = _parse_number(r.get(col_map_found.get('valor_total',   ''), 0))
        km_ant   = _parse_number(r.get(col_map_found.get('km_anterior',   ''), 0)) or 0
        km_now   = _parse_number(r.get(col_map_found.get('km_atual',      ''), 0))

        if km_now is None or litros is None or litros <= 0:
            continue

        comb_norm  = _normalize_combustivel(comb_raw)
        km_rod     = (km_now - km_ant) if km_ant and km_ant > 0 else None
        rendimento = (
            round(km_rod / litros, 2)
            if km_rod and km_rod > 0 and litros > 0 else None
        )

        veiculo_id = db_handler.get_vehicle_by_placa_or_frota(identificacao, frota_raw)

        match_method = '—'
        placa_display  = identificacao
        modelo_display = '—'
        frota_display  = frota_raw or '—'
        tem_frota_db   = False

        if veiculo_id:
            v_row = vehicles_df[vehicles_df['id'] == veiculo_id]
            if not v_row.empty:
                placa_display  = v_row.iloc[0]['placa']
                modelo_display = v_row.iloc[0]['modelo']
                match_method = (
                    '🔵 Placa'
                    if v_row.iloc[0]['placa'].upper() == identificacao.upper()
                    else '🟣 Frota'
                )
                frota_db = str(v_row.iloc[0].get('numero_frota', '') or '')
                tem_frota_db = frota_db not in ('', 'nan')
                if not tem_frota_db and frota_raw:
                    frota_display = f"{frota_raw} 🆕"

        alertas = []
        if km_ant > 0 and km_now < km_ant:
            alertas.append("⚠️ KM atual < KM anterior")
        if km_rod and km_rod > 2000:
            alertas.append("⚠️ KM rodados alto")
        if rendimento and rendimento < 2:
            alertas.append("⚠️ Rendimento suspeito")
        if not veiculo_id:
            alertas.append("❓ Veículo não cadastrado")

        rows.append({
            'identificacao':     identificacao,
            'frota':             frota_raw,
            'veiculo_id':        veiculo_id,
            'data':              data_raw,
            'comb_norm':         comb_norm,
            'litros':            litros,
            'preco':             preco or 0,
            'total':             total or round(litros * (preco or 0), 2),
            'km_anterior':       km_ant,
            'km_atual':          km_now,
            'km_rodados':        km_rod,
            'rendimento':        rendimento,
            'lote':              lote,
            'sincronizar_frota': bool(veiculo_id and frota_raw and not tem_frota_db),
            'placa':             placa_display,
            'modelo':            modelo_display,
            'frota_display':     frota_display,
            'combustivel':       comb_raw,
            'match':             match_method if veiculo_id else '❓ Não encontrado',
            'alertas':           ' | '.join(alertas) if alertas else '✅ OK',
        })
    return rows


# ─────────────────────────────────────────────────────────────────────────────
def fuel_analysis_page():
    st.header("⛽ Combustível e Rendimento")

    tab1, tab2, tab3 = st.tabs([
        "📥 Importar Planilha",
        "📊 Análise por Veículo",
        "🏭 Painel da Frota",
    ])

    # ═══════════════════════════════════════════════════════════════════════
    # TAB 1 — Importar
    # ═══════════════════════════════════════════════════════════════════════
    with tab1:
        st.subheader("Importar Planilha de Abastecimento")

        col_info, col_modelo = st.columns([2, 1])
        with col_info:
            st.info("""
**Formato esperado (gerado pelo sistema de abastecimento):**

| Data | Identificação | Frota | Combustível | Qt. Litros | Preco | Total | Km Anterior | Km Atual |
|---|---|---|---|---|---|---|---|---|
| 19/03/2026 00:06 | UAB2G88 | 67 | DIESEL S10 | 119,96 | 5,779 | 693,25 | 1115 | 11316 |

**Aceita:** `.CSV` e `.XLSX`  
**Busca:** por **Placa** e, se não achar, por **Nº de Frota**.  
O **Nº de Frota é vinculado automaticamente** ao cadastro do veículo.
""")
        with col_modelo:
            tpl = pd.DataFrame({
                'Data': ['19/03/2026 00:06', '19/03/2026 00:11'],
                'Identificação': ['PLACA001', 'PLACA002'],
                'Frota': [67, 66],
                'Combustível': ['DIESEL S10', 'GASOLINA'],
                'Qt. Litros': ['119,96', '88,11'],
                'Preco': ['5,779', '5,890'],
                'Total': ['693,25', '519,20'],
                'Km Anterior': [1115, 10384],
                'Km Atual': [11316, 10562],
            })
            buf = io.StringIO()
            tpl.to_csv(buf, index=False, sep=';', encoding='utf-8-sig')
            st.download_button(
                "📥 Baixar Modelo CSV",
                data=buf.getvalue(),
                file_name="modelo_abastecimento.csv",
                mime="text/csv",
            )

        st.divider()

        uploaded = st.file_uploader(
            "Selecione o arquivo da planilha de abastecimento",
            type=['csv', 'xlsx', 'xls'],
            help="Arquivos gerados pelo sistema de abastecimento"
        )

        if uploaded is not None:
            try:
                # ── Leitura ───────────────────────────────────────────────
                if uploaded.name.endswith(('.xlsx', '.xls')):
                    raw_df = pd.read_excel(uploaded, dtype=str)
                else:
                    content = uploaded.read()
                    raw_df = None
                    for sep in [';', ',', '\t']:
                        try:
                            tmp = pd.read_csv(
                                io.BytesIO(content), sep=sep,
                                dtype=str, encoding='utf-8-sig'
                            )
                            if len(tmp.columns) > 3:
                                raw_df = tmp
                                break
                        except Exception:
                            continue
                    if raw_df is None:
                        st.error(
                            "Não foi possível ler o arquivo. "
                            "Verifique o separador (`;` ou `,`)."
                        )
                        raw_df = pd.DataFrame()

                if not raw_df.empty:
                    st.success(
                        f"✅ **{len(raw_df)} linhas** lidas | "
                        f"Colunas: `{', '.join(raw_df.columns.tolist())}`"
                    )

                    # ── Mapeamento de colunas ─────────────────────────────
                    col_map_found = {
                        field: _find_col(raw_df.columns.tolist(), candidates)
                        for field, candidates in COL_MAP.items()
                    }

                    obrig_faltando = [
                        f for f, c in col_map_found.items()
                        if c is None and f in ('identificacao', 'numero_frota',
                                               'km_atual', 'volume_litros')
                    ]

                    if obrig_faltando:
                        st.error(
                            f"❌ Colunas obrigatórias não encontradas: "
                            f"`{obrig_faltando}`\n\n"
                            f"Colunas no arquivo: `{raw_df.columns.tolist()}`"
                        )
                    else:
                        # ── Normalização ──────────────────────────────────
                        vehicles_df = db_handler.get_vehicles()
                        lote = f"lote_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                        rows = _build_rows(raw_df, col_map_found, vehicles_df, lote)

                        if not rows:
                            st.warning("Nenhum registro válido encontrado no arquivo.")
                        else:
                            preview_df = pd.DataFrame(rows)

                            # Usa versão reconciliada se existir
                            if 'preview_df_reconciled' in st.session_state:
                                preview_df = st.session_state['preview_df_reconciled']

                            # ── Métricas ──────────────────────────────────
                            st.markdown("### 👁️ Preview — Dados a Importar")
                            a_sincronizar = int(preview_df['sincronizar_frota'].sum())
                            c1, c2, c3, c4, c5 = st.columns(5)
                            c1.metric("Total",             len(preview_df))
                            c2.metric("✅ Identificados",   int(preview_df['veiculo_id'].notna().sum()))
                            c3.metric("❓ Não Cadastrados", int(preview_df['veiculo_id'].isna().sum()))
                            c4.metric("🔄 Vincular Frota",  a_sincronizar)
                            c5.metric("⚠️ Com Alertas",    int((preview_df['alertas'] != '✅ OK').sum()))

                            # ── Tabela de preview ─────────────────────────
                            disp = preview_df[[
                                'match', 'frota_display', 'placa', 'modelo',
                                'data', 'combustivel', 'litros', 'total',
                                'km_anterior', 'km_atual', 'km_rodados',
                                'rendimento', 'alertas'
                            ]].copy()
                            disp.columns = [
                                'Localizado por', 'Frota', 'Placa', 'Modelo',
                                'Data', 'Combustível', 'Litros', 'Total R$',
                                'Km Ant.', 'Km Atual', 'Km Rodados', 'km/L', 'Status'
                            ]

                            def _style_row(row):
                                if row['Status'] != '✅ OK':
                                    return ['background-color: #fff3cd'] * len(row)
                                if row['Localizado por'] == '❓ Não encontrado':
                                    return ['background-color: #f8d7da'] * len(row)
                                return [''] * len(row)

                            st.dataframe(
                                disp.style.apply(_style_row, axis=1),
                                use_container_width=True, hide_index=True
                            )

                            # ── Reconciliação manual ──────────────────────
                            nao_encontrados = preview_df[
                                preview_df['veiculo_id'].isna()
                            ].copy()

                            if not nao_encontrados.empty:
                                with st.expander(
                                    f"⚠️ {len(nao_encontrados)} registro(s) com "
                                    "veículo NÃO CADASTRADO — clique para reconciliar",
                                    expanded=False
                                ):
                                    st.caption(
                                        "Vincule manualmente o registro ao veículo "
                                        "correspondente no sistema."
                                    )
                                    uniq = (
                                        nao_encontrados[
                                            ['identificacao', 'frota', 'comb_norm']
                                        ]
                                        .drop_duplicates()
                                        .reset_index(drop=True)
                                    )
                                    all_v_opts = {
                                        f"{r['placa']} — {r['modelo']} "
                                        f"(Frota: {r.get('numero_frota','—') or '—'})": r['id']
                                        for _, r in vehicles_df.iterrows()
                                    }
                                    opts_list = [
                                        '(Ignorar / Não vincular)'
                                    ] + list(all_v_opts.keys())

                                    if 'reconciliacao' not in st.session_state:
                                        st.session_state['reconciliacao'] = {}

                                    for idx, urow in uniq.iterrows():
                                        key = f"rec_{urow['identificacao']}_{urow['frota']}"
                                        st.write(
                                            f"**ID:** `{urow['identificacao']}` | "
                                            f"**Frota:** `{urow['frota']}` | "
                                            f"**Combustível:** `{urow['comb_norm']}`"
                                        )
                                        sel = st.selectbox(
                                            "Vincular a qual veículo?",
                                            opts_list, key=key
                                        )
                                        if sel != '(Ignorar / Não vincular)':
                                            st.session_state['reconciliacao'][key] = {
                                                'identificacao': urow['identificacao'],
                                                'frota':         urow['frota'],
                                                'veiculo_id':    all_v_opts[sel],
                                            }
                                        st.divider()

                                    if st.button("✅ Aplicar Vínculos"):
                                        for key, link in st.session_state.get(
                                            'reconciliacao', {}
                                        ).items():
                                            mask = (
                                                (preview_df['identificacao'] ==
                                                 link['identificacao']) &
                                                (preview_df['frota'] == link['frota'])
                                            )
                                            preview_df.loc[mask, 'veiculo_id'] = \
                                                link['veiculo_id']
                                            preview_df.loc[mask, 'sincronizar_frota'] = True
                                            preview_df.loc[mask, 'alertas'] = \
                                                '✅ OK (vinculado)'
                                        st.session_state['preview_df_reconciled'] = \
                                            preview_df
                                        st.success("Vínculos aplicados!")
                                        st.rerun()

                            # ── Opções e importação ───────────────────────
                            st.divider()
                            col_btn, col_opts = st.columns([1, 2])
                            with col_opts:
                                import_invalid = st.checkbox(
                                    "Importar registros com alertas também",
                                    value=True
                                )
                                sync_frota_opt = st.checkbox(
                                    "Vincular Nº de Frota ao cadastro do veículo",
                                    value=True
                                )

                            with col_btn:
                                if st.button(
                                    "🔄 Confirmar Importação",
                                    type="primary",
                                    use_container_width=True
                                ):
                                    rows_import = (
                                        preview_df if import_invalid
                                        else preview_df[
                                            preview_df['alertas'].str.startswith('✅')
                                        ]
                                    )

                                    success_count = error_count = frota_sync = 0
                                    prog = st.progress(0)
                                    info = st.empty()
                                    veh_fresh = db_handler.get_vehicles()

                                    for i, (_, rec) in enumerate(
                                        rows_import.iterrows()
                                    ):
                                        ok, _ = db_handler.add_abastecimento(
                                            veiculo_id       = rec['veiculo_id'],
                                            identificacao    = rec['identificacao'],
                                            numero_frota     = rec['frota'],
                                            data             = rec['data'],
                                            tipo_combustivel = rec['comb_norm'],
                                            volume_litros    = rec['litros'],
                                            preco_litro      = rec['preco'],
                                            valor_total      = rec['total'],
                                            km_anterior      = rec['km_anterior'],
                                            km_atual_bomba   = rec['km_atual'],
                                            lote_importacao  = rec['lote'],
                                        )
                                        if ok:
                                            success_count += 1
                                            if (sync_frota_opt
                                                    and rec.get('sincronizar_frota')
                                                    and rec['veiculo_id']
                                                    and rec['frota']):
                                                if _sync_frota_number(
                                                    int(rec['veiculo_id']),
                                                    rec['frota'], veh_fresh
                                                ):
                                                    frota_sync += 1
                                        else:
                                            error_count += 1

                                        prog.progress((i + 1) / len(rows_import))
                                        info.text(
                                            f"Processando {i+1}/{len(rows_import)}…"
                                        )

                                    prog.empty()
                                    info.empty()
                                    st.session_state.pop(
                                        'preview_df_reconciled', None
                                    )
                                    st.session_state.pop('reconciliacao', None)

                                    st.success(
                                        f"✅ **{success_count}** registros importados!"
                                    )
                                    if frota_sync:
                                        st.info(
                                            f"🔄 **{frota_sync}** veículo(s) com "
                                            "Nº de Frota atualizado."
                                        )
                                    if error_count:
                                        st.error(
                                            f"❌ {error_count} registros com erro."
                                        )
                                    if success_count > 0:
                                        st.balloons()

            except Exception as e:
                import traceback
                st.error(f"Erro ao processar arquivo: {e}")
                st.code(traceback.format_exc())

    # ═══════════════════════════════════════════════════════════════════════
    # TAB 2 — Análise por Veículo
    # ═══════════════════════════════════════════════════════════════════════
    with tab2:
        st.subheader("Análise por Veículo")
        vehicles_df2 = db_handler.get_vehicles()

        if vehicles_df2.empty:
            st.info("Nenhum veículo cadastrado.")
        else:
            all_fuel = db_handler.get_abastecimentos()

            if all_fuel.empty:
                st.info(
                    "Nenhum abastecimento importado ainda. "
                    "Use a aba '📥 Importar Planilha'."
                )
            else:
                ids_com_dados = set(
                    all_fuel['veiculo_id'].dropna().astype(int).tolist()
                )
                veh_com = vehicles_df2[vehicles_df2['id'].isin(ids_com_dados)]

                def _veh_label(row):
                    frota = str(row.get('numero_frota', '') or '').strip()
                    return (
                        f"Frota {frota} — {row['placa']} — {row['modelo']}"
                        if frota and frota != 'nan'
                        else f"{row['placa']} — {row['modelo']}"
                    )

                options = {_veh_label(r): r['id'] for _, r in veh_com.iterrows()}

                if not options:
                    st.info("Nenhum veículo com dados de abastecimento.")
                else:
                    busca = st.text_input(
                        "🔍 Buscar por Placa, Frota ou Modelo", ""
                    ).strip()
                    if busca:
                        options = {
                            k: v for k, v in options.items()
                            if busca.lower() in k.lower()
                        }

                    if not options:
                        st.warning("Nenhum veículo para a busca informada.")
                    else:
                        sel_label = st.selectbox(
                            "Selecione o Veículo", list(options.keys())
                        )
                        sel_id = options[sel_label]
                        vdf    = db_handler.get_abastecimentos(veiculo_id=sel_id)

                        if vdf.empty:
                            st.info(
                                "Nenhum abastecimento registrado para este veículo."
                            )
                        else:
                            v_data   = db_handler.get_vehicle_by_id(sel_id)
                            comb_key = (
                                (v_data or {}).get('tipo_combustivel', 'flex')
                                or 'flex'
                            )
                            ref   = RENDIMENTO_REF.get(comb_key,
                                                       RENDIMENTO_REF['flex'])
                            valid = vdf[
                                vdf['rendimento_kml'].notna()
                                & (vdf['rendimento_kml'] > 0)
                            ]

                            frota_info = (v_data or {}).get('numero_frota', '') or ''
                            st.markdown(
                                f"#### 🚗 {v_data['modelo']} — Placa "
                                f"`{v_data['placa']}`"
                                + (f" | Frota `{frota_info}`" if frota_info else "")
                            )

                            c1, c2, c3, c4 = st.columns(4)
                            c1.metric("Abastecimentos", len(vdf))
                            c2.metric("Total Litros",
                                      f"{vdf['volume_litros'].sum():,.1f} L")
                            c3.metric("Gasto Total",
                                      f"R$ {vdf['valor_total'].sum():,.2f}")
                            med_rend = (
                                valid['rendimento_kml'].mean()
                                if not valid.empty else 0
                            )
                            c4.metric(
                                "Média km/L", f"{med_rend:.2f}",
                                f"{med_rend - ref['esperado']:+.1f} vs ref."
                            )

                            if not valid.empty:
                                if med_rend < ref['alerta']:
                                    st.error(
                                        f"🔴 Rendimento CRÍTICO! "
                                        f"Média {med_rend:.2f} km/L "
                                        f"(alerta: {ref['alerta']} km/L)"
                                    )
                                elif med_rend < ref['esperado']:
                                    st.warning(
                                        f"🟡 Abaixo do esperado "
                                        f"({ref['esperado']} km/L para "
                                        f"{ref['label']})"
                                    )
                                else:
                                    st.success(
                                        f"🟢 Rendimento OK para {ref['label']}"
                                    )

                            st.markdown("#### Histórico de Abastecimentos")
                            hist = vdf[[
                                'data', 'tipo_combustivel', 'volume_litros',
                                'valor_total', 'km_anterior', 'km_atual',
                                'km_rodados', 'rendimento_kml'
                            ]].copy()
                            hist.columns = [
                                'Data', 'Combustível', 'Litros', 'Total R$',
                                'Km Ant.', 'Km Atual', 'Km Rodados', 'km/L'
                            ]
                            st.dataframe(
                                hist, use_container_width=True, hide_index=True
                            )

    # ═══════════════════════════════════════════════════════════════════════
    # TAB 3 — Painel da Frota
    # ═══════════════════════════════════════════════════════════════════════
    with tab3:
        st.subheader("🏭 Painel Geral da Frota")
        summary_df = db_handler.get_fleet_fuel_summary()

        if summary_df.empty:
            st.info(
                "Nenhum dado disponível. "
                "Importe uma planilha na aba '📥 Importar Planilha'."
            )
        else:
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Veículos com Dados",
                      len(summary_df))
            c2.metric("Total Litros",
                      f"{summary_df['total_litros'].sum():,.0f} L")
            c3.metric("Gasto Total",
                      f"R$ {summary_df['total_gasto'].sum():,.2f}")
            c4.metric("Total KM Rodados",
                      f"{summary_df['total_km_rodados'].sum():,.0f} km")

            st.divider()
            filtro = st.text_input(
                "🔍 Filtrar por Placa, Frota ou Modelo", ""
            ).strip().lower()

            st.markdown("#### 📋 Tabela Comparativa (ordenada por Nº de Frota)")

            rows_display = []
            for _, r in summary_df.iterrows():
                ck = str(r.get('combustivel', 'flex') or 'flex').lower()
                if 's10' in ck:     ck = 'diesel_s10'
                elif 'diesel' in ck:  ck = 'diesel_s10'
                elif 'gasolina' in ck: ck = 'gasolina'
                ref = RENDIMENTO_REF.get(ck, RENDIMENTO_REF['flex'])
                med = r['media_rendimento']

                if pd.isna(med) or med == 0:  status = '⚪ Sem dados'
                elif med < ref['alerta']:      status = '🔴 Crítico'
                elif med < ref['esperado']:    status = '🟡 Atenção'
                else:                         status = '🟢 OK'

                frota_v  = str(r.get('frota',  '') or '—')
                placa_v  = str(r.get('placa',  '—'))
                modelo_v = str(r.get('modelo', '—'))

                if filtro and not any(
                    filtro in v.lower()
                    for v in [frota_v, placa_v, modelo_v]
                ):
                    continue

                rows_display.append({
                    'Frota':       frota_v,
                    'Placa':       placa_v,
                    'Modelo':      modelo_v,
                    'Combustível': str(r.get('combustivel', '—')),
                    'Abastec.':    int(r.get('total_abastecimentos', 0) or 0),
                    'Total L':     (f"{r['total_litros']:,.1f}"
                                   if pd.notna(r['total_litros']) else '—'),
                    'Gasto R$':    (f"{r['total_gasto']:,.2f}"
                                   if pd.notna(r['total_gasto']) else '—'),
                    'KM Rodados':  (f"{r['total_km_rodados']:,.0f}"
                                   if pd.notna(r['total_km_rodados']) else '—'),
                    'Média km/L':  (f"{med:.2f}" if pd.notna(med) else '—'),
                    'Status':      status,
                })

            if rows_display:
                disp_df = pd.DataFrame(rows_display)
                try:
                    disp_df['_n'] = pd.to_numeric(
                        disp_df['Frota'], errors='coerce'
                    )
                    disp_df = disp_df.sort_values('_n').drop(columns='_n')
                except Exception:
                    pass
                st.dataframe(
                    disp_df, use_container_width=True, hide_index=True
                )
            else:
                st.info("Nenhum registro para o filtro informado.")

            st.divider()
            col_best, col_worst = st.columns(2)
            v_sum = summary_df.dropna(subset=['media_rendimento'])
            v_sum = v_sum[v_sum['media_rendimento'] > 0]

            with col_best:
                st.markdown("#### 🏆 Mais Eficientes (km/L)")
                if not v_sum.empty:
                    top = v_sum.nlargest(5, 'media_rendimento')[
                        ['frota', 'placa', 'modelo', 'media_rendimento']
                    ].copy()
                    top.columns = ['Frota', 'Placa', 'Modelo', 'km/L']
                    top['km/L'] = top['km/L'].apply(lambda x: f"{x:.2f}")
                    st.dataframe(top, use_container_width=True, hide_index=True)

            with col_worst:
                st.markdown("#### ⚠️ Menos Eficientes (km/L)")
                if not v_sum.empty:
                    bot = v_sum.nsmallest(5, 'media_rendimento')[
                        ['frota', 'placa', 'modelo', 'media_rendimento']
                    ].copy()
                    bot.columns = ['Frota', 'Placa', 'Modelo', 'km/L']
                    bot['km/L'] = bot['km/L'].apply(lambda x: f"{x:.2f}")
                    st.dataframe(bot, use_container_width=True, hide_index=True)
