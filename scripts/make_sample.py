#!/usr/bin/env python3
"""Gera 18 meses de dados sintéticos (fictícios) de um SaaS B2B para testar a skill. Nenhum dado real.

Usage: python3 make_sample.py examples/ [--seed 4]
"""
import argparse
import csv
import os
import random

CHANNELS = {"Google Ads": (0.30, 1.6), "LinkedIn Ads": (0.25, 1.3), "Orgânico (SEO)": (0.12, 0.45), "Eventos": (0.18, 1.1),
            "Outbound": (0.15, 1.2)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--seed", type=int, default=4)
    a = ap.parse_args()
    rnd = random.Random(a.seed)
    os.makedirs(a.out, exist_ok=True)
    mrr, cust = 380000.0, 420
    rows, crow = [], []
    for i in range(18):
        y, m = 2025 + (5 + i) // 12, (5 + i) % 12 + 1
        mkt = 95000 * (1 + 0.035 * i) * rnd.uniform(0.92, 1.08)
        sales = 120000 * (1 + 0.02 * i)
        leads = int(mkt / rnd.uniform(160, 210))
        mql = int(leads * rnd.uniform(0.32, 0.38))
        sql = int(mql * rnd.uniform(0.40, 0.48))
        opps = int(sql * rnd.uniform(0.62, 0.70))
        eff = 1 - 0.012 * i  # eficiência caindo devagar: mais verba, retorno marginal menor
        new_c = max(8, int(opps * rnd.uniform(0.20, 0.25) * eff))
        arpa = rnd.uniform(1150, 1350)
        new_mrr = new_c * arpa
        exp = mrr * rnd.uniform(0.010, 0.016)
        lost = int(cust * rnd.uniform(0.012, 0.020))
        churn = lost * rnd.uniform(800, 1100) + mrr * rnd.uniform(0.002, 0.004)
        rows.append({"mes": f"{y}-{m:02d}", "investimento_marketing": round(mkt), "custo_vendas": round(sales), "leads": leads,
                     "mql": mql, "sql": sql, "oportunidades": opps, "clientes_novos": new_c, "mrr_novo": round(new_mrr),
                     "mrr_expansao": round(exp), "mrr_churn": round(churn), "clientes_inicio": cust, "clientes_cancelados": lost,
                     "mrr_inicio": round(mrr), "margem_bruta": "78%", "pipeline_gerado": round(opps * rnd.uniform(14000, 17000)),
                     "pipeline_marketing": round(opps * rnd.uniform(9000, 11000))})
        left_c, left_m = new_c, new_mrr
        for k, (sh, cost_eff) in CHANNELS.items():
            sp = mkt * sh
            c = max(0, round(new_c * sh / cost_eff * rnd.uniform(0.8, 1.2) / sum(s / e for s, e in CHANNELS.values()) * 1.0))
            crow.append({"mes": f"{y}-{m:02d}", "canal": k, "investimento": round(sp), "leads": int(leads * sh / cost_eff / 1.25),
                         "oportunidades": int(opps * sh / cost_eff / 1.25), "clientes": c, "mrr_novo": round(c * arpa)})
        mrr += new_mrr + exp - churn
        cust += new_c - lost
    for name, data in (("mensal_exemplo.csv", rows), ("canais_exemplo.csv", crow)):
        with open(os.path.join(a.out, name), "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(data[0]))
            w.writeheader()
            w.writerows(data)
    print(len(rows), len(crow))


if __name__ == "__main__":
    main()
