#!/usr/bin/env python3
"""Base eleitoral — Anderson da Academia (Divinópolis/MG, 2024, 1º turno, vereador).

Lê os arquivos oficiais do TSE em tse_bruto/, filtra Divinópolis, liga seção →
local de votação → bairro, calcula os indicadores, confere as somas contra os
totais oficiais e gera a página "Base eleitoral" com os dados embutidos.

Uso:  python3 pipeline.py [tse_bruto] [saida]
Só usa a biblioteca padrão do Python 3.9+.
"""
import csv, io, json, re, sys, unicodedata, zipfile
from collections import defaultdict
from datetime import date
from pathlib import Path

AQUI = Path(__file__).resolve().parent
BRUTO = Path(sys.argv[1] if len(sys.argv) > 1 else "tse_bruto")
SAIDA = Path(sys.argv[2] if len(sys.argv) > 2 else ".")
DADOS = SAIDA / "dados_divinopolis"
MUNICIPIO = "DIVINOPOLIS"
CARGO_VEREADOR = "13"
TURNO = "1"
ESPECIAIS = {"95": "Branco", "96": "Nulo", "97": "Anulado (apuração em separado)", "98": "Anulado"}
ELEITO_RX = re.compile(r"^ELEITO")

csv.field_size_limit(10**9)


def sem_acento(s):
    s = unicodedata.normalize("NFD", str(s or ""))
    return "".join(c for c in s if unicodedata.category(c) != "Mn").upper().strip()


def ler(padrao):
    """Itera as linhas (dict) dos CSVs que casam com o padrão, dentro ou fora de .zip."""
    achados = sorted(BRUTO.glob("*"))
    rx = re.compile(padrao, re.I)
    usados = []
    for p in achados:
        if p.suffix.lower() == ".zip":
            with zipfile.ZipFile(p) as z:
                for n in z.namelist():
                    if n.lower().endswith(".csv") and rx.search(Path(n).name):
                        usados.append(f"{p.name}:{n}")
                        with z.open(n) as f:
                            yield from csv.DictReader(io.TextIOWrapper(f, encoding="latin-1", newline=""), delimiter=";")
        elif p.suffix.lower() == ".csv" and rx.search(p.name):
            usados.append(p.name)
            with open(p, encoding="latin-1", newline="") as f:
                yield from csv.DictReader(f, delimiter=";")
    if not usados:
        raise FileNotFoundError(f"Nenhum arquivo em {BRUTO}/ casa com {padrao!r}")
    ARQUIVOS_LIDOS.extend(usados)


ARQUIVOS_LIDOS = []


def col(row, *nomes, padrao=""):
    for n in nomes:
        if n in row and row[n] not in (None, ""):
            return row[n]
    return padrao


def num(v):
    try:
        return int(str(v).strip() or 0)
    except ValueError:
        return 0


def eh_divinopolis(r):
    return sem_acento(col(r, "NM_MUNICIPIO", "NM_UE")) == MUNICIPIO and col(r, "SG_UF") in ("MG", "")


def salvar_csv(caminho, linhas, campos=None):
    caminho.parent.mkdir(parents=True, exist_ok=True)
    linhas = list(linhas)
    campos = campos or (list(linhas[0].keys()) if linhas else [])
    with open(caminho, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=campos, delimiter=";", extrasaction="ignore")
        w.writeheader()
        w.writerows(linhas)


