import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Análise de DRE", layout="wide")

st.title("📊 Análise Completa de DRE")

st.write("Importe seu arquivo de DRE (.xlsx ou .xlsm) para visualizar as análises:")

arquivo = st.file_uploader("Selecionar Arquivo DRE", type=["xlsx", "xlsm"])

if arquivo:
    try:
        df = pd.read_excel(arquivo, sheet_name=None)
        abas_validas = [aba for aba in df.keys() if aba.startswith("itau-") or aba.startswith("sicoob-")]

        if abas_validas:
            todas_entradas = []
            for aba in abas_validas:
                dados = df[aba]
                dados = dados.dropna(how="all")
                if not dados.empty and "Data" in dados.columns and "Estabelecimento" in dados.columns and "Valor (R$)" in dados.columns:
                    dados["Mês/Ano"] = aba.split("-")[1] if "-" in aba else ""
                    todas_entradas.append(dados)

            if todas_entradas:
                consolidado = pd.concat(todas_entradas, ignore_index=True)

                st.success(f"{len(consolidado)} lançamentos carregados.")

                st.header("📄 Visualização Completa do DRE")
                st.dataframe(consolidado)

                st.header("🎯 Metas e Comparações por Categoria")
                categorias = st.multiselect("Escolha as categorias para definir metas (coluna 'Descrição Conta'):", consolidado["Descrição Conta"].dropna().unique())

                metas = {}
                for cat in categorias:
                    meta = st.number_input(f"Meta de gasto para '{cat}' (R$):", min_value=0.0, step=50.0)
                    metas[cat] = meta

                resumo = consolidado.groupby("Descrição Conta")["Valor (R$)"].sum().reset_index()
                resumo = resumo[resumo["Descrição Conta"].notna()]

                for _, row in resumo.iterrows():
                    desc = row["Descrição Conta"]
                    total = row["Valor (R$)"]
                    st.write(f"**{desc}:** R$ {total:.2f}")
                    if desc in metas:
                        if total > metas[desc]:
                            st.error(f"Ultrapassou a meta de {metas[desc]:.2f} em R$ {total - metas[desc]:.2f}")
                        else:
                            st.success(f"Dentro da meta de {metas[desc]:.2f} R$")

                st.header("📈 Gráfico de Gastos por Categoria")
                fig = px.pie(resumo, names="Descrição Conta", values="Valor (R$)", title="Distribuição dos Gastos")
                st.plotly_chart(fig)

                st.header("🔮 Evolução Mensal dos Gastos")
                gasto_mensal = consolidado.groupby("Mês/Ano")["Valor (R$)"].sum().reset_index()
                st.line_chart(gasto_mensal.set_index("Mês/Ano"))

                media_gasto = gasto_mensal["Valor (R$)"].mean()
                st.info(f"Gasto médio mensal atual: R$ {media_gasto:.2f}")

                economia = st.number_input("Quanto pretende economizar por mês (R$):", min_value=0.0, step=50.0)
                previsao_final_ano = 12 * (media_gasto - economia)

                st.success(f"Se atingir essa economia, previsão de gasto anual: R$ {previsao_final_ano:.2f}")

        else:
            st.warning("O arquivo não contém abas válidas com padrão 'itau-' ou 'sicoob-'.")

    except Exception as e:
        st.error(f"Erro ao processar o arquivo: {e}")
