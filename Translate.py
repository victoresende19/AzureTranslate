import os
import requests
import json
from dotenv import load_dotenv

# Importações para a PARTE 2 (Uso do Modelo)
from azure.core.credentials import AzureKeyCredential
from azure.ai.translation.text import TextTranslationClient

# --- CONFIGURAÇÃO INICIAL ---
# Carrega as variáveis do arquivo .env
load_dotenv()

# Credenciais e Endpoints carregados do .env
TRANSLATOR_KEY = os.getenv("TRANSLATOR_KEY")
TRANSLATOR_ENDPOINT = os.getenv("TRANSLATOR_ENDPOINT")
WORKSPACE_ID = os.getenv("WORKSPACE_ID")

# Endpoint da API de gerenciamento do Custom Translator
CUSTOM_TRANSLATOR_API_ENDPOINT = "https://portal.customtranslator.azure.ai"

# --- PARTE 1: FUNÇÕES DE GERENCIAMENTO DO MODELO (VIA API REST) ---

# Passo 3 do anexo: Criar um Projeto
def criar_projeto(nome_projeto, categoria_projeto, lang_origem, lang_destino):
    """Cria um novo projeto no Custom Translator."""
    url = f"{CUSTOM_TRANSLATOR_API_ENDPOINT}/api/texttranslator/v1.0/workspaces/{WORKSPACE_ID}/projects"
    headers = {"Ocp-Apim-Subscription-Key": TRANSLATOR_KEY, "Content-Type": "application/json"}
    body = {
        "name": nome_projeto,
        "languagePair": {
            "sourceLanguage": {"code": lang_origem},
            "targetLanguage": {"code": lang_destino}
        },
        "category": categoria_projeto,
        "description": f"Modelo para traduzir termos de {categoria_projeto}."
    }
    
    print(f"1. Criando o projeto '{nome_projeto}'...")
    response = requests.post(url, headers=headers, json=body)
    response.raise_for_status()  # Lança um erro se a requisição falhar
    
    project_info = response.json()
    project_id = project_info['id']
    print(f"   -> Projeto criado com sucesso. ID: {project_id}")
    return project_id

# Passo 4 do anexo: Carregar Arquivos de Dados
def carregar_arquivos(project_id, arquivo_origem, arquivo_destino, lang_origem_code):
    """Faz upload dos arquivos de treinamento para um projeto."""
    url = f"{CUSTOM_TRANSLATOR_API_ENDPOINT}/api/texttranslator/v1.0/projects/{project_id}/documents"
    headers = {"Ocp-Apim-Subscription-Key": TRANSLATOR_KEY}
    
    files_to_upload = [
        ("files", (os.path.basename(arquivo_origem), open(arquivo_origem, 'rb'), 'text/plain')),
        ("files", (os.path.basename(arquivo_destino), open(arquivo_destino, 'rb'), 'text/plain'))
    ]
    params = {"documentType": "training", "languageCode": lang_origem_code}

    print(f"2. Fazendo upload dos arquivos para o projeto {project_id}...")
    # O segundo arquivo é automaticamente associado como sendo o de destino (target)
    response = requests.post(url, headers=headers, files=files_to_upload, params=params)
    response.raise_for_status()
    print("   -> Upload dos arquivos concluído.")

# Passo 5 do anexo: Treinar um Modelo
def treinar_modelo(project_id, nome_modelo):
    """Inicia o processo de treinamento de um modelo."""
    url = f"{CUSTOM_TRANSLATOR_API_ENDPOINT}/api/texttranslator/v1.0/projects/{project_id}/models"
    headers = {"Ocp-Apim-Subscription-Key": TRANSLATOR_KEY, "Content-Type": "application/json"}
    body = {"name": nome_modelo}
    
    print(f"3. Iniciando o treinamento do modelo '{nome_modelo}'...")
    response = requests.post(url, headers=headers, json=body)
    response.raise_for_status()
    
    model_info = response.json()
    model_id = model_info['id']
    print(f"   -> Treinamento iniciado. ID do modelo: {model_id}")
    print("\nAVISO: O treinamento pode levar várias horas.")
    print("Monitore o status em: https://portal.customtranslator.azure.ai/")
    return model_id

