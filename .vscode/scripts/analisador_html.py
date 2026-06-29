import os
import glob
import re
import pandas as pd
import numpy as np

# Configurações
DIRETORIO_HTML = './' 
ARQUIVO_SAIDA = 'consolidado_testes_variacao_uwb_250_leituras.csv'

def extrair_dados_do_html(caminho_arquivo):
    with open(caminho_arquivo, 'r', encoding='utf-8', errors='ignore') as f:
        conteudo = f.read()

    dados = {
        'bruta': [],
        'kalman': [],
        'ma10': [],
        'ma30': [],
        'per_medio': 0.0
    }

    # 1. Extrai TODOS os "PER Médio" de todas as capturas do arquivo
    matches_per = re.findall(r'PER Médio:\s*([\d.]+)\s*%', conteudo)
    if matches_per:
        # Tira a média de todas as 5 janelas de captura para o PER global do arquivo
        valores_per = [float(v) for v in matches_per]
        dados['per_medio'] = sum(valores_per) / len(valores_per)

    # 2. Extrai os arrays de TODAS as instâncias do Chart.js no arquivo
    mapeamento_graficos = [
        ('bruta', r"label:\s*'Raw Data',\s*data:\s*\[(.*?)\]"),
        ('kalman', r"label:\s*'Kalman Filter',\s*data:\s*\[(.*?)\]"),
        ('ma30', r"label:\s*'Média Móvel \(30\)',\s*data:\s*\[(.*?)\]"),
        ('ma10', r"label:\s*'Média Móvel \(10\)',\s*data:\s*\[(.*?)\]")
    ]

    for chave, padrao in mapeamento_graficos:
        # findall acha todas as 5 listas de dados no HTML
        matches = re.findall(padrao, conteudo, re.IGNORECASE | re.DOTALL)
        
        for match in matches:
            numeros_str = match.replace('\n', '').split(',')
            for n in numeros_str:
                n_limpo = n.strip().replace('"', '').replace("'", "")
                # Ignora valores vazios ou pacotes perdidos ('null')
                if n_limpo and n_limpo.lower() != 'null':
                    try:
                        dados[chave].append(float(n_limpo))
                    except ValueError:
                        pass

    return dados

def calcular_metricas(nome_arquivo, dados):
    metricas = {'Cenário (Arquivo)': nome_arquivo}
    
    metricas['PER_Médio (%)'] = round(dados['per_medio'], 2)
    metricas['Total de Leituras'] = len(dados['kalman']) # Para confirmar se pegou as 250!

    filtros = ['bruta', 'kalman', 'ma10', 'ma30']
    nomes_bonitos = ['Dist. Bruta', 'Kalman 2D', 'Média 10', 'Média 30']

    for chave, nome in zip(filtros, nomes_bonitos):
        array = dados.get(chave, [])
        if array:
            metricas[f'{nome} - Média'] = round(np.mean(array), 2)
            metricas[f'{nome} - Desvio Padrão (Ruído)'] = round(np.std(array, ddof=1) if len(array) > 1 else 0, 2)
            metricas[f'{nome} - Range (Max-Min)'] = round(np.max(array) - np.min(array), 2)
        else:
            metricas[f'{nome} - Média'] = None
            metricas[f'{nome} - Desvio Padrão (Ruído)'] = None
            metricas[f'{nome} - Range (Max-Min)'] = None

    return metricas

def main():
    arquivos_html = glob.glob(os.path.join(DIRETORIO_HTML, '*.html'))
    
    if not arquivos_html:
        print("❌ Nenhum arquivo HTML encontrado na pasta.")
        return

    print(f"🔄 Iniciando análise COMPLETA de {len(arquivos_html)} relatórios HTML...")
    
    resultados_consolidados = []

    for arquivo in arquivos_html:
        nome_base = os.path.basename(arquivo)
        dados_brutos = extrair_dados_do_html(arquivo)
        
        if dados_brutos['kalman'] or dados_brutos['bruta']:
            metricas = calcular_metricas(nome_base, dados_brutos)
            resultados_consolidados.append(metricas)
        else:
            print(f"⚠️ Aviso: Dados não encontrados em '{nome_base}'.")

    if resultados_consolidados:
        df = pd.DataFrame(resultados_consolidados)
        df.sort_values(by='Cenário (Arquivo)', inplace=True) 
        df.to_csv(ARQUIVO_SAIDA, index=False, sep=';', decimal=',', encoding='utf-8-sig')
        print(f"\n✅ Concluído! Planilha gerada: {ARQUIVO_SAIDA}")
    else:
        print("\n❌ Nenhum dado válido foi extraído.")

if __name__ == '__main__':
    main()