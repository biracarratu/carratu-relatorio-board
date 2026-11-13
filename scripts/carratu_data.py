"""Leitura e normalização de exports de CRM (HubSpot, Pipedrive, RD Station CRM, Salesforce, Ploomes,
Agendor, planilhas). Comum às skills do Carratu Growth Kit.

CRM export reader and normalizer shared by the Carratu Growth Kit skills.
"""
from __future__ import annotations

import csv
import io
import json
import re
import statistics
import unicodedata
from datetime import datetime, date

# Sinônimos de colunas (comparados sem acento, minúsculos, sem pontuação).
DEAL_FIELDS = {
    "id": ["id", "deal id", "record id", "id do negocio", "negocio id", "id negocio", "opportunity id", "id da oportunidade", "deal_id"],
    "name": ["deal name", "nome do negocio", "negocio", "titulo", "title", "opportunity name", "nome da oportunidade", "nome", "name"],
    "created": ["create date", "created", "created at", "data de criacao", "criado em", "deal created", "add time",
                "negocio criado em", "data criacao", "created date", "data de cadastro", "abertura"],
    "closed": ["close date", "closed", "closed at", "data de fechamento", "fechado em", "won time", "lost time", "close time",
               "data fechamento", "data de conclusao", "data de ganho", "data de perda", "closed date", "fechamento"],
    "stage": ["deal stage", "stage", "etapa", "etapa do negocio", "fase", "estagio", "pipeline stage", "etapa do funil", "stage name"],
    "status": ["status", "situacao", "resultado", "won/lost", "is won", "estado", "deal status"],
    "amount": ["amount", "valor", "deal value", "value", "valor do negocio", "valor total", "receita", "mrr", "acv",
               "valor (r$)", "amount in company currency", "valor estimado"],
    "owner": ["deal owner", "owner", "proprietario", "responsavel", "vendedor", "dono do negocio", "usuario", "opportunity owner", "closer"],
    "source": ["source", "original source", "origem", "fonte", "canal", "lead source", "fonte original", "origem do lead", "channel", "midia"],
    "loss_reason": ["closed lost reason", "lost reason", "motivo de perda", "motivo da perda", "loss reason", "motivo"],
    "segment": ["segment", "segmento", "industry", "setor", "vertical", "industria", "ramo"],
    "company_size": ["company size", "porte", "numero de funcionarios", "number of employees", "employees", "funcionarios", "tamanho da empresa"],
    "region": ["region", "regiao", "estado (uf)", "uf", "state", "pais", "country", "cidade", "city"],
    "company": ["company", "empresa", "organizacao", "organization", "account name", "conta", "associated company", "cliente"],
    "pipeline": ["pipeline", "funil"],
}
WON = {"won", "ganho", "ganha", "closed won", "closedwon", "fechado ganho", "fechada ganha", "vendido", "venda", "true",
       "1", "sim", "yes", "ganhou", "convertido", "contrato assinado"}
LOST = {"lost", "perdido", "perdida", "closed lost", "closedlost", "fechado perdido", "fechada perdida", "false", "0",
        "nao", "no", "perdeu", "descartado", "cancelado"}


def strip(s):
    s = unicodedata.normalize("NFD", str(s or "")).encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", re.sub(r"[_\-]+", " ", s.lower())).strip()


def read_table(path):
    """Lê CSV (detecta separador e codificação) ou XLSX. Retorna lista de dicts."""
    if path.lower().endswith((".xlsx", ".xlsm", ".xls")):
        try:
            import openpyxl
        except ImportError:
            raise SystemExit("pip install openpyxl --break-system-packages")
        wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
        ws = wb.worksheets[0]
        rows = list(ws.iter_rows(values_only=True))
        hdr = [str(h or "").strip() for h in rows[0]]
        return [{hdr[i]: ("" if v is None else v) for i, v in enumerate(r) if i < len(hdr)} for r in rows[1:]
                if any(v not in (None, "") for v in r)]
    raw = open(path, "rb").read()
    for enc in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            text = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    sample = text[:20000]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
        sep = dialect.delimiter
    except csv.Error:
        sep = ";" if sample.count(";") > sample.count(",") else ","
    rd = csv.DictReader(io.StringIO(text), delimiter=sep)
    return [{(k or "").strip(): (v or "").strip() for k, v in r.items()} for r in rd if any((v or "").strip() for v in r.values())]


def detect_columns(headers, fields=DEAL_FIELDS, override=None):
    """Mapeia campos canônicos para colunas do arquivo. override: {campo: coluna}."""
    override = override or {}
    hn = {h: strip(h) for h in headers}
    out = {}
    used = set()
    for f, syns in fields.items():
        if f in override:
            out[f] = override[f]
            used.add(override[f])
            continue
        best = None
        for s in syns:  # 1) igual
            for h, n in hn.items():
                if h not in used and n == s:
                    best = h
                    break
            if best:
                break
        if not best:  # 2) contém
            for s in syns:
                if len(s) < 4:
                    continue
                for h, n in hn.items():
                    if h not in used and s in n:
                        best = h
                        break
                if best:
                    break
        if best:
            out[f] = best
            used.add(best)
    return out