# ---------------------------------------------------------------- ETAPA 2: filtrar
def filtrar():
    sec, det, loc, mz = [], [], [], []
    codigos, geracao = set(), set()
    for r in ler(r"^votacao_secao_2024_MG\.csv$"):
        if eh_divinopolis(r) and r.get("NR_TURNO") == TURNO and r.get("CD_CARGO") == CARGO_VEREADOR:
            sec.append(r); codigos.add(r["CD_MUNICIPIO"]); geracao.add(col(r, "DT_GERACAO"))
    if not sec:
        raise SystemExit("Nenhuma linha de Divinópolis/vereador/1º turno em votacao_secao_2024_MG.")
    for r in ler(r"^detalhe_votacao_secao_2024_MG\.csv$"):
        if r.get("CD_MUNICIPIO") in codigos and r.get("NR_TURNO") == TURNO and r.get("CD_CARGO") == CARGO_VEREADOR:
            det.append(r)
    for r in ler(r"^eleitorado_local_votacao_2024\.csv$"):
        if r.get("CD_MUNICIPIO") in codigos and col(r, "NR_TURNO", padrao=TURNO) == TURNO:
            loc.append(r)
    try:
        for r in ler(r"^votacao_candidato_munzona_2024_MG\.csv$"):
            if r.get("CD_MUNICIPIO") in codigos and r.get("NR_TURNO") == TURNO and r.get("CD_CARGO") == CARGO_VEREADOR:
                mz.append(r)
    except FileNotFoundError:
        pass
    salvar_csv(DADOS / "votacao_secao_vereador.csv", sec)
    salvar_csv(DADOS / "detalhe_apuracao_secao_vereador.csv", det)
    salvar_csv(DADOS / "eleitorado_local_votacao.csv", loc)
    if mz:
        salvar_csv(DADOS / "votacao_candidato_munzona_vereador.csv", mz)
    return sec, det, loc, mz, codigos, geracao


# ---------------------------------------------------------------- ETAPA 3: geografia
ABREV = [(r"\bJD\.?\b", "JARDIM"), (r"\bVL\.?\b", "VILA"), (r"\bSTA\.?\b", "SANTA"), (r"\bSTO\.?\b", "SANTO"),
         (r"\bS\.\s*", "SAO "), (r"\bN\.?\s*SRA\.?\b", "NOSSA SENHORA"), (r"\bSRA\.?\b", "SENHORA"),
         (r"\bDR\.?\b", "DOUTOR"), (r"\bPE\.?\b", "PADRE"), (r"\bCONJ\.?\b", "CONJUNTO"), (r"\bRES\.?\b", "RESIDENCIAL"),
         (r"\bPQ\.?\b", "PARQUE"), (r"\bSEN\.?\b", "SENADOR"), (r"\bPRES\.?\b", "PRESIDENTE")]


def chave_bairro(s):
    k = sem_acento(s)
    k = re.sub(r"[^\w\s.]", " ", k)
    for a, b in ABREV:
        k = re.sub(a, b, k)
    k = re.sub(r"^(BAIRRO|B\.)\s+", "", k)
    return re.sub(r"\s+", " ", k.replace(".", " ")).strip()


def normalizar_bairros(nomes_tse):
    """Casa cada nome do TSE com a BAIRROS_DIV por igualdade exata após tirar acento, caixa e
    expandir abreviações padronizadas. Sem casamento aproximado: o que não casar fica 'Não mapeado'."""
    ref = json.loads((AQUI / "referencia" / "bairros_div.json").read_text(encoding="utf-8"))
    idx = {}
    for b in ref:
        idx.setdefault(chave_bairro(b), b)
    corr = {}
    for n in nomes_tse:
        k = chave_bairro(n)
        if k in idx:
            corr[n] = (idx[k], "exato" if sem_acento(n) == sem_acento(idx[k]) else "normalizado")
        else:
            corr[n] = ("Não mapeado", "sem correspondência")
    return corr


def coord(v):
    try:
        x = float(str(v).replace(",", "."))
    except ValueError:
        return None
    return None if x in (0.0, -1.0) or abs(x) > 180 else x


