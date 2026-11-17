# Auditoria técnica — SaaS ABNT

Data: 13/11/2026. Escopo: recuperação inicial, inspeção estática e testes locais com dados sintéticos. Repositório `akogkoga/saasabnt`, branch `main`, commit `ec940a7` (Add adaptive formatting mode). Nenhum commit, push, merge ou deploy foi realizado.

## 1. Inventário e arquitetura

- Backend FastAPI em `app/main.py`; `GET /health`, `POST /format` com formulário multipart (`text`, `file`, `complete_missing`). O mesmo processo serve os arquivos estáticos em `/`.
- Pipeline: parser → normalizador → extração de atributos → contexto e pesos/softmax → classificador → estrutura → ordenação → validação/correção e convergência de IR → geração DOCX → verificação de conteúdo renderizado. A lógica de classificação é heurística determinística, não há modelo treinado ou comprovação estatística de probabilidade.
- Frontend HTML/CSS/JavaScript estático em `frontend/`; `config.js` aponta para `https://saasabnt-api.onrender.com` inclusive quando servido localmente.
- Geração com `python-docx`; implantação declarada para Render (`render.yaml`) e Netlify (`netlify.toml`). Testes existentes: `tests/predeploy_check.py`.
- Histórico recente: `ec940a7` modo adaptativo; `763f1d7` orientação de entrada; `41d1f5f` expansão do mecanismo; `c7b522a` estrutura obrigatória; `c9f2d80` integração com Render; `f26a8a7` configuração Render. `main` alinhada com `origin/main` no clone.

## 2. Ambiente e reprodução no Linux Mint

Sistema identificado: Linux Mint 22.3 (base Ubuntu noble); shell Bash; Git 2.43.0; Python 3.12.3; pip 24.0 do sistema; `venv` disponível. Node, npm e LibreOffice já disponíveis. A versão Python corresponde a `.python-version` (3.12). Não foi necessária instalação global ou administrativa. Clone em `~/Projetos/saasabnt`; `.venv` instalado nesse diretório. `pip check`: `No broken requirements found`. Dependências diretas instaladas: FastAPI 0.111.0, Uvicorn 0.30.1, python-docx 1.1.2, Pydantic 2.7.4, python-multipart 0.0.9; Starlette resolvido como 0.37.2. Dependências transitivas não estão travadas, portanto a instalação futura pode diferir. O resultado de `pip check` não é auditoria de segurança.

Reprodução, em máquina semelhante, após verificar que o destino não existe:

```bash
mkdir -p ~/Projetos
git clone https://github.com/akogkoga/saasabnt.git ~/Projetos/saasabnt
cd ~/Projetos/saasabnt
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m pip check
.venv/bin/python tests/predeploy_check.py
.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Para sair do ambiente, basta parar o servidor com Ctrl+C; ativação opcional: `source .venv/bin/activate`. O comando de instalação reproduz versões vulneráveis e destina-se somente à investigação local; não expor esse ambiente à rede. Sem acesso ao índice de pacotes, a instalação precisa de conexão ou cache prévio.

## 3. Resultados reais

| Verificação | Resultado observado |
|---|---|
| `python tests/predeploy_check.py` no `.venv` | **8 testes passaram**, em 2,078 s: saúde, assets, modo adaptativo, preenchimento, tabela simples, referências, erros e configuração Netlify. |
| `GET http://127.0.0.1:8765/health` | HTTP 200, `{"status":"ok"}`. |
| `POST /format` via curl, texto sintético | HTTP 200, `Content-Type` DOCX, `Content-Disposition` de download, 37.489 bytes, identificado como Word 2007+, estado `finalized`. |
| DOCX sintético com imagem, cabeçalho, negrito parcial e tabela 2×2 | HTTP 200/`finalized`; tabela e texto das quatro células preservados; imagens 1→0; cabeçalho de teste→vazio; negrito parcial convertido em texto sem negrito. Teste com `TestClient`, usando dados gerados para a auditoria. |
| Frontend e download via Playwright | Após substituir `config.js` somente na rota de teste para usar a API local, formulário de texto, estado finalizado e download concluídos. O DOCX baixado abriu com `python-docx` e continha os parágrafos sintéticos esperados. |
| Produção `GET https://saasabnt-api.onrender.com/health` | `curl` atingiu timeout de 25 s sem resposta; consulta alternativa também inacessível. Disponibilidade não confirmada; timeout isolado não prova indisponibilidade permanente. Nenhum documento foi enviado à produção. |

