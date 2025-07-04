import streamlit as st
import pdfplumber
import pandas as pd
import re
from io import BytesIO
from openpyxl import Workbook

st.set_page_config(page_title="Gestão Completa de Faturas e DRE", layout="wide")

st.title("💼 Faturas e Análises de DRE")

menu = st.sidebar.radio("Menu", ["📁 Converter Fatura PDF → DRE", "📊 Analisar DRE Consolidado"])

# ---------------- Função Melhorada com Coordenadas Itaú -----------------

def extrair_lancamentos_itau_por_cartao(pdf_path):
    datas, estabelecimentos, valores, cartoes = [], [], [], []
    
    with pdfplumber.open(pdf_path) as pdf:
        for pagina in pdf.pages:
            palavras = pagina.extract_words(use_text_flow=True, keep_blank_chars=False)

            cartao_atual = None
            for i, palavra in enumerate(palavras):
                # Detecta o número do cartão
                if re.search(r'\(final \d{4}\)', palavra['text']):
                    cartao_atual = re.search(r'\(final (\d{4})\)', palavra['text']).group(1)
                
                # Detecta padrão de lançamento
                if re.match(r'\d{2}/\d{2}', palavra['text']):
                    if cartao_atual is None:
                        continue  # Ignora se cartão não foi detectado ainda

                    try:
                        data = palavras[i]['text']
                        estabelecimento = palavras[i + 1]['text']
                        
                        valor_texto = palavras[i + 2]['text'].replace('.', '').replace(',', '.')
                        valor = float(valor_texto)
                        
                        datas.append(data)
                        estabelecimentos.append(estabelecimento)
                        valores.append(valor)
                        cartoes.append(cartao_atual)
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
            
            datas, estabelecimentos, valores, cartoes = extrair_lancamentos_itau_por_cartao(caminho_temp)

        if datas:
            st.success(f"Total de Lançamentos extraídos: {len(datas)}")

            cartoes_validos = [c for c in cartoes if c is not None]
            if cartoes_validos:
                st.info(f"Cartões encontrados: {', '.join(sorted(set(cartoes_validos)))}")
            else:
                st.warning("Nenhum número de cartão identificado nos lançamentos.")

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
