# Correções realizadas após a auditoria

O relatório `AUDITORIA_TECNICA.md` registra o estado anterior às alterações.

- DOCX com imagens, cabeçalhos ou rodapés com conteúdo, campos, links, riscado/realce, tabelas mescladas/aninhadas e outros recursos reconhecidos como não preserváveis são recusados com mensagem. Trechos de parágrafos e células de tabela com negrito parcial, itálico, sublinhado, sobrescrito e subscrito agora são preservados; o detector não garante cobertura de todo o formato DOCX. Tabelas simples têm bordas laterais abertas (padrão IBGE). Sempre revise a saída e guarde o original.
- Limites: 5 MiB por requisição, 40 MiB de conteúdo DOCX descompactado, 1.000 entradas ZIP e rate limiting em memória por IP (`RATE_LIMIT_PER_MINUTE`, padrão 60/min); arquivos com entradas duplicadas ou protegidos por senha são recusados. Esses limites não substituem rate limiting distribuído e proteções na hospedagem.
- Atualizadas versões de FastAPI, Starlette, Pydantic e python-multipart. `pip-audit -r requirements.txt` não encontrou vulnerabilidades conhecidas na consulta realizada em 13/11/2026; isso não garante ausência de vulnerabilidades.
- A classificação não trata automaticamente parágrafos longos sem referência explícita como citação longa; citações diretas em texto puro com `> 240` caracteres e `(AUTOR, ANO, p. X)` no final recebem recuo de 4 cm, mantendo necessidade de revisão manual. A reorganização automática e a inferência de metadados aceitam rótulos e campos opcionais do formulário.
- Frontend usa API local para `localhost` e loopback; verifica `/health`; rejeita seleção simultânea de texto e arquivo; exibe campos opcionais de capa/folha de rosto; apresenta aviso de revisão e anuncia alterações de estado.
- Testados oito casos de `tests/predeploy_check.py`, oito casos de `tests/test_protection.py` e dezessete casos de `tests/test_mvp_flow.py` com exemplos sintéticos (33 testes no total).

Ainda pendentes: preservação de imagens, cabeçalhos/rodapés ricos e tabelas mescladas; cálculo automático de número de página sem atualização manual do campo TOC no Word; validação de conformidade ABNT institucional completa; CORS com origem efetiva e política de privacidade; testes de acessibilidade em leitor de tela e implantação. Não houve deploy nem modificação de serviços externos.
