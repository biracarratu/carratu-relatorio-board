# report.json: a narrativa do relatório / the report narrative

`scripts/carratu_report.py` junta os blocos calculados pelos scripts da skill (`--auto auto_sections.json`) com a
narrativa que o Claude escreve em `report.json`. **Regra de ouro: todo número da narrativa vem de `metrics.json`
ou do resumo impresso pelos scripts. Nunca invente, arredonde para cima ou estime um número.**

`carratu_report.py` merges the computed blocks (`--auto`) with the narrative Claude writes in `report.json`.
**Every number in the narrative must come from `metrics.json` or the script summary.**

```json
{
  "lang": "pt",
  "title": "Diagnóstico de funil e receita",
  "subtitle": "Onde o pipeline vaza e o que destravar primeiro",
  "eyebrow": "CARRATU GROWTH KIT · DIAGNÓSTICO DE FUNIL",
  "client_name": "Empresa",
  "date": "2026-11-12",
  "score": {"value": 57, "label": "Saúde do funil", "confidence": 100,
            "verdict": "1 frase com o diagnóstico central"},
  "kpis": [{"label": "Win rate", "value": "15%", "note": "IC 95% 12% a 18%", "status": "warn"}],
  "executive_summary": "3 a 5 frases. **Negrito** no achado principal. Parágrafos separados por \\n\\n.",
  "top_priorities": ["Prioridade 1, específica e com número", "Prioridade 2", "Prioridade 3"],
  "biggest_strength": "1 frase com evidência",
  "context": {"business": "...", "icp": "...", "market": "...", "goal": "...", "period": "...", "target": "..."},
  "data_sources": ["Export do HubSpot (640 negócios, nov/2025 a nov/2026)"],
  "sections": [
    {"title": "Leitura do analista", "page_break_before": true, "position": "start | end", "intro": "Texto livre", "blocks": [
      {"type": "text", "text": "..."},
      {"type": "bullets", "items": ["..."]},
      {"type": "callout", "heading": "Título", "text": "..."},
      {"type": "table", "header": ["A", "B"], "rows": [["1", "2"]], "widths": [8, 9], "status_col": null},
      {"type": "kpis", "items": [{"label": "...", "value": "..."}]},
      {"type": "scores", "items": [{"name": "Conversão", "score": 52, "note": "..."}]},
      {"type": "chart", "path": "charts/x.png", "width_cm": 15, "caption": "..."}
    ]}
  ],
  "recommendations": [
    {"priority": "Crítica | Alta | Média | Ganho rápido", "issue": "O que fazer, no imperativo",
     "how": "Como fazer, 1 a 2 frases", "effort": "Baixo | Médio | Alto", "impact": "Baixo | Médio | Alto",
     "owner": "Vendas | Marketing | RevOps | Liderança | CS"}
  ],
  "action_plan": {"30": ["..."], "60": ["..."], "90": ["..."]},
  "limitations": ["O que não foi possível medir e como medir"],
  "methodology": "Parágrafo curto: fórmulas e faixas usadas, e qualquer ajuste feito na rubrica.",
  "onepager_summary": "Opcional: 2 a 3 frases para o diagnóstico de 1 página",
  "cta_title": "Opcional: sobrescreve o CTA da marca", "cta_text": "Opcional"
}
```

Ordem no relatório: capa → resumo, prioridades, contexto e fontes → suas seções (`position` padrão `start`) →
blocos calculados (`--auto`) → seções com `"position": "end"` → recomendações → plano 30/60/90 → limitações →
metodologia → CTA.

Em inglês, use `"lang": "en"` e escreva tudo em inglês; prioridades em inglês também funcionam
(`Critical | High | Medium | Quick win`). Status aceitos em tabelas e KPIs: `pass`, `warn`, `fail`.

## Como priorizar (visão de growth)

1. **Crítica**: vazamento que custa receita agora e é barato de estancar (ex.: etapa com passagem muito abaixo
   das outras, metade do pipeline parado, campo crítico do CRM vazio que impede gestão).
2. **Alta**: alavanca de receita comprovada nos dados (canal, segmento ou vendedor com valor por oportunidade 2x
   acima da média e amostra suficiente).
3. **Ganho rápido**: esforço baixo, impacto visível em 30 dias (higiene de dados, SLA, limpeza de pipeline).
4. **Média**: o resto que vale fazer, mas não muda o trimestre.

Cada recomendação cita o número que a justifica e diz quem é o dono. Nada genérico do tipo "melhore a qualificação".