# --- PARTE 2: FUNÇÃO DE USO DO MODELO (VIA SDK PYTHON) ---

# Chamar o modelo por meio da API do Tradutor
def traduzir_com_modelo_personalizado(categoria_projeto, lang_destino):
    """Traduz uma lista de textos usando o modelo personalizado treinado."""
    # O ID da Categoria é o que direciona a chamada para o seu modelo.
    # Formato: WorkspaceID + CategoriaDoProjeto
    category_id = f"{WORKSPACE_ID}{categoria_projeto}"

    print(f"\n--- Usando o Modelo Personalizado (Categoria: {category_id}) ---")

    client = TextTranslationClient(
        endpoint=TRANSLATOR_ENDPOINT,
        credential=AzureKeyCredential(TRANSLATOR_KEY)
    )

    textos_para_traduzir = [
        "The team will discuss the Product Backlog during Sprint Planning.",
        "We need to refine the user stories and fix the bugs."
    ]

    response = client.translate(
        content=textos_para_traduzir,
        to_language=lang_destino,
        # from_language="en", # Opcional, o serviço pode detectar
        category_id=category_id
    )

    print("Resultados da tradução:")
    for translation in response:
        print(f"Texto original: '{translation.source_text}'")
        for translated_text in translation.translations:
            print(f"  -> Tradução ({translated_text.to}): '{translated_text.text}'")


# --- BLOCO DE EXECUÇÃO PRINCIPAL ---
if __name__ == "__main__":
    
    # --- Configurações do seu projeto ---
    NOME_DO_PROJETO = "MeuProjetoTraducaoAgil"
    CATEGORIA_DO_PROJETO = "Agilidade" # Este nome será usado no ID da Categoria
    IDIOMA_ORIGEM = "en"
    IDIOMA_DESTINO = "pt"
    
    # === ETAPA 1: GERENCIAR E TREINAR O MODELO ===
    # Descomente as linhas abaixo para criar o projeto e iniciar o treinamento.
    # Execute o script UMA VEZ para esta etapa.
    
    try:
        # Criar arquivos de treinamento de exemplo
        with open("en-training.txt", "w", encoding='utf-8') as f:
            f.write("Product Backlog\nSprint Planning\nDaily Scrum\n")
        with open("pt-br-training.txt", "w", encoding='utf-8') as f:
            f.write("Backlog do Produto\nPlanejamento da Sprint\nReunião Diária\n")

        # Executa o fluxo de criação e treinamento
        id_projeto = criar_projeto(NOME_DO_PROJETO, CATEGORIA_DO_PROJETO, IDIOMA_ORIGEM, IDIOMA_DESTINO)
        carregar_arquivos(id_projeto, "en-training.txt", "pt-br-training.txt", IDIOMA_ORIGEM)
        treinar_modelo(id_projeto, f"Modelo{CATEGORIA_DO_PROJETO}_v1")
        
    except requests.exceptions.HTTPError as e:
        print(f"\nERRO na API de gerenciamento: {e}")
        print(f"Detalhes do erro: {e.response.text}")
    except Exception as e:
        print(f"Ocorreu um erro inesperado: {e}")
        
    
    # === ETAPA 2: USAR O MODELO PARA TRADUÇÃO ===
    # DEPOIS QUE O MODELO FOR TREINADO E PUBLICADO ('Deployed') no portal do Azure,
    # comente todo o bloco da "ETAPA 1" acima e descomente a linha abaixo para usar o modelo.
    
    # traduzir_com_modelo_personalizado(CATEGORIA_DO_PROJETO, IDIOMA_DESTINO)
