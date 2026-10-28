#!/usr/bin/env bash
# Baixa os arquivos oficiais do TSE (eleições municipais 2024) para ./tse_bruto.
# Se um download falhar, informa qual e o erro e segue com os demais.
set -u
DESTINO="${1:-tse_bruto}"
mkdir -p "$DESTINO"
BASE="https://cdn.tse.jus.br/estatistica/sead/odsele"
ARQS=(
  "votacao_secao/votacao_secao_2024_MG.zip"                  # Votação nominal por seção eleitoral 2024 (MG)
  "eleitorado_locais_votacao/eleitorado_local_votacao_2024.zip" # Eleitorado por local de votação 2024
  "detalhe_votacao_secao/detalhe_votacao_secao_2024_MG.zip"  # Detalhe da apuração por seção eleitoral 2024 (MG)
  "votacao_candidato_munzona/votacao_candidato_munzona_2024.zip" # Totais oficiais por candidato (conferência)
)
falhas=0
for a in "${ARQS[@]}"; do
  nome="$(basename "$a")"
  echo "Baixando $nome..."
  if ! erro=$(curl -fSL --retry 3 -o "$DESTINO/$nome" "$BASE/$a" 2>&1 >/dev/null); then
    echo "FALHOU: $nome -> $(echo "$erro" | tail -n1)"
    rm -f "$DESTINO/$nome"
    falhas=$((falhas+1))
  fi
done
echo "Concluído com $falhas falha(s). Arquivos em $DESTINO/"
