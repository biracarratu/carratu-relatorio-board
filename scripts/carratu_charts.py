"""Gráficos com a identidade Carratu (matplotlib). Comum às skills do Carratu Growth Kit.

Charts with the Carratu brand palette, shared by the Carratu Growth Kit skills.
"""
from __future__ import annotations

import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
BRAND = os.path.normpath(os.path.join(HERE, "..", "assets", "brand.json"))

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    OK = True
except Exception:  # pragma: no cover
    OK = False


def palette():
    try:
        c = json.load(open(BRAND, encoding="utf-8"))["colors"]
    except Exception:
        c = {"primary": "F43404", "dark": "0A0A0B", "muted": "6B7280", "border": "E5E7EB",
             "pass": "15803D", "warn": "B45309", "fail": "B91C1C"}
    h = lambda k, d="6B7280": "#" + c.get(k, d)
    return {"primary": h("primary"), "dark": h("dark"), "muted": h("muted"), "border": h("border"),
            "pass": h("pass"), "warn": h("warn"), "fail": h("fail"),
            "series": [h("primary"), h("dark"), "#E85D04", h("muted"), "#16A34A", "#7C3AED", "#B45309", "#0EA5E9"]}


def compact(v, _pos=None):
    a = abs(v)
    if a >= 1e6:
        return f"{v / 1e6:.1f}M".replace(".0M", "M")
    if a >= 1e3:
        return f"{v / 1e3:.0f}k"
    return f"{v:.0f}" if float(v).is_integer() else f"{v:.2f}"


def _style(ax, P):
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(P["border"])
    ax.tick_params(colors=P["dark"], labelsize=8.5)
    ax.yaxis.grid(True, color=P["border"], linewidth=0.6)
    ax.set_axisbelow(True)


def _save(fig, path):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    fig.tight_layout()
    fig.savefig(path, dpi=200)
    plt.close(fig)
    return path


def funnel(stages, values, path, title=None, rates=None):
    """Funil: etapa à esquerda, barra centralizada proporcional ao volume, volume e taxa de passagem à direita."""
    if not OK:
        return None
    P = palette()
    n = len(stages)
    fig, ax = plt.subplots(figsize=(7.2, 0.5 * n + 0.9))
    mx = max(values) or 1
    for i, (s, v) in enumerate(zip(stages, values)):
        w = max(v / mx, 0.01)
        y = n - 1 - i
        ax.barh(y, w, left=0.3 + (1 - w) / 2, color=P["primary"] if i == n - 1 else P["dark"], height=0.72)
        ax.text(0.28, y, s, ha="right", va="center", color=P["dark"], fontsize=9, fontweight="bold")
        lab = f"{v:,}".replace(",", ".")
        if rates and i > 0 and rates[i] is not None:
            lab += f"   {rates[i]:.0%}"
        ax.text(1.34, y, lab, ha="left", va="center", color=P["dark"], fontsize=8.5)
    ax.set_xlim(0, 1.75)
    ax.set_ylim(-0.6, n - 0.4)
    ax.axis("off")
    if title:
        ax.set_title(title, fontsize=10, color=P["dark"], loc="left", fontweight="bold")
    return _save(fig, path)


