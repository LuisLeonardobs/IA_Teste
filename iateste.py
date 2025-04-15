import tkinter as tk
from tkinter import scrolledtext, filedialog
import json
import os
import fitz
from docx import Document
import ollama
import requests
from bs4 import BeautifulSoup
from itertools import islice
from duckduckgo_search import DDGS
from googlesearch import search
import random

CACHE_FILE = "ia_memoria.json"
BASE_CONHECIMENTO = "conhecimento.txt"

##### Inicializa os arquivos
if not os.path.exists(CACHE_FILE):
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump([], f, ensure_ascii=False, indent=2)

if not os.path.exists(BASE_CONHECIMENTO):
    with open(BASE_CONHECIMENTO, "w", encoding="utf-8") as f:
        f.write("")

def carregar_memoria():
    with open(CACHE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def atualizar_memoria(pergunta, resposta, feedback=None):
    log = carregar_memoria()
    log.append({
        "pergunta": pergunta,
        "resposta": resposta,
        "feedback": feedback or "padrão"
    })
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(log, f, ensure_ascii=False, indent=2)

def buscar_duckduckgo(query):
    textos = []
    try:
        with DDGS() as ddgs:
            resultados = ddgs.text(query, region="wt-wt", safesearch="off", timelimit="y")
            for r in islice(resultados, 2):
                html = requests.get(r['href'], timeout=5).text
                soup = BeautifulSoup(html, 'html.parser')
                textos.append(soup.get_text()[:1500])
    except:
        pass
    return textos

def buscar_google(query):
    textos = []
    try:
        for url in islice(search(query, num_results=2), 2):
            html = requests.get(url, timeout=5).text
            soup = BeautifulSoup(html, 'html.parser')
            textos.append(soup.get_text()[:1500])
    except:
        pass
    return textos

def buscar_todos(query):
    fontes = [buscar_duckduckgo, buscar_google]
    random.shuffle(fontes)
    resultados = []
    for buscador in fontes:
        resultados.extend(buscador(query))
    return "\n\n".join(resultados[:3])

def carregar_conhecimento():
    with open(BASE_CONHECIMENTO, "r", encoding="utf-8") as f:
        return f.read()

def perguntar_ao_modelo(pergunta, contexto_online, memoria):
    conhecimento_local = carregar_conhecimento()
    prompt = (
        "Você é um assistente treinado com documentos do usuário e informações da internet.\n\n"
        "🧠 Conhecimento base:\n" + conhecimento_local[:3000] +
        "\n\n🌐 Informações recentes:\n" + contexto_online +
        "\n\n📜 Histórico recente:\n"
    )
    for m in memoria[-5:]:
        prompt += f"Usuário: {m['pergunta']}\nIA: {m['resposta']}\n"

    prompt += f"\nUsuário: {pergunta}\nIA:"
    resposta = ollama.chat(model='mistral', messages=[{"role": "user", "content": prompt}])
    return resposta['message']['content']

def processar_pergunta():
    pergunta = entrada.get()
    if not pergunta.strip():
        return
    memoria = carregar_memoria()
    contexto = buscar_todos(pergunta)
    resposta = perguntar_ao_modelo(pergunta, contexto, memoria)
    atualizar_memoria(pergunta, resposta)
    saida.configure(state='normal')
    saida.insert(tk.END, f"\n🧑 Você: {pergunta}\n🤖 IA: {resposta}\n")
    saida.configure(state='disabled')
    entrada.delete(0, tk.END)

##### Funções de leitura
def extrair_texto_pdf(caminho):
    doc = fitz.open(caminho)
    return "\n".join([page.get_text() for page in doc])

def extrair_texto_docx(caminho):
    doc = Document(caminho)
    return "\n".join([p.text for p in doc.paragraphs])

def extrair_texto_arquivo(caminho):
    try:
        if caminho.endswith(".pdf"):
            return extrair_texto_pdf(caminho)
        elif caminho.endswith(".docx"):
            return extrair_texto_docx(caminho)
        elif caminho.endswith(".txt"):
            with open(caminho, "r", encoding="utf-8") as f:
                return f.read()
    except Exception as e:
        return f"[Erro ao carregar {caminho}: {e}]"
    return ""

def adicionar_ao_conhecimento(texto):
    with open(BASE_CONHECIMENTO, "a", encoding="utf-8") as f:
        f.write("\n\n" + texto)

###### Carregar único documento
def carregar_documento():
    caminho = filedialog.askopenfilename(filetypes=[("Documentos", "*.pdf *.txt *.docx")])
    if caminho:
        texto = extrair_texto_arquivo(caminho)
        adicionar_ao_conhecimento(texto)
        saida.configure(state='normal')
        saida.insert(tk.END, f"\n📥 Documento carregado: {os.path.basename(caminho)}\n")
        saida.configure(state='disabled')

##### Carregar todos os documentos de uma pasta
def carregar_pasta():
    pasta = filedialog.askdirectory()
    if pasta:
        arquivos = [os.path.join(pasta, f) for f in os.listdir(pasta) if f.endswith((".pdf", ".txt", ".docx"))]
        for arquivo in arquivos:
            texto = extrair_texto_arquivo(arquivo)
            adicionar_ao_conhecimento(texto)
            saida.configure(state='normal')
            saida.insert(tk.END, f"\n📂 Arquivo importado: {os.path.basename(arquivo)}\n")
            saida.configure(state='disabled')

##### Interface gráfica
janela = tk.Tk()
janela.title("IA Aprendizado Contínuo + Documentos Offline")

saida = scrolledtext.ScrolledText(janela, wrap=tk.WORD, state='disabled', width=90, height=25)
saida.grid(column=0, row=0, padx=10, pady=10, columnspan=4)

entrada = tk.Entry(janela, width=70)
entrada.grid(column=0, row=1, padx=10, pady=10)

botao_perguntar = tk.Button(janela, text="Perguntar", command=processar_pergunta)
botao_perguntar.grid(column=1, row=1)

botao_documento = tk.Button(janela, text="📄 Documento", command=carregar_documento)
botao_documento.grid(column=2, row=1)

botao_pasta = tk.Button(janela, text="📂 Importar Pasta", command=carregar_pasta)
botao_pasta.grid(column=3, row=1)

janela.mainloop()
