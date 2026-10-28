# Base eleitoral — Anderson da Academia (Divinópolis/MG, 2024)

Pipeline que gera a página "Base eleitoral" do GabineteOS a partir dos dados abertos do TSE:
votação do vereador Anderson da Academia na eleição municipal de 2024 (1º turno), por zona,
bairro e local de votação, comparada com os demais candidatos.

## Como rodar

```bash
bash baixar_tse.sh tse_bruto
```

```bash
python3 pipeline.py tse_bruto .
```

Se o download por script falhar, baixe pelo navegador em dadosabertos.tse.jus.br e coloque os
.zip (ou os .csv extraídos) em `tse_bruto/`:

| Arquivo | Conjunto no portal do TSE |
|---|---|
| `votacao_secao_2024_MG.zip` | Resultados 2024 › Votação nominal por seção eleitoral (MG) |
| `detalhe_votacao_secao_2024_MG.zip` | Resultados 2024 › Detalhe da apuração por seção eleitoral (MG) |
| `eleitorado_local_votacao_2024.zip` | Eleitorado 2024 › Eleitorado por local de votação |
| `votacao_candidato_munzona_2024.zip` | Resultados 2024 › Votação nominal por município e zona (totais oficiais, usado na conferência e na lista de eleitos) |

## O que sai

- `dados_divinopolis/` — CSVs enxutos (só Divinópolis, vereador, 1º turno), `correspondencia_bairros.csv`,
  `conferencia_totais.csv`, `bairros.csv`, `zonas.csv` e `base_eleitoral.json`.
- `base_eleitoral_consolidado.csv` — um registro por local de votação, com bairro, zona, coordenadas e indicadores.
- `base_eleitoral.html` — a página pronta, com os dados embutidos, para publicar como artifact "Base eleitoral".

## Regras de cálculo

- **Válidos para vereador** = votos nominais válidos + votos de legenda, do detalhe da apuração por seção.
- **% dos válidos** = votos do Anderson ÷ válidos na unidade. **% do total dele** = votos na unidade ÷ total dele na cidade.
- **Posição** = 1 + nº de candidatos com mais votos que ele na unidade.
- **Concentração** = menor nº de bairros (do mais para o menos votado) que soma 50% e 80% do total dele.
- **Reduto / fragilidade** = % dos válidos no bairro acima / abaixo do % dele na cidade inteira.
- **Bairro**: `NM_BAIRRO` do eleitorado por local de votação, casado com a lista `BAIRROS_DIV` do GabineteOS
  (`referencia/bairros_div.json`) por igualdade exata depois de tirar acentos e caixa e expandir abreviações
  fixas (JD → Jardim, STA → Santa, N SRA → Nossa Senhora…). Sem casamento aproximado: o que não casa fica
  "Não mapeado" e aparece em `correspondencia_bairros.csv` para revisão manual.
- **Conferência**: a soma das seções de cada candidato é comparada ao total oficial do arquivo por município e
  zona; divergências aparecem no terminal, no CSV e na página.

## Visual

`template.html` usa os tokens do GabineteOS (cores, Barlow Condensed / Geist / Geist Mono, escuro por padrão,
claro pela preferência do sistema ou pelo botão). Ver `referencia/tokens_gabineteos.md`.
