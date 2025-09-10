#!/usr/bin/env bash
set -euo pipefail

# 1) Trocar contêineres "card" ad-hoc por .card
rg -l 'bg-[var(--bg-secondary)]\s+dark:bg-slate-800\s+p-6\s+rounded-lg\s+card' templates \
  | xargs -I{} sed -i.bak -E 's/bg-[var(--bg-secondary)]\s+dark:bg-slate-800\s+p-6\s+rounded-lg\s+card/card/g' {}

# 2) Normalizar grids de lista para .card-grid
rg -l 'grid-cols-1.*gap-6' templates \
  | xargs -I{} sed -i.bak -E 's/grid\s+grid-cols-1[^\"]*gap-6/card-grid/g' {}

# 3) Sidebar: remover hovers fixos slate-* (serão cobertos por .sidebar-item)
rg -l 'hover:bg-slate-|bg-slate-200|dark:hover:bg-slate-' templates/partials \
  | xargs -I{} sed -i.bak -E 's/\s+hover:bg-slate-[0-9]{3}//g; s/\s+bg-slate-[0-9]{3}//g; s/\s+dark:hover:bg-slate-[0-9]{3}//g' {}

echo "Codemod aplicado. Revise diffs antes do commit."
