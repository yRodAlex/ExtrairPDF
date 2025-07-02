
import streamlit as st
import pandas as pd
import os
import plotly.express as px
from io import BytesIO

st.set_page_config(page_title="Gestão Financeira Completa - DRE", layout="wide")

st.title("💸 Painel de Lançamentos, DRE, Metas e Previsões")

# Login simples por usuário
usuario = st.text_input("Digite seu nome de usuário:")

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
