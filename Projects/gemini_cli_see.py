import google.generativeai as genai
import os
import sys

# --- CONFIGURAÇÃO ---
# Extensões de arquivos que o script deve ler
EXTENSOES_PERMITIDAS = {'.py', '.js', '.html', '.css', '.c', '.cpp', '.h', '.java', '.json', '.sql', '.md', '.txt', '.ts'}

# Configuração da API
API_KEY = "Sua Chave aqui"
# API_KEY = os.getenv('GEMINI_API_KEY')
if not API_KEY:
    print("Erro: Variável GEMINI_API_KEY não encontrada.")
    print("Dica: No Windows, configure com 'set GEMINI_API_KEY=sua_chave' ou nas Variáveis de Ambiente.")
    sys.exit(1)

genai.configure(api_key=API_KEY)

def ler_arquivos_projeto(diretorio_base):
    """
    Lê arquivos do projeto recursivamente com travas de segurança
    para evitar ler pastas gigantes (como venv ou node_modules).
    """
    conteudo_total = "CONTEXTO DO PROJETO (Arquivos carregados do meu PC):\n\n"
    arquivos_lidos = 0
    LIMITE_SEGURANCA = 30  # Se passar de 30 arquivos, ele para de ler (ajuste se precisar)
    
    # Lista de pastas proibidas (evita ler lixo ou bibliotecas externas)
    PASTAS_IGNORADAS_SET = {
        'venv', '.venv', 'env', '.env',                                 # Ambientes Python
        'node_modules',                                                 # Javascript
        '.git', '.github', '.gitlab',                                   # Git
        '__pycache__',                                                  # Cache
        '.vscode', '.idea',                                             # Configurações de IDE
        'build', 'dist', 'bin', 'obj',                                  # Arquivos compilados
        'migrations',                                                   # Opcional: Banco de dados
        'static', 'assets', 'media',                                    # Arquivos de imagem/som
        'buildoutput', 'debug', 'release', 'cmakefiles',                # C#/C++
        'uci', 'qani', 'helloworld',                                     # Exemplos de hardware
        'nrf52840dk', 'q-tag', 'type2ab_evb'
    }

    print(f"\n--- Escaneando pasta atual: {diretorio_base} ---")
    
    for root, dirs, files in os.walk(diretorio_base):
        # 1. Filtro de Pastas: Remove pastas proibidas da busca imediatamente
        dirs[:] = [d for d in dirs if d.lower() not in PASTAS_IGNORADAS_SET]
        
        # Mostra visualmente onde o script está entrando (Debug)
        pasta_atual = os.path.relpath(root, diretorio_base)
        if pasta_atual != ".":
            print(f"📂 Verificando pasta: \\{pasta_atual}")

        for file in files:
            # 2. Trava de Segurança por quantidade
            if arquivos_lidos >= LIMITE_SEGURANCA:
                print(f"\n⚠️ ALERTA: Limite de {LIMITE_SEGURANCA} arquivos atingido.")
                print("   Parando leitura para não sobrecarregar o contexto.")
                print("   (Se seu projeto for maior, aumente a variável 'LIMITE_SEGURANCA' no script)")
                return conteudo_total, arquivos_lidos

            ext = os.path.splitext(file)[1].lower()
            
            if ext in EXTENSOES_PERMITIDAS:
                caminho_completo = os.path.join(root, file)
                caminho_relativo = os.path.relpath(caminho_completo, diretorio_base)
                
                try:
                    # errors='ignore' ajuda a não travar se tiver algum caractere estranho
                    with open(caminho_completo, 'r', encoding='utf-8', errors='ignore') as f:
                        conteudo = f.read()
                        # Formata para o Gemini entender onde começa e termina cada arquivo
                        conteudo_total += f"--- ARQUIVO: {caminho_relativo} ---\n"
                        conteudo_total += conteudo + "\n"
                        conteudo_total += f"--- FIM DE {caminho_relativo} ---\n\n"
                        
                        arquivos_lidos += 1
                        print(f"   📄 Lido: {caminho_relativo}")
                except Exception as e:
                    print(f"   ❌ Erro ao ler {caminho_relativo}: {e}")

    print(f"--- Concluído: {arquivos_lidos} arquivos carregados. ---\n")
    return conteudo_total, arquivos_lidos

def start_chat():
    # Tenta usar o modelo mais inteligente primeiro
   #  nome_modelo = 'gemini-3-pro-preview'
   #  try:
   #      model = genai.GenerativeModel(nome_modelo)
   #  except:
   #      print(f"Modelo {nome_modelo} não encontrado, usando gemini-2.5-pro...")
   #      model = genai.GenerativeModel('gemini-2.5-pro')
    model = genai.GenerativeModel('gemini-2.5-flash')

    # Passo 1: Ler os arquivos da pasta onde você está
    diretorio_atual = os.getcwd()
    contexto_projeto, qtd_arquivos = ler_arquivos_projeto(diretorio_atual)
    
    chat = model.start_chat(history=[])

    # Passo 2: Enviar o código para o cérebro do Gemini (se houver arquivos)
    if qtd_arquivos > 0:
        print("Enviando código para análise (aguarde)...")
        
        prompt_sistema = (
            f"Você é um Engenheiro de Software Sênior (Gemini CLI). "
            f"Carreguei os arquivos do meu projeto local abaixo. "
            f"Analise a estrutura, sintaxe e lógica. Responda minhas dúvidas baseadas nestes arquivos.\n\n"
            f"{contexto_projeto}"
        )
        
        try:
            # Envia silenciosamente para configurar o contexto
            chat.send_message(prompt_sistema)
            print(">>> ✅ Gemini: Código recebido e analisado! Estou pronto.")
        except Exception as e:
            print(f">>> ❌ Erro ao enviar contexto (Talvez excedeu o tamanho): {e}")
    else:
        print(">>> ⚠️ Nenhum arquivo de código foi lido. O chat começará vazio.")

    print("\n--- Chat Iniciado (Digite 'sair' para fechar ou '/refresh' para reler arquivos) ---")

    # Loop principal da conversa
    while True:
        try:
            user_input = input("\nVocê: ")
            
            if user_input.lower() in ['sair', 'exit', 'quit']:
                print("Encerrando...")
                break
            
            # Comando especial para recarregar se você editar o código
            if user_input.lower() == '/refresh':
                print("\n--- Recarregando projeto... ---")
                start_chat() # Reinicia a função
                return

            if not user_input.strip():
                continue

            response = chat.send_message(user_input, stream=True)
            
            print("Gemini: ", end="")
            for chunk in response:
                print(chunk.text, end="")
            print()

        except KeyboardInterrupt:
            print("\nCancelado pelo usuário.")
            break
        except Exception as e:
            print(f"\nErro: {e}")

if __name__ == "__main__":
    start_chat()