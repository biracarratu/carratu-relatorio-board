---
name: carratu-relatorio-board
description: Relatório de marketing e vendas para o board e o CFO, por Ubirajara Carratu - CAC blended e por canal, payback, LTV:CAC, NRR, magic number, crescimento do MRR, funil e pipeline por real investido, com nota de eficiência de crescimento 0-100 e narrativa de diretoria. Use quando o usuário pedir relatório para o board, conselho, investidores ou CFO, unit economics, eficiência de marketing, CAC e payback, ROI de marketing, report mensal ou trimestral de growth, ou "como justifico o orçamento de marketing". Também em inglês (board deck metrics, SaaS unit economics, marketing efficiency report). Entrega DOCX e PDF.
---

# Relatório para o board (Metodologia Carratu)

Autor: Ubirajara Carratu · Carratu revenue growth consulting. Versão 1.0.0 (nov/2026).
Licença: PolyForm Noncommercial 1.0.0 (ver `NOTICE.md`).

Board não quer saber de cliques. Quer saber quanto custa trazer um real de receita recorrente, em quanto tempo ele se
paga, se a base cresce sozinha e se o próximo real investido rende como o anterior. Você vai traduzir marketing e vendas
para essa língua, com números calculados e uma recomendação clara de onde pôr ou tirar dinheiro.

**Idioma:** o do usuário (`--lang pt|en`). `SKILL_DIR` é a pasta deste arquivo; trabalhe com `board_data/` e `outputs/`.
Referências: `references/data-model.md` (colunas e fórmulas), `references/rubric.json` (faixas e pesos),
`references/report-schema.md`.

---

## Etapa 0: Escuta ativa (uma rodada)

1. **Para quem e para quê**: reunião de conselho, investidores, CFO ou planejamento de orçamento? Qual decisão o
   relatório precisa apoiar (aumentar verba, cortar canal, contratar vendedor)?
2. **Dados**: planilha mensal (ofereça o modelo de `data-model.md`), CRM conectado para funil e pipeline, billing para
   MRR. Quais meses (padrão: últimos 12)?
3. **Modelo de receita**: recorrente (MRR) ou venda única; margem bruta; o que entra em custo de vendas.
4. **Formato**: relatório completo, 1 página executiva ou os dois.

## Etapa 1: Dados

Monte `mensal.csv` (e `canais.csv`, se houver) na pasta de trabalho, juntando planilha, CRM e billing. Mostre ao
usuário uma tabela dos meses montados e peça confirmação antes de calcular. **Nunca preencha mês faltante com estimativa**;
deixe em branco e diga.

## Etapa 2: Cálculo

```bash
python3 SKILL_DIR/scripts/board.py mensal.csv --out board_data [--channels canais.csv] [--months 12] --lang pt
```
Gera `metrics.json`, `auto_sections.json` e `charts/`. O resumo traz a janela completa, os últimos 3 meses contra os 3
anteriores, o magic number, os canais e a lista do que faltou.

## Etapa 3: Narrativa de diretoria

Responda, com números do resumo, as 4 perguntas do board:
1. **Estamos crescendo de forma eficiente?** Payback e LTV:CAC contra as faixas; tendência dos últimos 3 meses.
2. **O próximo real rende como o anterior?** Magic number e CAC marginal (últimos 3 vs anteriores): se o investimento
   subiu e o MRR novo não, há saturação.
3. **A base segura o crescimento?** NRR e churn de logos. NRR abaixo de 100% significa que a base encolhe sem venda nova.
4. **Onde pôr o próximo real?** Canais com menor CAC de marketing e maior participação no MRR novo; canais que pedem teste
   antes de corte.
Feche com **uma recomendação de orçamento** (manter, realocar, aumentar ou reduzir, com valores) e os riscos.

## Etapa 4: Relatório

`report.json` (`report-schema.md`): `score` = eficiência de crescimento e confiança; 6 a 8 `kpis`; resumo executivo
em linguagem de conselho (sem jargão de mídia); seção "Recomendação de orçamento" com tabela; recomendações e plano.
```bash
python3 SKILL_DIR/scripts/carratu_report.py board_data/report.json --auto board_data/auto_sections.json --out outputs --format both
```
O formato de 1 página serve como folha de rosto para a reunião. Confira as páginas como imagem e entregue.

## Princípios inegociáveis

- **Todo número vem do script**, e cada indicador diz a fórmula (`data-model.md`) quando o board perguntar.
- **CAC blended no topo, CAC de marketing nos canais.** Nunca compare os dois.
- **Tendência acima de foto.** Um mês bom não muda a tese; mostre a janela e os últimos 3 meses.
- **Sem maquiagem.** Número ruim vai para o resumo com a explicação e o plano, não para o anexo.
- **Recomendação com valor.** "Mover R$ X de A para B por 60 dias e medir Y" e não "otimizar canais".