O primeiro ensaio em sandbox isolado iniciou Uvicorn, mas outros processos não conseguiam alcançar seu loopback e o `TestClient` não concluiu; as verificações acima foram repetidas fora desse isolamento, mantendo o servidor vinculado a `127.0.0.1`. A primeira tentativa do Playwright falhou por diretório de cache somente leitura; uma segunda sessão com acesso adequado abriu o navegador, mas a navegação excedeu 30 s. Uma nova tentativa concluiu o fluxo com configuração temporária da API local e download; a sessão foi fechada.

## 4. Funcionalidades e limitações

**Funcionando nos casos testados:** saúde, retorno de DOCX por HTTP, processamento de texto, validação de ausência de entrada e arquivo inválido, modo de preenchimento, tabela simples e referência sintética, conforme os oito testes.

**Parciais:** upload DOCX com conteúdo rico; classificação e reordenação automática; criação de estrutura completa com marcadores; preservação de tabelas apenas para o caso simples coberto. O hash de renderização compara texto e células com o IR já simplificado, não com o documento original: não comprova fidelidade de imagens, estilos ou conteúdo eliminado antes do IR. O estado `finalized` significa aprovação dos controles internos, não conformidade ABNT nem preservação integral.

**Não verificadas:** upload pelo navegador, responsividade e navegação assistiva em dispositivos reais, comportamento do frontend publicado, serviço Render em produção, Netlify publicado, arquivos complexos, tabelas mescladas/aninhadas, hyperlinks, notas, fórmulas, revisões, rodapés, paginação impressa e aplicação fiel das normas em documentos representativos. Não se inspecionou configuração real dos serviços ou seus segredos.

## 5. Achados reproduzidos e riscos

### P0 — perda silenciosa de dados

`app/parser/engine.py` ignora imagens explicitamente, descarta parágrafos sem texto e extrai texto/rótulos básicos; `app/docx_generator/engine.py` cria um documento novo. O ensaio acima comprovou perda de imagem, cabeçalho e negrito parcial mesmo com sucesso. Isso impede uso seguro em documentos cujo conteúdo precise ser preservado. Estruturas adicionais também podem ser perdidas, mas não foram testadas individualmente. Evitar apresentação como conversor fiel até resolver ou informar claramente e bloquear formatos não suportados.

### P0 — dependências expostas a negação de serviço

