# ABNT Formatter Engine

Backend modular para formatação automática de documentos seguindo a norma ABNT NBR 14724.

## 🚀 Como Rodar

1. **Instale as dependências:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Inicie o servidor:**
   ```bash
   python app/main.py
   ```

3. **Use o endpoint:**
   O servidor estará rodando em `http://localhost:8000`.
   Você pode testar via cURL ou Postman enviando um `POST` para `/format`.

### Exemplo cURL (Texto):
```bash
curl -X POST http://localhost:8000/format \
     -F "text=TÍTULO DO TRABALHO\nNOME DO AUTOR\nINTRODUÇÃO\nEste é um texto de introdução." \
     --output meu_trabalho.docx
```

## 🏗️ Arquitetura

- **Parser**: Extrai blocos de texto de strings ou arquivos .docx.
- **Rules Engine**: Classifica blocos (Heading, Paragraph, Citation) de forma determinística.
- **Structure Builder**: Monta a árvore do documento (Capa, Introdução, Desenvolvimento, etc).
- **DOCX Generator**: Aplica as regras visuais da ABNT (margens, fontes, recuos) usando `python-docx`.

## 📐 Regras Aplicadas

- Fonte: Times New Roman, Tamanho 12.
- Margens: Sup/Esq 3cm, Inf/Dir 2cm.
- Espaçamento: 1.5 (Geral) e 1.0 (Citações Longas/Referências).
- Recuo: 1.25cm na primeira linha de parágrafos.
- Citação Longa: Recuo de 4cm à esquerda, fonte 10.

⚡ GOLDCODE rules applied — global_rules.md v3.0
