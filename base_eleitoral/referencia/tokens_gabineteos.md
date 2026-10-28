# Tokens visuais do GabineteOS (extraídos em 28/10/2026, somente leitura)

Fontes: Barlow Condensed 600/700 (números e títulos, `--f-num`), Geist 400/500/600 (interface, `--f-ui`),
Geist Mono 400/500 (valores tabulares, `--f-mono`). Raios: 14px (painéis), 10px, 7px.

| Token | Escuro (padrão) | Claro |
|---|---|---|
| `--bg` | #0E1113 | #F2F5F3 |
| `--surface` | #14181B | #FFFFFF |
| `--raised` | #1B2024 | #F7F9F8 |
| `--hover` | #222830 | #EDF1EF |
| `--line` / `--line-2` | #262D32 / #323A40 | #DFE5E2 / #CBD4CF |
| `--fg` | #E7ECE9 | #111815 |
| `--muted` / `--faint` | #8B9690 / #5F6A65 | #5A6661 / #8A958F |
| `--accent` | #3DDC97 | #0F9E5E |
| `--ok` / `--warn` / `--crit` / `--info` | #3DDC97 / #F3B746 / #F25C5F / #5AAEF2 | #0F9E5E / #B87700 / #D2383C / #2575CC |
| `--m-anderson` | #34C77B | #159A57 |

Tema: escuro por padrão; claro via `prefers-color-scheme: light` (se `data-theme` não for `dark`) ou `data-theme="light"`.

`BAIRROS_DIV`: 199 entradas (195 únicas) em `bairros_div.json`. Observações: há duplicatas
(Granjas do Sheik, Belvedere, Ermida, Santo Antônio dos Campos) e três nomes que são municípios vizinhos
(Nova Serrana, Itaúna, Bom Sucesso) — não afetam o casamento, mas vale limpar no GabineteOS.
