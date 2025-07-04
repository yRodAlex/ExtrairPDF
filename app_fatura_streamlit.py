import streamlit as st
import pdfplumber
import pandas as pd
import re
from io import BytesIO
from openpyxl import Workbook
from PIL import Image
import pytesseract

st.set_page_config(page_title="Gestão Completa de Faturas e DRE", layout="wide")

st.title("💼 Faturas e Análises de DRE")

menu = st.sidebar.radio("Menu", ["📁 Converter Fatura PDF → DRE", "📊 Analisar DRE Consolidado"])


# ---------------- Função Final com OCR por Área -----------------

def extrair_lancamentos_itau_ocr_area(pdf_path):
    datas, estabelecimentos, valores, cartoes = [], [], [], []

    with pdfplumber.open(pdf_path) as pdf:
        cartao_atual = None

        for pagina in pdf.pages:
            imagem = pagina.to_image(resolution=300)
            
            # Corta parte do cabeçalho e foca na região dos lançamentos (ajustável conforme layout)
            cropped = imagem.crop((0, 150, imagem.width, imagem.height))
            
            pil_img = cropped.original.convert("RGB")
            texto = pytesseract.image_to_string(pil_img, lang="por")

            linhas = texto.split('\n')
            buffer_descricao = ""
            data_atual = None

            for linha in linhas:
                linha = linha.strip()

                # Detecta o cartão
                if re.search(r'final \d{4}', linha, re.IGNORECASE):
                    cartao_atual = re.search(r'final (\d{4})', linha, re.IGNORECASE).group(1)

                if not cartao_atual:
                    continue

                # Detecta início de lançamento com data
                match_data = re.match(r'(\d{2}/\d{2})\s+(.*)', linha)
                if match_data:
                    if data_atual and buffer_descricao:
                        match_valor = re.search(r'(-?\d{1,3}(?:\.\d{3})*,\d{2})', buffer_descricao)
                        if match_valor:
                            valor_str = match_valor.group(1).replace('.', '').replace(',', '.')
                            try:
                                valor = float(valor_str)
                                descricao_limpa = re.sub(r'(-?\d{1,3}(?:\.\d{3})*,\d{2})', '', buffer_descricao).strip()
                                datas.append(data_atual)
                                estabelecimentos.append(descricao_limpa)
                                valores.append(valor)
                                cartoes.append(cartao_atual)
                            except:
                                pass

                    data_atual = match_data.group(1)
                    buffer_descricao = match_data.group(2).strip()

                else:
                    buffer_descricao += " " + linha.strip()

            # Finaliza o último lançamento da página
            if data_atual and buffer_descricao:
                match_valor = re.search(r'(-?\d{1,3}(?:\.\d{3})*,\d{2})', buffer_descricao)
                if match_valor:
                    valor_str = match_valor.group(1).replace('.', '').replace(',', '.')
                    try:
                        valor = float(valor_str)
                        descricao_limpa = re.sub(r'(-?\d{1,3}(?:\.\d{3})*,\d{2})', '', buffer_descricao).strip()
                        datas.append(data_atual)
                        estabelecimentos.append(descricao_limpa)
                        valores.append(valor)
                        cartoes.append(cartao_atual)
                    except:
                        pass

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

            datas, estabelecimentos, valores, cartoes = extrair_lancamentos_itau_ocr_area(caminho_temp)

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
