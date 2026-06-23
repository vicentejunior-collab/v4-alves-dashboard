#!/usr/bin/env python3
"""
gerar_dashboard.py v2
─────────────────────
Lê os .md do repo privado, extrai Performance Atual (semanal) e
Performance Mensal, gera dados.json e faz push para o repo público.

Env vars:
    GITHUB_TOKEN        → escrita no repo público
    GITHUB_READ_TOKEN   → leitura no repo privado
"""

import os, re, json, base64, urllib.request, urllib.error
from datetime import datetime
from pathlib import Path

PRIVATE_OWNER  = "vicentejunior-collab"
PRIVATE_REPO   = "v4-alves-segundo-cerebro"
PRIVATE_BRANCH = "main"
PUBLIC_OWNER   = "vicentejunior-collab"
PUBLIC_REPO    = "v4-alves-dashboard"
PUBLIC_BRANCH  = "main"

WRITE_TOKEN = os.getenv("GITHUB_TOKEN", "")
READ_TOKEN  = os.getenv("GITHUB_READ_TOKEN", "")
SCRIPT_DIR  = Path(__file__).parent
INDEX_HTML  = SCRIPT_DIR / "dashboard" / "index.html"

CLIENT_MAP = [
    {"file": "travel-rock",          "name": "Travel Rock",              "hs_nome": "Travel Rock"},
    {"file": "farmacia-descontao",   "name": "Farmácia Descontão",       "hs_nome": "Farmacia Descontao"},
    {"file": "ventania",             "name": "Ventania / Marynga",       "hs_nome": "Marynga Motos (Ventania)"},
    {"file": "ethereal",             "name": "Éthéreal",                 "hs_nome": "Ethereal"},
    {"file": "parcelando-tudo",      "name": "Parcelando Tudo",          "hs_nome": "Parcelando Tudo"},
    {"file": "grupo-obara",          "name": "Grupo Obará",              "hs_nome": "Obara"},
    {"file": "vitrinni",             "name": "Vitrinni",                 "hs_nome": "Vitrinni Lounge"},
    {"file": "terra-vitta",          "name": "Terra Vitta",              "hs_nome": "Terra Vitta"},
    {"file": "uniao-vida",           "name": "União Vida",               "hs_nome": "Uniao Vida"},
    {"file": "instituto-lazarin",    "name": "Instituto Lazarin",        "hs_nome": "Inst. Lazarin"},
    {"file": "fc-servicos",          "name": "F&C Serviços",             "hs_nome": "F&C Servicos"},
    {"file": "fc-group-app",         "name": "F&C Group App",            "hs_nome": "F&C Group"},
    {"file": "uberhaus-rp",          "name": "Uberhaus RP",              "hs_nome": "Uberhaus RP"},
    {"file": "rede-representacoes",  "name": "Rede Representações",      "hs_nome": "Rede Representacoes"},
    {"file": "clinica-phoenix",      "name": "Clínica Phoenix",          "hs_nome": "Clinica Phoenix"},
    {"file": "higilife",             "name": "HigiLife",                 "hs_nome": "Higilife"},
    {"file": "cafe-mineiro",         "name": "Café Mineiro",             "hs_nome": "Cafe Mineiro"},
    {"file": "papelaria-home-office","name": "Papelaria Home & Office",  "hs_nome": "Home & Office"},
    {"file": "condal-beauty",        "name": "Condal Beauty",            "hs_nome": "Condal"},
    {"file": "ma-producoes-rabin",   "name": "M.A Produções Rabin",      "hs_nome": "M.A Producoes Rabin"},
    {"file": "ma-producoes-marrom",  "name": "M.A Produções Marrom",     "hs_nome": "M.A Producoes Marrom"},
    {"file": "fazenda-vale-imperial","name": "Fazenda Vale Imperial",    "hs_nome": "Fazenda Vale Imperial"},
    {"file": "empadinhas",           "name": "Empadinhas",               "hs_nome": "Empadinhas"},
    # ── Adicione novos clientes aqui ──
]