# ---------------------------------------------------------------- ETAPA 4: análise
def main():
    sec, det, loc, mz, codigos, geracao = filtrar()

    locais = {}
    for r in loc:
        k = (r["NR_ZONA"], r["NR_LOCAL_VOTACAO"])
        if k not in locais:
            locais[k] = dict(zona=r["NR_ZONA"], nr_local=r["NR_LOCAL_VOTACAO"], nome=col(r, "NM_LOCAL_VOTACAO"),
                             endereco=col(r, "DS_ENDERECO"), bairro_tse=col(r, "NM_BAIRRO").strip(),
                             lat=coord(col(r, "NR_LATITUDE")), lon=coord(col(r, "NR_LONGITUDE")))
    for r in sec:  # locais que existam só no arquivo de votação
        k = (r["NR_ZONA"], r["NR_LOCAL_VOTACAO"])
        locais.setdefault(k, dict(zona=k[0], nr_local=k[1], nome=col(r, "NM_LOCAL_VOTACAO"),
                                  endereco=col(r, "DS_LOCAL_VOTACAO_ENDERECO"), bairro_tse="", lat=None, lon=None))

    corr = normalizar_bairros(sorted({l["bairro_tse"] for l in locais.values() if l["bairro_tse"]}))
    n_locais_bairro = defaultdict(int)
    for l in locais.values():
        l["bairro"] = corr.get(l["bairro_tse"], ("Não mapeado",))[0]
        n_locais_bairro[l["bairro_tse"]] += 1
    salvar_csv(DADOS / "correspondencia_bairros.csv",
               [dict(bairro_tse=n, bairro_gabineteos=b, metodo=m, n_locais=n_locais_bairro[n]) for n, (b, m) in sorted(corr.items())]
               + [dict(bairro_tse="(vazio no TSE)", bairro_gabineteos="Não mapeado", metodo="sem bairro no TSE", n_locais=n_locais_bairro[""])]
               * (1 if n_locais_bairro[""] else 0))

    # candidatos
    cand = {}
    for r in mz:
        n = r["NR_CANDIDATO"]
        c = cand.setdefault(n, dict(nr=n, nome=col(r, "NM_URNA_CANDIDATO"), partido=col(r, "SG_PARTIDO"),
                                    situacao=col(r, "DS_SIT_TOT_TURNO"), oficial=0))
        c["oficial"] += num(col(r, "QT_VOTOS_NOMINAIS"))
    for r in sec:
        n = r["NR_VOTAVEL"]
        if n not in ESPECIAIS and len(n) > 2:
            cand.setdefault(n, dict(nr=n, nome=r["NM_VOTAVEL"], partido="", situacao="", oficial=None))

    anderson = [c for c in cand.values() if "ANDERSON" in sem_acento(c["nome"]) and "ACADEMIA" in sem_acento(c["nome"])]
    if len(anderson) != 1:
        raise SystemExit(f"Não achei exatamente um 'Anderson da Academia' (achei {[c['nome'] for c in anderson]}).")
    A = anderson[0]["nr"]

    # votos por local (candidatos e legenda) e válidos por seção
    votos_local = defaultdict(lambda: defaultdict(int))
    soma_secao = defaultdict(int)
    legenda_local = defaultdict(int)
    for r in sec:
        k = (r["NR_ZONA"], r["NR_LOCAL_VOTACAO"]); n = r["NR_VOTAVEL"]; q = num(r["QT_VOTOS"])
        if n in ESPECIAIS:
            continue
        if len(n) <= 2:
            legenda_local[k] += q
        else:
            votos_local[k][n] += q
            soma_secao[n] += q

    # válidos oficiais por seção (detalhe da apuração) → por local
    secao_local = {(r["NR_ZONA"], r["NR_SECAO"]): (r["NR_ZONA"], r["NR_LOCAL_VOTACAO"]) for r in sec}
    validos_det = defaultdict(int); aptos = defaultdict(int); comp = defaultdict(int)
    for r in det:
        k = secao_local.get((r["NR_ZONA"], r["NR_SECAO"]))
        if not k:
            continue
        nom = num(col(r, "QT_VOTOS_NOMINAIS_VALIDOS", "QT_VOTOS_NOMINAIS"))
        leg = num(col(r, "QT_VOTOS_LEGENDA_VALIDOS", "QT_VOTOS_LEG_VALIDOS", "QT_VOTOS_LEGENDA"))
        validos_det[k] += nom + leg
        aptos[k] += num(col(r, "QT_APTOS")); comp[k] += num(col(r, "QT_COMPARECIMENTO"))

    def validos(k):
        return validos_det[k] if det else sum(votos_local[k].values()) + legenda_local[k]

    total_A = soma_secao[A]
    validos_cidade = sum(validos(k) for k in locais)

    def ranking(votos):
        ordem = sorted(votos.items(), key=lambda x: (-x[1], x[0]))
        pos = 1 + sum(1 for _, v in ordem if v > votos.get(A, 0))
        return ordem, pos

    def unidade(chaves, **extra):
        v = defaultdict(int); val = 0; ap = 0; cp = 0
        for k in chaves:
            for n, q in votos_local[k].items():
                v[n] += q
            val += validos(k); ap += aptos[k]; cp += comp[k]
        ordem, pos = ranking(v)
        a = v.get(A, 0)
        venc_nr, venc_v = ordem[0] if ordem else ("", 0)
        return dict(extra, votos=a, validos=val, aptos=ap, comparecimento=cp,
                    pct_validos=round(100 * a / val, 3) if val else 0,
                    pct_total=round(100 * a / total_A, 3) if total_A else 0,
                    posicao=pos if a else None, n_candidatos=len([x for x in v.values() if x]),
                    vencedor=cand[venc_nr]["nome"] if venc_nr else "", vencedor_nr=venc_nr, vencedor_votos=venc_v,
                    dif_vencedor=a - venc_v,
                    top5=[dict(nr=n, nome=cand[n]["nome"], partido=cand[n]["partido"], votos=q) for n, q in ordem[:5]],
                    _votos=v)

    def centro(chaves):
        pts = [(locais[k]["lat"], locais[k]["lon"]) for k in chaves if locais[k]["lat"] is not None and locais[k]["lon"] is not None]
        return (round(sum(p[0] for p in pts) / len(pts), 6), round(sum(p[1] for p in pts) / len(pts), 6)) if pts else (None, None)

    grupos = {"zona": defaultdict(list), "bairro": defaultdict(list)}
    for k, l in locais.items():
        grupos["zona"][l["zona"]].append(k); grupos["bairro"][l["bairro"]].append(k)

    niveis = {"local": [], "bairro": [], "zona": []}
    for k, l in sorted(locais.items()):
        u = unidade([k], id=f"{k[0]}-{k[1]}", nome=l["nome"], zona=l["zona"], bairro=l["bairro"], bairro_tse=l["bairro_tse"],
                    endereco=l["endereco"], lat=l["lat"], lon=l["lon"], n_locais=1)
        niveis["local"].append(u)
    for nivel in ("bairro", "zona"):
        for nome, ks in sorted(grupos[nivel].items()):
            lat, lon = centro(ks)
            u = unidade(ks, id=nome, nome=nome if nivel == "bairro" else f"Zona {int(nome)}", lat=lat, lon=lon, n_locais=len(ks),
                        zona=", ".join(sorted({locais[k]["zona"] for k in ks})))
            niveis[nivel].append(u)

    # comparativo com os eleitos
    eleitos = sorted([c for c in cand.values() if ELEITO_RX.match(sem_acento(c["situacao"]))], key=lambda c: -soma_secao[c["nr"]])
    bairros_reais = [b for b in niveis["bairro"] if b["id"] != "Não mapeado"]
    primeiros = defaultdict(int)
    for b in bairros_reais:
        if b["vencedor_nr"]:
            primeiros[b["vencedor_nr"]] += 1
    comp_cands = {c["nr"]: c for c in eleitos}
    comp_cands[A] = cand[A]
    comparativo = sorted([dict(nr=c["nr"], nome=c["nome"], partido=c["partido"], situacao=c["situacao"], votos=soma_secao[c["nr"]],
                               pct_validos=round(100 * soma_secao[c["nr"]] / validos_cidade, 3) if validos_cidade else 0,
                               bairros_1o=primeiros[c["nr"]], eh_anderson=c["nr"] == A) for c in comp_cands.values()],
                         key=lambda x: -x["votos"])

    ordem_cidade = sorted(soma_secao.items(), key=lambda x: -x[1])
    colocacao = 1 + sum(1 for _, v in ordem_cidade if v > total_A)

    # concentração e redutos
    por_votos = sorted(bairros_reais, key=lambda b: -b["votos"])
    acum, conc = 0, {}
    for i, b in enumerate(por_votos, 1):
        acum += b["votos"]
        for meta in (50, 80):
            if meta not in conc and total_A and acum >= total_A * meta / 100:
                conc[meta] = i
    media = round(100 * total_A / validos_cidade, 3) if validos_cidade else 0
    for b in niveis["bairro"]:
        b["classe"] = "Não mapeado" if b["id"] == "Não mapeado" else ("Reduto" if b["pct_validos"] > media else "Fragilidade" if b["pct_validos"] < media else "Na média")

    # conferência: soma das seções × totais oficiais
    conf = []
    for c in sorted(cand.values(), key=lambda c: -soma_secao[c["nr"]]):
        of = c["oficial"]
        conf.append(dict(nr=c["nr"], nome=c["nome"], partido=c["partido"], soma_secoes=soma_secao[c["nr"]],
                         total_oficial="" if of is None else of, diferenca="" if of is None else soma_secao[c["nr"]] - of,
                         confere="sem total oficial" if of is None else ("sim" if soma_secao[c["nr"]] == of else "NÃO")))
    salvar_csv(DADOS / "conferencia_totais.csv", conf)
    divergentes = [c for c in conf if c["confere"] == "NÃO"]
    validos_somados = sum(sum(votos_local[k].values()) + legenda_local[k] for k in locais)

    # lacunas
    sem_coord = [l for l in niveis["local"] if l["lat"] is None]
    nao_map = next((b for b in niveis["bairro"] if b["id"] == "Não mapeado"), None)
    lacunas = []
    if not mz:
        lacunas.append("Arquivo de totais oficiais por candidato (votacao_candidato_munzona) ausente: conferência não feita e lista de eleitos indisponível.")
    if not det:
        lacunas.append("Detalhe da apuração ausente: % dos válidos calculado com os votos nominais + legenda do próprio arquivo de seções.")
    if sem_coord:
        lacunas.append(f"{len(sem_coord)} local(is) de votação sem latitude/longitude no TSE não aparecem no mapa (estão na tabela).")
    if nao_map:
        lacunas.append(f"{nao_map['n_locais']} local(is) com bairro sem correspondência na lista do GabineteOS ficaram em \"Não mapeado\" ({nao_map['votos']} votos do Anderson). Veja correspondencia_bairros.csv.")
    if total_A and None in (conc.get(50), conc.get(80)):
        lacunas.append("Parte dos votos do Anderson está em locais sem bairro mapeado; por isso a marca de 50%/80% de concentração pode não ser atingida só com bairros mapeados.")
    lacunas.append("Limites oficiais dos bairros não disponíveis: o mapa usa pontos por local de votação; bairro e zona aparecem no centro dos seus locais.")
    if divergentes:
        lacunas.append(f"{len(divergentes)} candidato(s) com soma das seções diferente do total oficial. Veja conferencia_totais.csv.")

    # CSV consolidado (um registro por local de votação)
    campos = ["zona", "id", "nome", "endereco", "bairro_tse", "bairro", "lat", "lon", "aptos", "comparecimento", "validos",
              "votos", "pct_validos", "pct_total", "posicao", "n_candidatos", "vencedor", "vencedor_votos", "dif_vencedor"]
    salvar_csv(SAIDA / "base_eleitoral_consolidado.csv", niveis["local"], campos)
    salvar_csv(DADOS / "bairros.csv", [dict(b, classe=b["classe"]) for b in niveis["bairro"]], ["id", "zona", "n_locais"] + campos[8:] + ["classe"])
    salvar_csv(DADOS / "zonas.csv", niveis["zona"], ["id", "nome", "n_locais"] + campos[8:])

    for lista in niveis.values():
        for u in lista:
            u.pop("_votos", None)
    pacote = dict(
        gerado_em=date.today().strftime("%d/%m/%Y"),
        geracao_tse=sorted(g for g in geracao if g),
        arquivos=sorted(set(ARQUIVOS_LIDOS)),
        municipio=dict(nome="Divinópolis", uf="MG", cd_tse=sorted(codigos)),
        anderson=dict(nr=A, nome=cand[A]["nome"], partido=cand[A]["partido"], situacao=cand[A]["situacao"], votos=total_A,
                      colocacao=colocacao, n_candidatos=len([1 for _, v in ordem_cidade if v]),
                      pct_validos=media, bairros_1o=primeiros[A], n_bairros=len(bairros_reais),
                      conc50=conc.get(50), conc80=conc.get(80)),
        validos_cidade=validos_cidade, validos_somados=validos_somados,
        niveis=niveis, comparativo=comparativo,
        conferencia=dict(n_candidatos=len(conf), conferem=sum(1 for c in conf if c["confere"] == "sim"),
                         divergentes=divergentes[:20], sem_oficial=sum(1 for c in conf if c["confere"] == "sem total oficial")),
        lacunas=lacunas)
    # carga para o app "Base Eleitoral" já publicado: coleção "locais" (lotes de até 50) e pacote do Comparativo
    secoes_local = defaultdict(set)
    for (z, s_), k in secao_local.items():
        secoes_local[k].add(int(s_))
    lotes_dir = DADOS / "carga_app_locais"
    lotes_dir.mkdir(parents=True, exist_ok=True)
    for f in lotes_dir.glob("lote_*.json"):
        f.unlink()
    docs = []
    for u in niveis["local"]:
        k = tuple(u["id"].split("-", 1))
        docs.append(dict(op="set", collection="locais", doc_id=f"tse2024-z{int(k[0])}-l{int(k[1])}", data=dict(
            nome=u["nome"], bairro=u["bairro"], zona=str(int(u["zona"])), endereco=u["endereco"], votos=u["votos"],
            aptos=u["aptos"] or "", secoes=", ".join(str(x) for x in sorted(secoes_local[k])),
            lat=u["lat"] if u["lat"] is not None else "", lng=u["lon"] if u["lon"] is not None else "",
            fonte=f"TSE 2024, 1º turno (processado em {date.today().strftime('%d/%m/%Y')})")))
    for i in range(0, len(docs), 50):
        (lotes_dir / f"lote_{i // 50 + 1:02d}.json").write_text(json.dumps(docs[i:i + 50], ensure_ascii=False), encoding="utf-8")
    comp_app = dict(gerado_em=pacote["gerado_em"], geracao_tse=pacote["geracao_tse"], anderson=pacote["anderson"],
                    comparativo=comparativo, conferencia=pacote["conferencia"], lacunas=lacunas,
                    validos_cidade=validos_cidade, validos_somados=validos_somados,
                    bairros=[{k2: b[k2] for k2 in ("id", "zona", "n_locais", "votos", "validos", "pct_validos", "pct_total", "posicao",
                                                   "n_candidatos", "vencedor", "vencedor_votos", "dif_vencedor", "top5", "classe")}
                             for b in niveis["bairro"]])
    (DADOS / "comparativo_app.json").write_text(json.dumps(comp_app, ensure_ascii=False), encoding="utf-8")

    (DADOS / "base_eleitoral.json").write_text(json.dumps(pacote, ensure_ascii=False), encoding="utf-8")
    html = (AQUI / "template.html").read_text(encoding="utf-8").replace("/*__DADOS__*/null", json.dumps(pacote, ensure_ascii=False).replace("</", "<\\/"))
    (SAIDA / "base_eleitoral.html").write_text(html, encoding="utf-8")

    # relatório no terminal
    a = pacote["anderson"]
    print(f"Município: Divinópolis — código TSE {', '.join(sorted(codigos))}")
    print(f"Candidato: {a['nome']} (nº {a['nr']}, {a['partido']}) — {a['situacao']}")
    print(f"Votos: {a['votos']} | {a['colocacao']}º de {a['n_candidatos']} | {a['pct_validos']:.2f}% dos válidos | 1º em {a['bairros_1o']} bairro(s)")
    print(f"Concentração: {a['conc50']} bairros = 50% | {a['conc80']} bairros = 80%")
    print(f"Conferência: {pacote['conferencia']['conferem']}/{len(conf)} candidatos batem com o total oficial; "
          f"{len(divergentes)} divergente(s); {pacote['conferencia']['sem_oficial']} sem total oficial")
    print(f"Válidos (detalhe da apuração): {validos_cidade} | válidos somados das seções: {validos_somados}")
    for l in lacunas:
        print("Lacuna:", l)


if __name__ == "__main__":
    main()