def bars(labels, values, path, title=None, fmt="{:.0f}", horizontal=True, highlight=None, ref=None, ref_label=None):
    if not OK:
        return None
    P = palette()
    n = len(labels)
    fig, ax = plt.subplots(figsize=(7.2, max(2.2, 0.38 * n + 1.0)) if horizontal else (7.2, 3.4))
    colors = [P["primary"] if (highlight and l in highlight) else P["dark"] for l in labels]
    if horizontal:
        y = list(range(n))[::-1]
        ax.barh(y, values, color=colors, height=0.65)
        ax.set_yticks(y)
        ax.set_yticklabels(labels)
        for yy, v in zip(y, values):
            ax.text(v, yy, " " + fmt.format(v), va="center", fontsize=8, color=P["dark"])
        if ref is not None:
            ax.axvline(ref, color=P["muted"], linestyle="--", linewidth=1)
            if ref_label:
                ax.text(ref, n - 0.4, " " + ref_label, color=P["muted"], fontsize=7.5)
        ax.xaxis.grid(True, color=P["border"], linewidth=0.6)
        ax.yaxis.grid(False)
    else:
        ax.bar(labels, values, color=colors)
        if n <= 8:
            for i, v in enumerate(values):
                ax.text(i, v, fmt.format(v), ha="center", va="bottom", fontsize=8)
        else:
            plt.setp(ax.get_xticklabels(), rotation=45, ha="right")
        if ref is not None:
            ax.axhline(ref, color=P["muted"], linestyle="--", linewidth=1)
    _style(ax, P)
    from matplotlib.ticker import FuncFormatter
    if horizontal:
        ax.yaxis.grid(False)
        ax.xaxis.set_major_formatter(FuncFormatter(compact))
    else:
        ax.yaxis.set_major_formatter(FuncFormatter(compact))
    if title:
        ax.set_title(title, fontsize=10, color=P["dark"], loc="left", fontweight="bold")
    return _save(fig, path)


def lines(x, series, path, title=None, ylabel=None, percent=False):
    """series: dict nome -> lista de valores (mesmo tamanho de x)."""
    if not OK:
        return None
    P = palette()
    fig, ax = plt.subplots(figsize=(7.2, 3.2))
    for i, (name, vals) in enumerate(series.items()):
        ax.plot(x, vals, marker="o", markersize=3.5, linewidth=2, color=P["series"][i % len(P["series"])], label=name)
    _style(ax, P)
    from matplotlib.ticker import PercentFormatter, FuncFormatter
    ax.yaxis.set_major_formatter(PercentFormatter(1.0) if percent else FuncFormatter(compact))
    if ylabel:
        ax.set_ylabel(ylabel, fontsize=8.5, color=P["muted"])
    if len(series) > 1:
        ax.legend(frameon=False, fontsize=8, ncol=min(4, len(series)))
    if len(x) > 8:
        plt.setp(ax.get_xticklabels(), rotation=45, ha="right")
    if title:
        ax.set_title(title, fontsize=10, color=P["dark"], loc="left", fontweight="bold")
    return _save(fig, path)


def stacked(x, series, path, title=None, percent=False):
    if not OK:
        return None
    P = palette()
    fig, ax = plt.subplots(figsize=(7.2, 3.2))
    bottom = [0] * len(x)
    for i, (name, vals) in enumerate(series.items()):
        ax.bar(x, vals, bottom=bottom, color=P["series"][i % len(P["series"])], label=name)
        bottom = [b + v for b, v in zip(bottom, vals)]
    _style(ax, P)
    from matplotlib.ticker import PercentFormatter, FuncFormatter
    ax.yaxis.set_major_formatter(PercentFormatter(1.0) if percent else FuncFormatter(compact))
    ax.legend(frameon=False, fontsize=8, ncol=min(4, len(series)))
    if len(x) > 8:
        plt.setp(ax.get_xticklabels(), rotation=45, ha="right")
    if title:
        ax.set_title(title, fontsize=10, color=P["dark"], loc="left", fontweight="bold")
    return _save(fig, path)


def scatter(points, path, title=None, xlabel=None, ylabel=None, quad=None):
    """points: lista de (x, y, rótulo). quad: (x_ref, y_ref) desenha quadrantes."""
    if not OK:
        return None
    P = palette()
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    for x, y, lab in points:
        ax.scatter(x, y, s=40, color=P["primary"])
        ax.annotate(lab, (x, y), textcoords="offset points", xytext=(4, 3), fontsize=7.5, color=P["dark"])
    if quad:
        ax.axvline(quad[0], color=P["muted"], linestyle="--", linewidth=1)
        ax.axhline(quad[1], color=P["muted"], linestyle="--", linewidth=1)
    _style(ax, P)
    if xlabel:
        ax.set_xlabel(xlabel, fontsize=8.5, color=P["muted"])
    if ylabel:
        ax.set_ylabel(ylabel, fontsize=8.5, color=P["muted"])
    if title:
        ax.set_title(title, fontsize=10, color=P["dark"], loc="left", fontweight="bold")
    return _save(fig, path)
