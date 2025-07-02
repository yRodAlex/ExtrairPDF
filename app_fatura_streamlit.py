
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

# Login simples
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