`python-multipart==0.0.9` está no intervalo afetado por [GHSA-59g5-xgcq-4qw3](https://github.com/advisories/GHSA-59g5-xgcq-4qw3) (<0.0.18) e [GHSA-pp6c-gr5w-3c5g](https://github.com/advisories/GHSA-pp6c-gr5w-3c5g) (<0.0.27). O endpoint recebe multipart, portanto a superfície é pertinente; exploração não foi executada. A versão transitiva Starlette 0.37.2 também está no intervalo de [GHSA-f96h-pmfr-66vw](https://github.com/advisories/GHSA-f96h-pmfr-66vw). Revisar o conjunto de versões e testar atualização compatível; não simplesmente alterar uma versão isolada. Não se fez varredura exaustiva de todas as dependências.

### P1 — limites e validação insuficientes

`app/main.py` lê todo o arquivo com `await file.read()` sem limite explícito de tamanho; não há limite de texto, controles de taxa, autenticação ou política de retenção registrados no código inspecionado. DOCX é um ZIP e pode implicar consumo desproporcional de recursos; não foi tentada exploração. `Parser.from_docx` captura todas as exceções como arquivo inválido, ocultando causa interna; demais falhas do pipeline não têm tratamento específico no endpoint. Entrada simultânea de arquivo e texto prioriza arquivo silenciosamente.

### P1 — classificação e reordenação podem alterar o sentido

`classifier/engine.py` usa sinais e limiares fixos; parágrafo com mais de 240 caracteres e pelo menos três pontos é tratado como citação longa, sem evidência de citação. O resultado precisa de revisão humana. `structure_builder` usa os dois primeiros blocos como possível capa; `ordering_engine` reorganiza fases e referências, usa marcadores e pressupõe título e autor nas duas primeiras posições. Em modo completo, gera dados genéricos e ano corrente; o sumário é uma lista gerada, não se demonstrou numeração de páginas. Essas são análises de código, não bugs de todos os documentos.

### P1 — declaração de conformidade

Há código e testes para A4 e margens 3/3/2/2 cm; README descreve fonte, espaçamentos e recuos. Verificar visualmente e por casos representativos cada regra, versões aplicáveis das normas, exceções e instruções institucionais antes de alegar conformidade. Não houve comparação normativa autorizada e completa; a mensagem de interface “100%” pode sugerir garantia não comprovada.

### P2 — interface e acessibilidade

O formulário tem rótulo para texto, botão de limpeza com nome acessível e modal com `role=dialog`. A inspeção do código não demonstra captura/restauração de foco, fechamento com Escape ou anúncio de progresso/erros por região viva; avaliar no navegador e com leitor de tela. Disponibilizar erros compreensíveis, aviso explícito de perda e escolha clara entre texto/arquivo. A interface mostra informações internas como IR, pouco úteis ao usuário. O modal de download exibiu a mensagem informal “agradeça o ko pelo carinho folgada”, inadequada para uma apresentação profissional. A URL remota fixa em `frontend/config.js` faz uma página local chamar a API de produção por padrão; para teste local seguro, ajustar configuração apenas em cópia local temporária ou com mecanismo de configuração apropriado, sem enviar documentos à produção.

## 6. Deploy e documentação

`render.yaml` instala requirements, inicia `uvicorn app.main:app` em `0.0.0.0:$PORT` e define `ALLOWED_ORIGINS=*`. `app/main.py` habilita CORS apenas quando variável está definida; métodos GET/POST, cabeçalhos livres e alguns cabeçalhos expostos. O wildcard permite leitura por qualquer origem no navegador; não é autenticação nem substitui limites de recursos. Restringir à origem real após identificá-la. Não há URL Netlify identificada no repositório. `netlify.toml` publica `frontend` e redireciona rotas a `index.html`. Não se validou ambiente implantado, domínio, políticas de rede ou proteção do Render/Netlify.

README instrui `python app/main.py`, mas o projeto usa imports absolutos `app.*`: execução direta pode falhar conforme caminho de importação; usar `python -m uvicorn app.main:app`. A documentação mistura afirmações normativas com implementação sem evidência de conformidade. `PRE_DEPLOY.md` usa comandos Windows e anuncia seis testes, enquanto a suíte atual tem oito. Incluir Linux, configuração local da API, dependências, limites, riscos e critérios de testes; corrigir números e exemplos. Não se comprovou a falha do comando direto nesta execução.

## 7. Plano de recuperação para aprovação

- **P0:** impedir perda silenciosa; estabelecer política de preservação ou rejeição explícita dos recursos não suportados; criar testes de ida e volta com imagens, estilos, cabeçalho/rodapé, hyperlinks e tabelas complexas. Atualizar dependências afetadas em conjunto, validar testes e limitar exposição pública.
- **P1:** impor limites de upload, descompressão, tempo e taxa; validação e erros consistentes; criar corpus sintético representativo com expectativas de conteúdo, ordenação e falsos positivos; definir versões de normas e revisar com especialista. Esclarecer marcadores e não afirmar 100% de conformidade.
- **P2:** corrigir configuração do frontend local/produção, CORS com origem conhecida, acessibilidade de modal e estados, feedback e seleção de entrada. Fixar transitivas ou lockfile; executar auditoria automatizada de dependências, CI e testes de integração/navegador.
- **P3:** simplificar pipeline e nomenclatura, medir desempenho, definir observabilidade e documentação de operação e manutenção. Remover módulos mortos somente após análise de dependências.

## 8. Critérios objetivos para portfólio

1. Corpus sintético documentado preserva todos os recursos prometidos; recursos não suportados produzem aviso ou rejeição explícitos, sem perda silenciosa.
2. Nenhuma vulnerabilidade conhecida de alta ou crítica sem tratamento documentado nas dependências implantadas; limites de upload e testes negativos aprovados.
3. Testes automatizados de backend e navegador aprovados no commit publicado, incluindo upload, estados de erro e download; CI reproduzível e dependências travadas.
4. Regras ABNT declaradas delimitadas por norma/edição e validadas com amostras e revisão qualificada; sem promessa de conformidade integral não comprovada.
5. Frontend e API publicados e verificados ponta a ponta, CORS restrito, URLs corretas, saúde e logs verificados; deploy somente após autorização separada.
6. README com instalação Linux, execução, testes, limites de preservação, privacidade e exemplos sintéticos. Acessibilidade básica por teclado, foco e mensagens revisadas.

## 9. Fontes e limitações

As referências de segurança acima são avisos públicos da base GitHub Advisory; representam evidência de versões afetadas, não prova de exploração. O serviço externo não foi modificado. Codebase Memory MCP não estava disponível no inventário de ferramentas; a arquitetura foi inspecionada diretamente em arquivos selecionados. Não houve auditoria independente de todas as normas, dependências e combinações de DOCX; este diagnóstico é baseado nos testes e trechos descritos.