DATE_FMTS = ["%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M:%S", "%d/%m/%Y", "%d/%m/%Y %H:%M",
             "%d/%m/%Y %H:%M:%S", "%d/%m/%y", "%d-%m-%Y", "%m/%d/%Y", "%m/%d/%Y %H:%M", "%Y/%m/%d", "%d.%m.%Y"]


def parse_date(v, dayfirst=True):
    if v in (None, ""):
        return None
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    s = str(v).strip()
    s = re.sub(r"(\.\d+)?(Z|[+-]\d{2}:?\d{2})$", "", s)
    fmts = DATE_FMTS if dayfirst else [f for f in DATE_FMTS if f.startswith("%m")] + DATE_FMTS
    for f in fmts:
        try:
            return datetime.strptime(s, f).date()
        except ValueError:
            continue
    if re.fullmatch(r"\d{10,13}", s):  # epoch
        n = int(s)
        return datetime.utcfromtimestamp(n / 1000 if n > 1e11 else n).date()
    return None


def parse_money(v):
    if v in (None, ""):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = re.sub(r"[^\d,.\-]", "", str(v))
    if not s or s in "-.,":
        return None
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".") if s.rfind(",") > s.rfind(".") else s.replace(",", "")
    elif "," in s:
        parts = s.split(",")
        s = s.replace(",", ".") if len(parts[-1]) in (1, 2) else s.replace(",", "")
    elif s.count(".") > 1 or (s.count(".") == 1 and len(s.split(".")[-1]) == 3 and len(s) > 4):
        s = s.replace(".", "")
    try:
        return float(s)
    except ValueError:
        return None


def status_of(row_status, stage, won_stages=(), lost_stages=()):
    st = strip(row_status)
    sg = strip(stage)
    if sg and sg in [strip(x) for x in won_stages]:
        return "won"
    if sg and sg in [strip(x) for x in lost_stages]:
        return "lost"
    if st in WON:
        return "won"
    if st in LOST:
        return "lost"
    for probe in (st, sg):
        if not probe:
            continue
        if re.search(r"\b(won|ganh|fechado ganho|closed won|vendid)", probe):
            return "won"
        if re.search(r"\b(lost|perd|closed lost|descart|cancel)", probe):
            return "lost"
    return "open"


def median(xs):
    xs = [x for x in xs if x is not None]
    return statistics.median(xs) if xs else None


def mean(xs):
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else None


def pctile(xs, p):
    xs = sorted(x for x in xs if x is not None)
    if not xs:
        return None
    k = (len(xs) - 1) * p
    f = int(k)
    c = min(f + 1, len(xs) - 1)
    return xs[f] + (xs[c] - xs[f]) * (k - f)


def wilson(k, n, z=1.96):
    """Intervalo de confiança de Wilson (95%) para uma proporção."""
    if not n:
        return (None, None)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    m = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5) / d
    return (max(0.0, c - m), min(1.0, c + m))


# ------------------------------------------------------------- formatação
def fmt_money(v, lang="pt", cur=None):
    if v is None:
        return "-"
    cur = cur or ("R$" if lang == "pt" else "$")
    a = abs(v)
    if lang == "pt":
        if a >= 1e6:
            s = f"{v / 1e6:.1f} mi".replace(".", ",")
        elif a >= 1e3:
            s = f"{v / 1e3:.1f} mil".replace(".", ",")
        else:
            s = f"{v:.0f}"
        return f"{cur} {s}"
    if a >= 1e6:
        return f"{cur}{v / 1e6:.1f}M"
    if a >= 1e3:
        return f"{cur}{v / 1e3:.1f}k"
    return f"{cur}{v:.0f}"


def fmt_pct(v, lang="pt", d=0):
    if v is None:
        return "-"
    s = f"{v * 100:.{d}f}%"
    return s.replace(".", ",") if lang == "pt" else s


def fmt_num(v, lang="pt", d=0):
    if v is None:
        return "-"
    s = f"{v:,.{d}f}"
    if lang == "pt":
        s = s.replace(",", "§").replace(".", ",").replace("§", ".")
    return s


def fmt_days(v, lang="pt"):
    if v is None:
        return "-"
    return f"{v:.0f} dias" if lang == "pt" else f"{v:.0f} days"


def dump(obj, path):
    def conv(o):
        if isinstance(o, (date, datetime)):
            return o.isoformat()
        raise TypeError(type(o))
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1, default=conv)
