import streamlit as st
import pdfplumber
import pandas as pd
import re
import plotly.express as px
from io import BytesIO
from openpyxl import Workbook
from PIL import Image
import pytesseract

st.set_page_config(page_title="Gestão Completa de Faturas e DRE", layout="wide")

st.title("💼 Faturas e Análises de DRE")

menu = st.sidebar.radio("Menu", ["📁 Converter Fatura PDF → DRE", "📊 Analisar DRE Consolidado"])


# ---------------- Função com OCR -----------------

def extrair_lancamentos_itau_ocr(pdf_path):
    datas, estabelecimentos, cidades, valores = [], [], [], []

    with pdfplumber.open(pdf_path) as pdf:
        for pagina in pdf.pages:
            texto = pagina.extract_text()

            # Se não extrair texto estruturado, tenta OCR
            if not texto or len(texto.strip()) < 10:
                imagem = pagina.to_image(resolution=300)
                pil_image = Image.frombytes("RGB", imagem.original.size, imagem.original.convert("RGB").tobytes())
                texto = pytesseract.image_to_string(pil_image, lang='por')

            linhas = texto.split('\n')
            regex_linha = re.compile(r'(\d{2}/\d{2})\s+(.*?)\s+(-?\d{1,3}(?:\.\d{3})*,\d{2})')

            for linha in linhas:
                linha = linha.strip()
                match = regex_linha.search(linha)
                if match:
                    data = match.group(1)
                    descricao = match.group(2).strip()
                    valor_str = match.group(3).replace('.', '').replace(',', '.')

                    try:
                        valor = float(valor_str)
                    except:
                        continue

                    datas.append(data)
                    estabelecimentos.append(descricao)
                    cidades.append("")
                    valores.append(valor)

    return datas, estabelecimentos, cidades, valores


# ---------------- Aba de Transformação PDF → DRE -----------------

if menu == "📁 Converter Fatura PDF → DRE":
    st.header("Conversão de Fatura para DRE (Excel)")

    banco = st.selectbox("Selecione o Banco:", ["itau", "sicoob"])
    mes = st.text_input("Mês da fatura (número ou nome, ex: 06 ou Junho):")
    ano = st.text_input("Ano da fatura (ex: 2025):")
    uploaded_file = st.file_uploader("Envie o PDF da fatura:", type=["pdf"])

    if uploaded_file and mes and ano:
        datas, estabelecimentos, cidades, valores = [], [], [], []

        if banco == "itau":
            caminho_temp = "temp_fatura.pdf"
            with open(caminho_temp, "wb") as f:
                f.write(uploaded_file.read())

            datas, estabelecimentos, cidades, valores = extrair_lancamentos_itau_ocr(caminho_temp)

        elif banco == "sicoob":
            with pdfplumber.open(uploaded_file) as pdf:
                lendo = False
                meses_dict = {'JAN':'01','FEV':'02','MAR':'03','ABR':'04','MAI':'05','JUN':'06',
                              'JUL':'07','AGO':'08','SET':'09','OUT':'10','NOV':'11','DEZ':'12'}

                for pagina in pdf.pages:
                    texto = pagina.extract_text()
                    if texto:
                        linhas = texto.split('\n')

                        for linha in linhas:
                            if "DATA" in linha and "DESCRIÇÃO" in linha and "VALOR" in linha:
                                lendo = True
                                continue

                            if lendo:
                                if "TOTAL" in linha:
                                    break

                                partes = linha.strip().split()
                                if len(partes) < 5:
                                    continue

                                dia = partes[0]
                                mes_abrev = partes[1].upper()
                                mes_num = meses_dict.get(mes_abrev, "00")
                                data_formatada = f"{dia}/{mes_num}"

                                valor_bruto = partes[-1].replace('.', '').replace(',', '.').replace('R$', '')
                                try:
                                    valor_float = float(valor_bruto)
                                except:
                                    continue

                                cidade = partes[-2].replace("R$", "").strip()
                                descricao = " ".join(partes[2:-2])

                                datas.append(data_formatada)
                                estabelecimentos.append(descricao.strip())
                                cidades.append(cidade.strip())
                                valores.append(valor_float)

        if datas:
            st.success(f"Lançamentos extraídos: {len(datas)}")

            df_resultado = pd.DataFrame({
                "Data": datas,
                "Estabelecimento": estabelecimentos,
                "Cidade": cidades,
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
            ws.append(['Data', 'Estabelecimento', 'Cidade', 'Valor (R$)', 'Código Conta', 'Descrição Conta'])

            for i in range(len(datas)):
                linha_excel = i + 5
                ws.append([
                    datas[i],
                    estabelecimentos[i],
                    cidades[i],
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
            st.warning("Nenhum lançamento encontrado no PDF. Verifique o arquivo e tente novamente.")
