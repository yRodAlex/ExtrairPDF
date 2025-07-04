import streamlit as st
import pdfplumber
import pandas as pd
import re
from io import BytesIO
from openpyxl import Workbook

st.set_page_config(page_title="Gestão Completa de Faturas e DRE", layout="wide")

st.title("💼 Faturas e Análises de DRE")

menu = st.sidebar.radio("Menu", ["📁 Converter Fatura PDF → DRE", "📊 Analisar DRE Consolidado"])

# ---------------- Função Final, Robusta e Corrigida -----------------

def extrair_lancamentos_itau_preciso(pdf_path):
    datas, estabelecimentos, valores, cartoes = [], [], [], []
    
    with pdfplumber.open(pdf_path) as pdf:
        cartao_atual = None
        buffer_linha = ""

        for pagina in pdf.pages:
            texto = pagina.extract_text()
            if not texto:
                continue

            linhas = texto.split('\n')
            for linha in linhas:
                # Detecta o cartão atual
                if re.search(r'\(final \d{4}\)', linha):
                    cartao_atual = re.search(r'\(final (\d{4})\)', linha).group(1)

                linha = linha.strip()

                # Se for linha de lançamento (data, descrição e valor)
                match = re.search(r'(\d{2}/\d{2})\s+(.*?)\s+(-?\d{1,3}(?:\.\d{3})*,\d{2})$', linha)
                if match and cartao_atual:
                    data = match.group(1)
                    descricao = match.group(2).strip()
                    valor_str = match.group(3).replace('.', '').replace(',', '.')

                    try:
                        valor = float(valor_str)
                        datas.append(data)
                        estabelecimentos.append(descricao)
                        valores.append(valor)
                        cartoes.append(cartao_atual)
                    except:
                        continue
                else:
                    # Se a linha não bate, acumula no buffer e tenta juntar na próxima
                    buffer_linha += " " + linha.strip()

                    # Tenta extrair juntando buffer
                    match2 = re.search(r'(\d{2}/\d{2})\s+(.*?)\s+(-?\d{1,3}(?:\.\d{3})*,\d{2})$', buffer_linha)
                    if match2 and cartao_atual:
                        data = match2.group(1)
                        descricao = match2.group(2).strip()
                        valor_str = match2.group(3).replace('.', '').replace(',', '.')

                        try:
                            valor = float(valor_str)
                            datas.append(data)
                            estabelecimentos.append(descricao)
                            valores.append(valor)
                            cartoes.append(cartao_atual)
                            buffer_linha = ""
                        except:
                            continue

    return datas, estabelecimentos, valores, cartoes

# ---------------- Aba de Transformação PDF → DRE -----------------

if menu == "📁 Converter Fatura PDF → DRE":
    st.header("Conversão de Fatura para DRE (Excel)")

    banco = st.selectbox("Selecione o Banco:", ["itau", "sicoob"])
    mes = st.text_input("Mês da fatura (número ou nome, ex: 06 ou Junho):")
    ano = st.text_input("Ano da fatura (ex: 2025):")
    uploaded_file = st.file_uploader("Envie o PDF da fatura:", type=["pdf"])

    if uploaded_file and mes and ano:
        datas, estabelecimentos, valores, cartoes = [], [], [], []

        if banco == "itau":
            caminho_temp = "temp_fatura.pdf"
            with open(caminho_temp, "wb") as f:
                f.write(uploaded_file.read())
            
            datas, estabelecimentos, valores, cartoes = extrair_lancamentos_itau_preciso(caminho_temp)

        if datas:
            st.success(f"Total de Lançamentos extraídos: {len(datas)}")

            total_por_cartao = pd.DataFrame({
                "Cartão": cartoes,
                "Valor (R$)": valores
            }).groupby("Cartão").sum().reset_index()

            for _, row in total_por_cartao.iterrows():
                st.info(f"Cartão final {row['Cartão']}: Total de R$ {row['Valor (R$)']:.2f}")

            df_resultado = pd.DataFrame({
                "Cartão": cartoes,
                "Data": datas,
                "Estabelecimento": estabelecimentos,
                "Valor (R$)": valores
            })
            st.dataframe(df_resultado)

            output = BytesIO()
            wb = Workbook()
            nome_aba = f'{banco}-{mes}{ano}'
            ws = wb.active
            ws.title = nome_aba

            ws['A1'] = f'Fatura do mês {mes}, ano {ano}, Banco {banco.upper()}'
            ws.append([])
            ws.append([])
            ws.append(['Cartão', 'Data', 'Estabelecimento', 'Valor (R$)', 'Código Conta', 'Descrição Conta'])

            for i in range(len(datas)):
                linha_excel = i + 5
                ws.append([
                    cartoes[i],
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

            st.download_button(
                label="📥 Baixar Excel DRE Gerado",
                data=output,
                file_name=f'DRE_{banco}_{mes}_{ano}.xlsx',
                mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
        else:
            st.warning("Nenhum lançamento encontrado. Verifique o PDF.")
