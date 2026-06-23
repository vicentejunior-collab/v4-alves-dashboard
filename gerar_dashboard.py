#!/usr/bin/env python3
"""
gerar_dashboard.py
──────────────────
Lê os .md do repo privado (v4-alves-segundo-cerebro) via API do GitHub,
extrai Performance Atual e Health Score, gera dados.json e faz push de
dados.json + index.html para o repo público (v4-alves-dashboard).

Uso:
    python gerar_dashboard.py

Env vars (mesmo .env do atualizar_segundo_cerebro.py):
    GITHUB_TOKEN        → token com escrita no repo PÚBLICO
    GITHUB_READ_TOKEN   → token com leitura no repo PRIVADO
"""

import os, re, json, base64, urllib.request, urllib.error
from datetime import datetime
from pathlib import Path

# ── Config ────────────────────────────────────────────────────────────
PRIVATE_OWNER  = "vicentejunior-collab"
PRIVATE_REPO   = "v4-alves-segundo-cerebro"
PRIVATE_BRANCH = "main"

PUBLIC_OWNER   = "vicentejunior-collab"
PUBLIC_REPO    = "v4-alves-dashboard"
PUBLIC_BRANCH  = "main"

# Tokens — lidos do .env ou variáveis de ambiente
WRITE_TOKEN    = os.getenv("GITHUB_TOKEN", "")
READ_TOKEN     = os.getenv("GITHUB_READ_TOKEN", "")

# Caminho do index.html (relativo a este script)
SCRIPT_DIR     = Path(__file__).parent
INDEX_HTML     = SCRIPT_DIR / "dashboard" / "index.html"

# ── Client map ────────────────────────────────────────────────────────
# file: nome do .md em clientes/
# name: nome de exibição no dashboard
# hs_nome: campo "nome" no JSON do health score
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

# ── GitHub API ────────────────────────────────────────────────────────
def gh_get_raw(path, token, owner=None, repo=None, branch=None):
    """Fetch file content from GitHub API, returns decoded text or None."""
    o = owner or PRIVATE_OWNER
    r = repo  or PRIVATE_REPO
    b = branch or PRIVATE_BRANCH
    url = f"https://api.github.com/repos/{o}/{r}/contents/{path}?ref={b}"
    req = urllib.request.Request(url, headers={"Authorization": f"token {token}"})
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.load(resp)
            if isinstance(data, dict) and data.get("content"):
                return base64.b64decode(data["content"]).decode("utf-8")
            return None
    except Exception as e:
        print(f"  ⚠️  GET {path}: {e}")
        return None

def gh_list(path, token, owner=None, repo=None, branch=None):
    """List directory contents from GitHub API."""
    o = owner or PRIVATE_OWNER
    r = repo  or PRIVATE_REPO
    b = branch or PRIVATE_BRANCH
    url = f"https://api.github.com/repos/{o}/{r}/contents/{path}?ref={b}"
    req = urllib.request.Request(url, headers={"Authorization": f"token {token}"})
    try:
        with urllib.request.urlopen(req) as resp:
            return json.load(resp)
    except Exception as e:
        print(f"  ⚠️  LIST {path}: {e}")
        return []

