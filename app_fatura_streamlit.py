
import streamlit as st
import pdfplumber
import pandas as pd
import re
import os
import plotly.express as px
from io import BytesIO
from openpyxl import Workbook

st.set_page_config(page_title="Gestão Completa de Faturas e DRE", layout="wide")

st.title("💼 Faturas e Análises de DRE")

usuario = st.text_input("Digite seu nome de usuário:")
if usuario:
    pasta_usuario = f"dados/{usuario}"
    os.makedirs(pasta_usuario, exist_ok=True)

    st.success(f"Bem-vindo, {usuario}!")

    menu = st.sidebar.radio("Menu", ["📁 Converter Fatura PDF → Excel", "📊 Analisar Arquivos DRE"])

    if menu == "📁 Converter Fatura PDF → Excel":
        st.header("Conversão de Fatura para Excel DRE")

        banco = st.selectbox("Selecione o Banco:", ["itau", "sicoob"])
        mes = st.text_input("Mês da fatura (número ou nome, ex: 06 ou Junho):")
        ano = st.text_input("Ano da fatura (ex: 2025):")
        uploaded_file = st.file_uploader("Envie o PDF da fatura:", type=["pdf"])

        if uploaded_file and mes and ano:
            datas, estabelecimentos, valores = [], [], []
            with pdfplumber.open(uploaded_file) as pdf:
                for pagina in pdf.pages:
                    texto = pagina.extract_text()
                    if texto:
                        linhas = texto.split('\n')

                        if banco == "itau":
                            regex = re.compile(r'(\d{2}/\d{2})\s+(.+?)\s+(\d+\.\d{2}|\d+,\d{2})')
                            for linha in linhas:
                                match = regex.search(linha)
                                if match:
                                    datas.append(match.group(1))
                                    estabelecimentos.append(match.group(2).strip())
                                    valores.append(float(match.group(3).replace('.', '').replace(',', '.')))

                        elif banco == "sicoob":
                            lendo = False
                            meses_dict = {'JAN':'01','FEV':'02','MAR':'03','ABR':'04','MAI':'05','JUN':'06',
                                          'JUL':'07','AGO':'08','SET':'09','OUT':'10','NOV':'11','DEZ':'12'}
                            
                            for linha in linhas:
                                if "DATA" in linha and "DESCRIÇÃO" in linha and "VALOR" in linha:
                                    lendo = True
                                    continue

                                if lendo:
                                    if "TOTAL" in linha or "ALIMENTAÇÃO" in linha or "AUTOMÓVEIS" in linha:
                                        break

                                    partes = linha.strip().split()
                                    if len(partes) >= 5:
                                        dia = partes[0]
                                        mes_abrev = partes[1].upper()
                                        mes_num = meses_dict.get(mes_abrev, "00")
                                        data_formatada = f"{dia}/{mes_num}"

                                        valor_bruto = partes[-1].replace('.', '').replace(',', '.').replace('R$', '')
                                        try:
                                            valor_float = float(valor_bruto)
                                        except:
                                            continue

                                        cidade = partes[-2]
                                        estabelecimento = " ".join(partes[2:-2])

                                        datas.append(data_formatada)
                                        estabelecimentos.append(estabelecimento.strip())
                                        valores.append(valor_float)

            if datas:
                output = BytesIO()
                wb = Workbook()
                nome_aba = f'{banco}-{mes}{ano}'
                ws = wb.active
                ws.title = nome_aba

                ws['A1'] = f'Fatura do mês {mes}, ano {ano}, Banco {banco.upper()}'
                ws.append([])
                ws.append([])
                ws.append(['Data', 'Estabelecimento', 'Valor (R$)', 'Código Conta', 'Descrição Conta'])

                for i in range(len(datas)):
                    linha_excel = i + 5
                    ws.append([
                        datas[i],
                        estabelecimentos[i],
                        valores[i],
                        '',
                        f'=VLOOKUP(D{linha_excel};\'Plano de Contas\'!A:B;2;FALSE)'
                    ])

                ws2 = wb.create_sheet('Plano de Contas')
                ws2.append(['Código Conta', 'Descrição Conta'])
                ws2.append([1, 'Gasto Geral'])
                ws2.append([2, 'Restaurantes'])
                ws2.append([3, 'Transporte'])
                ws2.append([4, 'Mercado'])

                wb.save(output)
                output.seek(0)

                nome_arquivo = f'Fatura_{banco}_{mes}_{ano}.xlsx'
                caminho_salvar = os.path.join(pasta_usuario, nome_arquivo)
                with open(caminho_salvar, "wb") as f:
                    f.write(output.getbuffer())

                st.success(f"Lançamentos extraídos: {len(datas)}")
                st.download_button(label="📥 Baixar Excel DRE Gerado",
                                   data=output,
                                   file_name=nome_arquivo,
                                   mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

    if usuario:
    pasta_usuario = f"dados/{usuario}"
    os.makedirs(pasta_usuario, exist_ok=True)

    st.success(f"Bem-vindo, {usuario}! Seus dados estão protegidos.")

    # Sessão de upload
    with st.expander("📁 Upload do DRE Preenchido"):
        arquivo = st.file_uploader("Envie o arquivo DRE (.xlsx ou .xlsm):", type=["xlsx", "xlsm"])
        if arquivo:
            caminho_arquivo = os.path.join(pasta_usuario, arquivo.name)
            with open(caminho_arquivo, "wb") as f:
                f.write(arquivo.getbuffer())
            st.success("Arquivo salvo com sucesso! Recarregue a página para atualizar as análises.")

    # Listagem dos arquivos
    arquivos_salvos = [f for f in os.listdir(pasta_usuario) if f.endswith((".xlsx", ".xlsm"))]
    
    if arquivos_salvos:
        st.sidebar.header("Arquivos Disponíveis")
        selecao = st.sidebar.selectbox("Selecione um arquivo para análise:", arquivos_salvos)

        caminho_selecionado = os.path.join(pasta_usuario, selecao)
        
        try:
            df = pd.read_excel(caminho_selecionado, sheet_name=None)
            abas_validas = [aba for aba in df.keys() if aba.startswith("itau-") or aba.startswith("sicoob-")]

            if abas_validas:
                st.sidebar.success(f"{len(abas_validas)} abas de lançamentos detectadas.")
                todas_entradas = []

                for aba in abas_validas:
                    dados = df[aba]
                    dados = dados.dropna(how="all")
                    if not dados.empty and "Data" in dados.columns and "Estabelecimento" in dados.columns and "Valor (R$)" in dados.columns:
                        dados["Mês/Ano"] = aba.split("-")[1] if "-" in aba else ""
                        todas_entradas.append(dados)

                if todas_entradas:
                    consolidado = pd.concat(todas_entradas, ignore_index=True)
                    st.header("📊 Lançamentos Consolidados")
                    st.dataframe(consolidado)

                    st.header("🎯 Metas e Comparações")
                    categorias = st.multiselect("Defina as categorias para controle (use a coluna 'Descrição Conta'):", consolidado["Descrição Conta"].dropna().unique())

                    metas = {}
                    for cat in categorias:
                        meta = st.number_input(f"Meta de gasto para '{cat}' (R$):", min_value=0.0, step=50.0)
                        metas[cat] = meta

                    st.subheader("Resumo por Categoria")
                    resumo = consolidado.groupby("Descrição Conta")["Valor (R$)"].sum().reset_index()
                    resumo = resumo[resumo["Descrição Conta"].notna()]

                    for idx, row in resumo.iterrows():
                        desc = row["Descrição Conta"]
                        total = row["Valor (R$)"]
                        st.write(f"**{desc}:** R$ {total:.2f}")
                        if desc in metas:
                            if total > metas[desc]:
                                st.error(f"Ultrapassou a meta de {metas[desc]:.2f} em {total - metas[desc]:.2f} R$")
                            else:
                                st.success(f"Dentro da meta de {metas[desc]:.2f} R$")

                    st.header("📈 Gráfico de Gastos por Categoria")
                    fig = px.pie(resumo, names="Descrição Conta", values="Valor (R$)", title="Distribuição dos Gastos")
                    st.plotly_chart(fig)

                    st.header("🔮 Previsão de Gastos Futuros")
                    gasto_mensal = consolidado.groupby("Mês/Ano")["Valor (R$)"].sum().reset_index()
                    st.line_chart(gasto_mensal.set_index("Mês/Ano"))

                    media_gasto = gasto_mensal["Valor (R$)"].mean()
                    st.info(f"Gasto médio mensal atual: R$ {media_gasto:.2f}")
                    economia = st.number_input("Quanto pretende economizar por mês (R$):", min_value=0.0, step=50.0)
                    previsao_final_ano = (12 * (media_gasto - economia))

                    st.success(f"Se manter essa economia, previsão de gasto no final do ano: R$ {previsao_final_ano:.2f}")

                else:
                    st.warning("Nenhum dado válido de lançamento encontrado nas abas.")
            else:
                st.warning("Nenhuma aba válida de lançamentos encontrada.")
        except Exception as e:
            st.error(f"Erro ao processar o arquivo: {e}")
