#!/usr/bin/env python3
"""Relatório de marketing e vendas para o board: eficiência de crescimento em linguagem de CFO.

Uso:
  python3 board.py mensal.csv --out board_data [--channels canais.csv] [--months 12] [--lang pt|en] [--currency R$]

mensal.csv: uma linha por mês. Colunas (nomes em PT ou EN, ver references/data-model.md); só "mes" é obrigatória,
o resto destrava indicadores: investimento_marketing, custo_vendas, leads, mql, sql, oportunidades, clientes_novos,
mrr_novo, mrr_expansao, mrr_churn, clientes_inicio, clientes_cancelados, mrr_inicio, margem_bruta, pipeline_gerado,
pipeline_marketing.
canais.csv (opcional): mes, canal, investimento, leads, oportunidades, clientes, mrr_novo.
Saídas: metrics.json, auto_sections.json, charts/.

Board-ready marketing and sales efficiency report (CAC, payback, LTV:CAC, NRR, magic number).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from carratu_data import read_table, detect_columns, parse_money, parse_date, fmt_money, fmt_pct, fmt_num, dump  # noqa
import carratu_charts as C  # noqa

F = {
    "month": ["mes", "month", "periodo", "competencia", "data", "date"],
    "mkt": ["investimento marketing", "investimento_marketing", "marketing spend", "gasto marketing", "custo marketing", "investimento em marketing"],
    "sales_cost": ["custo vendas", "custo_vendas", "sales cost", "custo comercial", "sales spend", "folha comercial"],
    "leads": ["leads"], "mql": ["mql", "mqls"], "sql": ["sql", "sqls"],
    "opps": ["oportunidades", "opportunities", "opps", "negocios criados"],
    "new_cust": ["clientes novos", "clientes_novos", "new customers", "novos clientes", "ganhos"],
    "new_mrr": ["mrr novo", "mrr_novo", "new mrr", "receita nova", "new revenue"],
    "exp_mrr": ["mrr expansao", "mrr_expansao", "expansion mrr", "expansao"],
    "churn_mrr": ["mrr churn", "mrr_churn", "churned mrr", "mrr perdido", "churn mrr", "contracao e churn"],
    "cust_start": ["clientes inicio", "clientes_inicio", "customers start", "base inicio", "clientes no inicio"],
    "cust_lost": ["clientes cancelados", "clientes_cancelados", "churned customers", "cancelamentos", "logos perdidos"],
    "mrr_start": ["mrr inicio", "mrr_inicio", "starting mrr", "mrr no inicio", "mrr base"],
    "gm": ["margem bruta", "margem_bruta", "gross margin", "margem"],
    "pipe": ["pipeline gerado", "pipeline_gerado", "pipeline created", "pipeline criado"],
    "pipe_mkt": ["pipeline marketing", "pipeline_marketing", "marketing sourced pipeline", "pipeline de marketing"],
}
CH = {"month": ["mes", "month", "periodo"], "channel": ["canal", "channel", "origem", "source"],
      "spend": ["investimento", "spend", "custo", "gasto"], "leads": ["leads"], "opps": ["oportunidades", "opportunities", "opps"],
      "cust": ["clientes", "customers", "ganhos"], "mrr": ["mrr novo", "mrr_novo", "new mrr", "mrr", "receita"]}
T = {
    "pt": {"kpis": "Os números que o board pergunta", "cac": "CAC (blended)", "payback": "Payback do CAC", "ltv_cac": "LTV:CAC",
           "nrr": "NRR anualizado", "magic": "Magic number", "new_mrr": "MRR novo", "growth": "Crescimento do MRR", "logo_churn": "Churn de logos",
           "months": "meses", "per_month": "/mês", "scores": "Eficiência de crescimento por indicador", "trend": "Tendência",
           "funnel": "Funil mensal e conversões", "month": "Mês", "conv": "Conversões", "channels": "Eficiência por canal",
           "channel": "Canal", "spend": "Investimento", "cpl": "Custo por lead", "cpo": "Custo por oportunidade", "cust": "Clientes",
           "share_spend": "% do investimento", "share_mrr": "% do MRR novo", "mrr_bridge": "MRR novo e expansão por mês",
           "last": "Últimos 3 meses", "prev": "3 meses anteriores", "delta": "Variação", "metric": "Indicador", "pipe_eff": "Pipeline por R$ 1 investido",
           "mkt_share": "Pipeline originado por marketing", "na": "sem dados", "spend_vs_mrr": "Investimento vs MRR novo",
           "cac_trend": "CAC blended por mês", "q": "Comparativo trimestral",
           "cac_mkt": "CAC de marketing (só verba de mídia e marketing)", "ch_note": "Por canal, o CAC considera só o investimento de marketing do canal; o CAC blended do topo do relatório inclui também o custo do time comercial."},
    "en": {"kpis": "The numbers the board asks for", "cac": "CAC (blended)", "payback": "CAC payback", "ltv_cac": "LTV:CAC",
           "nrr": "Annualized NRR", "magic": "Magic number", "new_mrr": "New MRR", "growth": "MRR growth", "logo_churn": "Logo churn",
           "months": "months", "per_month": "/mo", "scores": "Growth efficiency by metric", "trend": "Trend",
           "funnel": "Monthly funnel and conversions", "month": "Month", "conv": "Conversions", "channels": "Efficiency by channel",
           "channel": "Channel", "spend": "Spend", "cpl": "Cost per lead", "cpo": "Cost per opportunity", "cust": "Customers",
           "share_spend": "% of spend", "share_mrr": "% of new MRR", "mrr_bridge": "New and expansion MRR by month",
           "last": "Last 3 months", "prev": "Previous 3 months", "delta": "Change", "metric": "Metric", "pipe_eff": "Pipeline per $1 spent",
           "mkt_share": "Marketing-sourced pipeline", "na": "no data", "spend_vs_mrr": "Spend vs new MRR",
           "cac_trend": "Blended CAC by month", "q": "Quarter over quarter",
           "cac_mkt": "Marketing CAC (marketing spend only)", "ch_note": "Channel CAC uses only that channel's marketing spend; the blended CAC at the top also includes the sales team cost."},
}


def s(xs):
    xs = [x for x in xs if x is not None]
    return sum(xs) if xs else None


def div(a, b):
    return a / b if (a is not None and b) else None


def lin(v, bad, good):
    if v is None:
        return None
    x = (v - bad) / (good - bad)
    return round(100 * max(0.0, min(1.0, x)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("file")
    ap.add_argument("--out", default="board_data")
    ap.add_argument("--channels", default=None)
    ap.add_argument("--months", type=int, default=12)
    ap.add_argument("--lang", default="pt")
    ap.add_argument("--currency", default=None)
    ap.add_argument("--map", default=None)
    ap.add_argument("--rubric", default=os.path.join(HERE, "..", "references", "rubric.json"))
    a = ap.parse_args()
    lang = a.lang if a.lang in T else "pt"
    t = T[lang]
    M = lambda v: fmt_money(v, lang, a.currency)
    P = lambda v, d=0: fmt_pct(v, lang, d)
    N = lambda v, d=1: "-" if v is None else fmt_num(v, lang, d)
    R = json.load(open(a.rubric, encoding="utf-8"))
    os.makedirs(os.path.join(a.out, "charts"), exist_ok=True)

    rows = read_table(a.file)
    cols = detect_columns(list(rows[0].keys()), F, json.load(open(a.map, encoding="utf-8")) if a.map else None)
    if "month" not in cols:
        raise SystemExit(f"Coluna de mês não encontrada: {list(rows[0].keys())}")
    data = []
    for r in rows:
        mv = str(r[cols["month"]]).strip()
        d = parse_date(mv) or parse_date(mv + "-01") or parse_date("01/" + mv)
        if not d:
            continue
        row = {"m": f"{d.year}-{d.month:02d}"}
        for k in F:
            if k != "month":
                row[k] = parse_money(r.get(cols[k])) if k in cols else None
        if row["gm"] is not None and row["gm"] > 1:
            row["gm"] /= 100
        data.append(row)
    data.sort(key=lambda x: x["m"])
    data = data[-a.months:]
    have = {k: any(x[k] is not None for x in data) for k in F if k != "month"}
    ms = [x["m"] for x in data]
    for x in data:
        x["sm"] = s([x["mkt"], x["sales_cost"]])
        x["cac"] = div(x["sm"], x["new_cust"])
        x["arpa_new"] = div(x["new_mrr"], x["new_cust"])
        gm = x["gm"] if x["gm"] is not None else None
        x["payback"] = div(x["cac"], (x["arpa_new"] or 0) * gm) if gm and x["arpa_new"] else None
        x["net_new"] = s([x["new_mrr"], x["exp_mrr"], -(x["churn_mrr"] or 0) if x["churn_mrr"] is not None else None])

    def window(xs):
        sm, nc, nm = s([x["sm"] for x in xs]), s([x["new_cust"] for x in xs]), s([x["new_mrr"] for x in xs])
        cac = div(sm, nc)
        arpa = div(nm, nc)
        gm = s([x["gm"] for x in xs if x["gm"] is not None])
        gm = gm / len([x for x in xs if x["gm"] is not None]) if gm is not None else None
        payback = div(cac, (arpa or 0) * gm) if gm and arpa else None
        churn_rate = div(s([x["cust_lost"] for x in xs]), s([x["cust_start"] for x in xs]))  # média mensal de churn de logos
        ltv = div((arpa or 0) * (gm or 0), churn_rate) if churn_rate and arpa and gm else None
        mrr0 = xs[0]["mrr_start"] if xs and xs[0]["mrr_start"] else None
        nrr = None
        if all(x["mrr_start"] for x in xs) and have["exp_mrr"] and have["churn_mrr"]:
            m_ret = [1 + ((x["exp_mrr"] or 0) - (x["churn_mrr"] or 0)) / x["mrr_start"] for x in xs]
            prod = 1.0
            for v in m_ret:
                prod *= v
            nrr = prod ** (12 / len(m_ret))
        growth = None
        if mrr0 and xs[-1]["mrr_start"]:
            end = xs[-1]["mrr_start"] + (xs[-1]["net_new"] or 0)
            growth = (end / mrr0) ** (1 / len(xs)) - 1
        return {"sm": sm, "new_cust": nc, "new_mrr": nm, "cac": cac,
                "cac_mkt": div(s([x["mkt"] for x in xs]), nc), "arpa": arpa, "gm": gm, "payback": payback,
                "logo_churn_m": churn_rate, "ltv": ltv, "ltv_cac": div(ltv, cac), "nrr": nrr, "mrr_growth_m": growth,
                "leads": s([x["leads"] for x in xs]), "opps": s([x["opps"] for x in xs]), "pipe": s([x["pipe"] for x in xs]),
                "pipe_mkt": s([x["pipe_mkt"] for x in xs]), "mkt": s([x["mkt"] for x in xs]),
                "net_new": s([x["net_new"] for x in xs])}

    W = window(data)
    last3, prev3 = window(data[-3:]), window(data[-6:-3]) if len(data) >= 6 else None
    # magic number: (MRR líquido novo do trimestre × 12) ÷ S&M do trimestre anterior
    magic = None
    if len(data) >= 6 and last3["net_new"] is not None and prev3 and prev3["sm"]:
        magic = last3["net_new"] * 12 / prev3["sm"]
    pipe_eff = div(W["pipe"], W["mkt"])
    mkt_share = div(W["pipe_mkt"], W["pipe"])

    rb = R["metrics"]
    sc = {"ltv_cac": lin(W["ltv_cac"], *rb["ltv_cac"]), "payback": lin(W["payback"], *rb["payback_months"]),
          "nrr": lin(W["nrr"], *rb["nrr"]), "magic": lin(magic, *rb["magic_number"]),
          "growth": lin(W["mrr_growth_m"], *rb["mrr_growth_monthly"])}
    wts = R["weights"]
    parts = [(sc[k], wts[k]) for k in sc if sc[k] is not None]
    total = round(sum(v * w for v, w in parts) / sum(w for _, w in parts)) if parts else None
    conf = round(100 * sum(w for _, w in parts) / sum(wts.values()))

    # canais
    chan = None
    if a.channels:
        crow = read_table(a.channels)
        cc = detect_columns(list(crow[0].keys()), CH)
        g = defaultdict(lambda: defaultdict(float))
        keep = set(ms)
        for r in crow:
            mv = str(r.get(cc.get("month"), "")).strip()
            d = parse_date(mv) or parse_date(mv + "-01")
            if d and f"{d.year}-{d.month:02d}" not in keep:
                continue
            ch = str(r.get(cc["channel"], "")).strip() or "-"
            for k in ("spend", "leads", "opps", "cust", "mrr"):
                if k in cc:
                    g[ch][k] += parse_money(r.get(cc[k])) or 0
        tot_sp = sum(v["spend"] for v in g.values()) or 1
        tot_mrr = sum(v["mrr"] for v in g.values()) or 1
        chan = sorted([{"channel": k, **v, "cpl": div(v["spend"], v["leads"]), "cpo": div(v["spend"], v["opps"]),
                        "cac": div(v["spend"], v["cust"]), "share_spend": v["spend"] / tot_sp, "share_mrr": v["mrr"] / tot_mrr}
                       for k, v in g.items()], key=lambda x: -x["spend"])

    metrics = {"months": ms, "window": W, "last3": last3, "prev3": prev3, "magic_number": magic, "pipe_per_spend": pipe_eff,
               "mkt_sourced_share": mkt_share, "scores": sc, "score_total": total, "confidence": conf, "channels": chan,
               "monthly": data, "available": have}
    dump(metrics, os.path.join(a.out, "metrics.json"))

    # gráficos
    chd = os.path.join(a.out, "charts")
    if have["mkt"]:
        C.lines(ms, {t["spend"] + " (marketing + vendas)" if lang == "pt" else t["spend"] + " (marketing + sales)": [x["sm"] or 0 for x in data]},
                os.path.join(chd, "spend.png"), title=t["spend"])
    if have["new_mrr"]:
        C.bars(ms, [x["new_mrr"] or 0 for x in data], os.path.join(chd, "new_mrr.png"), horizontal=False, fmt="{:,.0f}", title=t["new_mrr"])
    if any(x["cac"] for x in data):
        C.lines(ms, {t["cac"]: [x["cac"] or float("nan") for x in data]}, os.path.join(chd, "cac.png"), title=t["cac_trend"])
    if have["new_mrr"] and have["churn_mrr"]:
        C.stacked(ms, {t["new_mrr"]: [x["new_mrr"] or 0 for x in data], "Expansão" if lang == "pt" else "Expansion": [x["exp_mrr"] or 0 for x in data]},
                  os.path.join(chd, "bridge.png"), title=t["mrr_bridge"])
    S = []
    kp = [{"label": t["cac"], "value": M(W["cac"]), "note": f"ARPA novo {M(W['arpa'])}{t['per_month']}"},
          {"label": t["payback"], "value": (N(W["payback"]) + " " + t["months"]) if W["payback"] else "-",
           "status": None if W["payback"] is None else "pass" if W["payback"] <= 12 else "warn" if W["payback"] <= 20 else "fail"},
          {"label": t["ltv_cac"], "value": (N(W["ltv_cac"]) + "x") if W["ltv_cac"] else "-",
           "status": None if W["ltv_cac"] is None else "pass" if W["ltv_cac"] >= 3 else "warn" if W["ltv_cac"] >= 2 else "fail"},
          {"label": t["nrr"], "value": P(W["nrr"]), "status": None if W["nrr"] is None else "pass" if W["nrr"] >= 1.05 else "warn" if W["nrr"] >= 0.95 else "fail"},
          {"label": t["magic"], "value": N(magic, 2) if magic is not None else "-",
           "status": None if magic is None else "pass" if magic >= 0.75 else "warn" if magic >= 0.5 else "fail"},
          {"label": t["growth"], "value": P(W["mrr_growth_m"], 1) + t["per_month"] if W["mrr_growth_m"] is not None else "-"},
          {"label": t["logo_churn"], "value": P(W["logo_churn_m"], 1) + t["per_month"] if W["logo_churn_m"] is not None else "-"},
          {"label": t["mkt_share"], "value": P(mkt_share)}]
    S.append({"title": t["kpis"], "blocks": [{"type": "kpis", "items": kp}, {"type": "scores", "items": [
        {"name": t[k if k != "payback" else "payback"], "score": sc[k]} for k in ("ltv_cac", "payback", "nrr", "magic", "growth")]}]})
    if prev3:
        def row(lbl, k, f):
            a_, b_ = prev3.get(k), last3.get(k)
            dl = "-" if (a_ is None or b_ is None or not a_) else f"{(b_ / a_ - 1) * 100:+.0f}%"
            return [lbl, f(a_), f(b_), dl]
        S.append({"title": t["q"], "blocks": [{"type": "table", "header": [t["metric"], t["prev"], t["last"], t["delta"]], "rows": [
            row(t["spend"], "sm", M), row(t["new_mrr"], "new_mrr", M), row(t["cust"], "new_cust", lambda v: N(v, 0)),
            row(t["cac"], "cac", M), row("Leads", "leads", lambda v: N(v, 0)), row("Oportunidades" if lang == "pt" else "Opportunities", "opps", lambda v: N(v, 0)),
            row("Pipeline", "pipe", M)], "widths": [5, 4, 4, 4]}]})
    blocks = []
    for fn in ("spend.png", "new_mrr.png", "cac.png", "bridge.png"):
        if os.path.exists(os.path.join(chd, fn)):
            blocks.append({"type": "chart", "path": f"charts/{fn}", "width_cm": 15})
    if blocks:
        S.append({"title": t["trend"], "page_break_before": True, "blocks": blocks})
    if have["leads"]:
        hdr = [t["month"], "Leads", "MQL", "SQL", "Opps", t["cust"], "Lead→Opp", "Opp→Cliente" if lang == "pt" else "Opp→Win"]
        S.append({"title": t["funnel"], "blocks": [{"type": "table", "header": hdr, "rows": [
            [x["m"], N(x["leads"], 0), N(x["mql"], 0), N(x["sql"], 0), N(x["opps"], 0), N(x["new_cust"], 0),
             P(div(x["opps"], x["leads"]), 1), P(div(x["new_cust"], x["opps"]))] for x in data],
            "widths": [2, 1.8, 1.8, 1.8, 1.8, 1.8, 3, 3], "size": 8.5}]})
    if chan:
        S.append({"title": t["channels"], "blocks": [{"type": "table", "header": [t["channel"], t["spend"], t["share_spend"], t["cpl"], t["cpo"], t["cac_mkt"], t["share_mrr"]],
                  "rows": [[c["channel"], M(c["spend"]), P(c["share_spend"]), M(c["cpl"]), M(c["cpo"]), M(c["cac"]), P(c["share_mrr"])] for c in chan]
                  + [["**Total**", M(sum(c["spend"] for c in chan)), "100%", "", "", M(W["cac_mkt"]), "100%"]],
                  "widths": [3.4, 2.4, 2, 2.2, 2.4, 2.4, 2.2], "size": 8.5}]})
        C.bars([c["channel"] for c in chan if c["cac"]], [c["cac"] for c in chan if c["cac"]], os.path.join(chd, "cac_canal.png"),
               fmt="{:,.0f}", title=t["cac_mkt"], ref=W["cac_mkt"], ref_label="média" if lang == "pt" else "average")
        S[-1]["blocks"].insert(0, {"type": "chart", "path": "charts/cac_canal.png", "width_cm": 13})
        S[-1]["blocks"].append({"type": "text", "text": t["ch_note"]})
    dump({"sections": S}, os.path.join(a.out, "auto_sections.json"))
    out = {"score_total": total, "confidence": conf, "scores": sc, "window": {k: v for k, v in W.items()}, "magic_number": magic,
           "last3": last3, "prev3": prev3, "pipe_per_spend": pipe_eff, "mkt_sourced_share": mkt_share,
           "channels": [(c["channel"], round(c["spend"]), round(c["cac"] or 0), round(c["share_spend"], 3), round(c["share_mrr"], 3)) for c in chan] if chan else None,
           "missing": [k for k, v in have.items() if not v]}
    print(json.dumps(out, ensure_ascii=False, indent=1, default=str))


if __name__ == "__main__":
    main()