# ── GitHub API ──────────────────────────────────────────────────────
def gh_get_raw(path, token, owner=None, repo=None, branch=None):
    o, r, b = owner or PRIVATE_OWNER, repo or PRIVATE_REPO, branch or PRIVATE_BRANCH
    url = f"https://api.github.com/repos/{o}/{r}/contents/{path}?ref={b}"
    req = urllib.request.Request(url, headers={"Authorization": f"token {token}"})
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.load(resp)
            if isinstance(data, dict) and data.get("content"):
                return base64.b64decode(data["content"]).decode("utf-8")
    except Exception as e:
        print(f"  ⚠️  GET {path}: {e}")
    return None

def gh_list(path, token, owner=None, repo=None, branch=None):
    o, r, b = owner or PRIVATE_OWNER, repo or PRIVATE_REPO, branch or PRIVATE_BRANCH
    url = f"https://api.github.com/repos/{o}/{r}/contents/{path}?ref={b}"
    req = urllib.request.Request(url, headers={"Authorization": f"token {token}"})
    try:
        with urllib.request.urlopen(req) as resp:
            return json.load(resp)
    except Exception as e:
        print(f"  ⚠️  LIST {path}: {e}")
    return []

def gh_put(path, content_bytes, message, token, owner=None, repo=None, branch=None):
    o, r, b = owner or PUBLIC_OWNER, repo or PUBLIC_REPO, branch or PUBLIC_BRANCH
    url = f"https://api.github.com/repos/{o}/{r}/contents/{path}"
    sha = None
    try:
        with urllib.request.urlopen(
            urllib.request.Request(url, headers={"Authorization": f"token {token}"})
        ) as resp:
            sha = json.load(resp).get("sha")
    except Exception:
        pass
    payload = {"message": message, "content": base64.b64encode(content_bytes).decode(), "branch": b}
    if sha:
        payload["sha"] = sha
    req = urllib.request.Request(url, data=json.dumps(payload).encode(), method="PUT",
        headers={"Authorization": f"token {token}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req):
            print(f"  ✅ {path} publicado")
            return True
    except urllib.error.HTTPError as e:
        print(f"  ❌ {path}: {e.read().decode()[:200]}")
        return False

# ── Parsing ─────────────────────────────────────────────────────────
def compute_flag(notas):
    if not notas: return "sem-dados", None
    vals = [v for v in notas.values() if v is not None]
    if not vals: return "sem-dados", None
    avg = sum(vals) / len(vals)
    pct = round((avg / 2) * 100)
    return ("verde", pct) if avg >= 1.6 else ("amarelo", pct) if avg >= 0.8 else ("vermelho", pct)

def parse_block(block):
    """Parse a metrics table block into a dict."""
    if not block:
        return None

    def pick(label):
        rx = re.compile(r"\|[^|]*" + re.escape(label) + r"\s*\|\s*([^|\n]+)\s*\|", re.IGNORECASE)
        match = rx.search(block)
        if not match: return None
        v = re.sub(r"[^\x00-\x7F]", "", match.group(1)).strip()
        return None if v in ("", "—", "-") else v

    # Period — try both formats
    period_m = re.search(r"_Período:\s*([^_\n]+)_", block) or re.search(r"_([\w/]+\s*—[^\n_]+)_", block)
    period = period_m.group(1).strip() if period_m else None

    # Top 2 campaigns (only in Atual block)
    campaigns = []
    camp_m = re.search(r"### Por Campanha(.*?)(?=\n###|\Z)", block, re.DOTALL)
    if camp_m:
        rows = re.findall(r"\|\s*(\[.*?\][^|]*)\|\s*R\$\s*([\d.,]+)", camp_m.group(1))
        for name, spend in rows[:2]:
            campaigns.append({"name": re.sub(r"\s+", " ", name.strip())[:35], "spend": f"R$ {spend}"})

    result = {
        "period":     period,
        "invest":     pick("Investimento"),
        "impressoes": pick("Impressões") or pick("Impressoes"),
        "cliques":    pick("Cliques"),
        "ctr":        pick("CTR"),
        "cpm":        pick("CPM"),
        "cpc":        pick("CPC"),
        "conversoes": pick("Conversões (Total)") or pick("Conversoes (Total)"),
        "cpl":        pick("CPL"),
        "roas":       pick("ROAS"),
        "campaigns":  campaigns,
    }
    # Return None if no real data
    if not any(v for k, v in result.items() if k not in ("period", "campaigns")):
        return None
    return result

def parse_meta_full(md_text):
    """Extract both Atual (semanal) and Mensal blocks."""
    if not md_text:
        return None, None

    atual_m = re.search(r"## Performance Atual(.*?)(?=\n## |\Z)", md_text, re.DOTALL)
    mensal_m = re.search(r"## Performance Mensal(.*?)(?=\n## |\Z)", md_text, re.DOTALL)

    atual  = parse_block(atual_m.group(1) if atual_m else "")
    mensal = parse_block(mensal_m.group(1) if mensal_m else "")

    return atual, mensal

# ── Health Score ────────────────────────────────────────────────────
def load_health_score():
    files = gh_list("health-score/historico", READ_TOKEN)
    jsons = sorted([f for f in files if f["name"].endswith(".json")],
                   key=lambda f: f["name"], reverse=True)
    if not jsons:
        return {}, "N/A"
    latest = jsons[0]["name"]
    print(f"  📊 Health Score: {latest}")
    raw = gh_get_raw(f"health-score/historico/{latest}", READ_TOKEN)
    if not raw: return {}, "N/A"
    data = json.loads(raw)
    return {c["nome"]: c for c in data.get("clientes", [])}, latest.replace(".json", "")

# ── Main ────────────────────────────────────────────────────────────
def main():
    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] ── Gerando dashboard v2 ──────────")

    if not WRITE_TOKEN: print("❌  GITHUB_TOKEN não definido"); return
    if not READ_TOKEN:  print("❌  GITHUB_READ_TOKEN não definido"); return

    print("\n1. Carregando Health Score...")
    hs_map, hs_date = load_health_score()

    print("\n2. Lendo arquivos de clientes...")
    output = {
        "gerado_em": datetime.now().strftime("%Y-%m-%d"),
        "health_score_data": hs_date,
        "clientes": [],
        "churns": [],
    }

    for c in CLIENT_MAP:
        hs = hs_map.get(c["hs_nome"])

        if hs and hs.get("classificacao") == "CHURN":
            output["churns"].append({"name": c["name"], "squad": hs.get("squad","—"), "churn_date": hs.get("churn","")})
            print(f"  ✗  {c['name']} — CHURN")
            continue

        flag, score, squad, fee = "sem-dados", None, "—", None
        if hs and hs.get("notas"):
            flag, score = compute_flag(hs["notas"])
            squad, fee = hs.get("squad","—"), hs.get("fee")

        md = gh_get_raw(f"clientes/{c['file']}.md", READ_TOKEN)
        atual, mensal = parse_meta_full(md)

        icon = {"verde":"🟢","amarelo":"🟡","vermelho":"🔴"}.get(flag,"⚪")
        has = ("sem✓" if atual else "sem meta") + (" | men✓" if mensal else "")
        print(f"  {icon}  {c['name']} ({squad}) — {has}")

        output["clientes"].append({
            "name": c["name"], "file": c["file"],
            "squad": squad, "fee": fee,
            "flag": flag, "score": score,
            "meta_semanal": atual,
            "meta_mensal":  mensal,
        })

    print("\n3. Publicando no repo público...")
    dados_bytes = json.dumps(output, ensure_ascii=False, indent=2).encode("utf-8")
    gh_put("dados.json", dados_bytes, f"dados: {output['gerado_em']}", WRITE_TOKEN)

    if INDEX_HTML.exists():
        gh_put("index.html", INDEX_HTML.read_bytes(), f"dashboard: {output['gerado_em']}", WRITE_TOKEN)
    else:
        print(f"  ⚠️  {INDEX_HTML} não encontrado")

    print(f"\n✅  Done! {len(output['clientes'])} clientes · {len(output['churns'])} churns")
    print(f"    https://{PUBLIC_OWNER}.github.io/{PUBLIC_REPO}/\n")

if __name__ == "__main__":
    main()
