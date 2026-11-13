# Modelo de dados e fórmulas / Data model and formulas

## mensal.csv (uma linha por mês)

| Coluna | O que é | Destrava |
|---|---|---|
| `mes` | AAAA-MM (obrigatória) | tudo |
| `investimento_marketing` | mídia, ferramentas, agência, time de marketing | CAC, pipeline por R$ |
| `custo_vendas` | time comercial (salário, comissão, ferramentas) | CAC blended, magic number |
| `leads`, `mql`, `sql`, `oportunidades` | volumes do funil no mês | conversões |
| `clientes_novos`, `mrr_novo` | ganhos do mês e a receita recorrente que trouxeram | CAC, ARPA, payback |
| `mrr_expansao`, `mrr_churn` | upsell e perda (inclua contração no churn) | NRR, ponte de MRR |
| `clientes_inicio`, `clientes_cancelados`, `mrr_inicio` | base no início do mês e cancelamentos | churn de logos, LTV, crescimento |
| `margem_bruta` | % (ex.: 78%) | payback, LTV |
| `pipeline_gerado`, `pipeline_marketing` | valor de oportunidades criadas; parte originada por marketing | pipeline por R$, % marketing |

Sem receita recorrente (venda única)? Use `mrr_novo` com a receita nova do mês e deixe expansão, churn e NRR em branco:
o relatório mostra CAC, conversões e canais e marca o resto como sem dados.

`canais.csv` (opcional): `mes, canal, investimento, leads, oportunidades, clientes, mrr_novo`.

## Fórmulas (janela padrão: 12 meses)

| Indicador | Fórmula |
|---|---|
| CAC blended | (marketing + vendas) ÷ clientes novos |
| CAC de marketing | marketing ÷ clientes novos (é a base do CAC por canal) |
| ARPA novo | MRR novo ÷ clientes novos |
| Payback do CAC | CAC blended ÷ (ARPA novo × margem bruta), em meses |
| Churn de logos | clientes cancelados ÷ clientes no início (média mensal) |
| LTV | ARPA × margem bruta ÷ churn mensal de logos |
| LTV:CAC | LTV ÷ CAC blended |
| NRR anualizado | produto de (1 + (expansão − churn) ÷ MRR inicial) de cada mês, elevado a 12 ÷ meses |
| Crescimento do MRR | taxa mensal composta entre o MRR inicial da janela e o final |
| Magic number | (MRR líquido novo do último trimestre × 12) ÷ (marketing + vendas do trimestre anterior) |
| Pipeline por R$ 1 | pipeline gerado ÷ investimento de marketing |

## Notas e referências

Faixas em `rubric.json` (LTV:CAC 1x a 4x, payback 30 a 9 meses, NRR 90% a 115%, magic number 0,3 a 1,0, crescimento
mensal 0% a 5%). São referências de mercado para SaaS B2B; empresa em estágio inicial ou com venda enterprise pode ter
payback maior por desenho. Ajuste e explique em `methodology`.

## Como obter

Financeiro (investimento, custo de vendas, margem), CRM (funil, clientes, pipeline), billing ou ERP (MRR, expansão,
churn). Com HubSpot conectado, funil e pipeline saem por consulta; investimento quase sempre vem de planilha do
financeiro. Monte o CSV na pasta de trabalho antes de rodar; nunca estime um mês que não veio.