def gh_put(path, content_bytes, message, token, owner=None, repo=None, branch=None):
    """Push a file to GitHub, creating or updating."""
    o = owner or PUBLIC_OWNER
    r = repo  or PUBLIC_REPO
    b = branch or PUBLIC_BRANCH
    url = f"https://api.github.com/repos/{o}/{r}/contents/{path}"

    # Get current SHA if file exists (needed for update)
    sha = None
    req_get = urllib.request.Request(url, headers={"Authorization": f"token {token}"})
    try:
        with urllib.request.urlopen(req_get) as resp:
            sha = json.load(resp).get("sha")
    except Exception:
        pass  # File doesn't exist yet — that's fine

    payload = {
        "message": message,
        "content": base64.b64encode(content_bytes).decode("utf-8"),
        "branch": b,
    }
    if sha:
        payload["sha"] = sha

    req = urllib.request.Request(
        url, data=json.dumps(payload).encode("utf-8"), method="PUT",
        headers={"Authorization": f"token {token}", "Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req) as resp:
            d = json.load(resp)
            print(f"  ✅ {path} publicado")
            return True
    except urllib.error.HTTPError as e:
        print(f"  ❌ {path}: {e.read().decode()}")
        return False

# ── Parsing ────────────────────────────────────────────────────────────
def compute_flag(notas):
    """Compute health flag and score % from notas dict."""
    if not notas:
        return "sem-dados", None
    vals = [v for v in notas.values() if v is not None]
    if not vals:
        return "sem-dados", None
    avg = sum(vals) / len(vals)
    pct = round((avg / 2) * 100)
    if avg >= 1.6:
        return "verde", pct
    elif avg >= 0.8:
        return "amarelo", pct
    else:
        return "vermelho", pct

def parse_meta(md_text):
    """Extract ## Performance Atual metrics from markdown."""
    if not md_text:
        return None
    m = re.search(r"## Performance Atual(.*?)(?=\n## |\Z)", md_text, re.DOTALL)
    if not m:
        return None
    block = m.group(1)

    def pick(label):
        rx = re.compile(
            r"\|\s*" + re.escape(label) + r"\s*\|\s*([^|\n]+)\s*\|",
            re.IGNORECASE
        )
        match = rx.search(block)
        if not match:
            return None
        v = re.sub(r"[^\x00-\x7F]", "", match.group(1)).strip()
        return None if v in ("", "—", "-") else v

    period_m = re.search(r"_Período:\s*([^_\n]+)_", block)
    period = period_m.group(1).strip() if period_m else None

    # Top 2 campaigns
    campaigns = []
    camp_m = re.search(r"### Por Campanha(.*?)(?=\n###|\Z)", block, re.DOTALL)
    if camp_m:
        rows = re.findall(
            r"\|\s*(\[.*?\][^|]*)\|\s*R\$\s*([\d.,]+)",
            camp_m.group(1)
        )
        for name, spend in rows[:2]:
            clean = re.sub(r"\s+", " ", name.strip())[:35]
            campaigns.append({"name": clean, "spend": f"R$ {spend}"})

    return {
        "period":     period,
        "invest":     pick("Investimento"),
        "impressoes": pick("Impressoes") or pick("Impress\u00f5es"),
        "cliques":    pick("Cliques"),
        "ctr":        pick("CTR"),
        "cpm":        pick("CPM"),
        "cpc":        pick("CPC"),
        "conversoes": pick("Convers\u00f5es (Total)") or pick("Conversoes (Total)"),
        "cpl":        pick("CPL"),
        "roas":       pick("ROAS"),
        "campaigns":  campaigns,
    }

# ── Load Health Score ──────────────────────────────────────────────────
def load_health_score():
    """Load latest health score JSON from historico/ directory."""
    files = gh_list("health-score/historico", READ_TOKEN)
    jsons = sorted(
        [f for f in files if f["name"].endswith(".json")],
        key=lambda f: f["name"],
        reverse=True
    )
    if not jsons:
        print("  ⚠️  Nenhum JSON de health score encontrado")
        return {}, "N/A"

    latest = jsons[0]["name"]
    print(f"  📊 Health Score: {latest}")
    raw = gh_get_raw(f"health-score/historico/{latest}", READ_TOKEN)
    if not raw:
        return {}, "N/A"

    data = json.loads(raw)
    hs_map = {c["nome"]: c for c in data.get("clientes", [])}
    return hs_map, latest.replace(".json", "")

# ── Main ───────────────────────────────────────────────────────────────
def main():
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"\n[{ts}] ── Gerando dashboard ──────────────────────────")

    if not WRITE_TOKEN:
        print("❌  GITHUB_TOKEN não definido. Configure no .env")
        return
    if not READ_TOKEN:
        print("❌  GITHUB_READ_TOKEN não definido. Configure no .env")
        return

    # 1. Load health score
    print("\n1. Carregando Health Score...")
    hs_map, hs_date = load_health_score()

    # 2. Load each client .md and parse
    print("\n2. Lendo arquivos de clientes...")
    output = {
        "gerado_em": datetime.now().strftime("%Y-%m-%d"),
        "health_score_data": hs_date,
        "clientes": [],
        "churns": [],
    }

    for c in CLIENT_MAP:
        hs = hs_map.get(c["hs_nome"])

        # Churn check
        if hs and hs.get("classificacao") == "CHURN":
            output["churns"].append({
                "name": c["name"],
                "squad": hs.get("squad", "—"),
                "churn_date": hs.get("churn", ""),
            })
            print(f"  ✗  {c['name']} — CHURN")
            continue

        # Health flag
        flag, score = "sem-dados", None
        squad, fee = "—", None
        if hs and hs.get("notas"):
            flag, score = compute_flag(hs["notas"])
            squad = hs.get("squad", "—")
            fee   = hs.get("fee")

        # Meta Ads data
        md = gh_get_raw(f"clientes/{c['file']}.md", READ_TOKEN)
        meta = parse_meta(md) if md else None

        icon = {"verde": "🟢", "amarelo": "🟡", "vermelho": "🔴"}.get(flag, "⚪")
        meta_label = "meta ✓" if meta and meta.get("invest") else "sem meta"
        print(f"  {icon}  {c['name']} ({squad}) — {meta_label}")

        output["clientes"].append({
            "name":  c["name"],
            "file":  c["file"],
            "squad": squad,
            "fee":   fee,
            "flag":  flag,
            "score": score,
            "meta":  meta,
        })

    # 3. Push dados.json
    print("\n3. Publicando no repo público...")
    dados_bytes = json.dumps(output, ensure_ascii=False, indent=2).encode("utf-8")
    gh_put("dados.json", dados_bytes, f"dados: atualização {output['gerado_em']}", WRITE_TOKEN)

    # 4. Push index.html (só se existir localmente)
    if INDEX_HTML.exists():
        html_bytes = INDEX_HTML.read_bytes()
        gh_put("index.html", html_bytes, f"dashboard: atualização {output['gerado_em']}", WRITE_TOKEN)
    else:
        print(f"  ⚠️  {INDEX_HTML} não encontrado — index.html não atualizado")

    print(f"\n✅  Dashboard atualizado!")
    print(f"    {len(output['clientes'])} clientes · {len(output['churns'])} churns")
    print(f"    URL: https://{PUBLIC_OWNER}.github.io/{PUBLIC_REPO}/\n")


if __name__ == "__main__":
    main()
