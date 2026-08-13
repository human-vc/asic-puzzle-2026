#!/bin/zsh
set -u
cd ${0:a:h}/..
BASE=https://raw.githubusercontent.com/google/skywater-pdk-libs-sky130_fd_sc_hd/main

if [[ ! -s pdk/cellnames.txt ]]; then
  mkdir -p pdk
  .venv/bin/python - <<'EOF'
import klayout.db as db
ly = db.Layout(); ly.read("puzzle.gds")
names = sorted({c.name for c in ly.each_cell() if c.name.startswith("sky130")})
open("pdk/cellnames.txt", "w").write("\n".join(names) + "\n")
print("%d cell types used by the design" % len(names))
EOF
fi

get() {
  local out=pdk/verilog/$1
  [[ -s $out ]] && return 0
  mkdir -p ${out:h}
  local code=$(curl -s -o $out -w '%{http_code}' "$BASE/$1")
  [[ $code == 200 ]] || { rm -f $out; echo "MISS $1"; }
}

mkdir -p pdk/functional
for full in ${(f)"$(cat pdk/cellnames.txt)"}; do
  base=${full#sky130_fd_sc_hd__}; base=${base%_*}
  if [[ ! -s pdk/functional/$base.v ]]; then
    code=$(curl -s -o pdk/functional/$base.v -w '%{http_code}' \
           "$BASE/cells/$base/sky130_fd_sc_hd__$base.functional.v")
    [[ $code == 200 ]] || { rm -f pdk/functional/$base.v; echo "MISS $base"; }
  fi
  get "cells/$base/$full.v"
  get "cells/$base/sky130_fd_sc_hd__$base.v"
  get "cells/$base/sky130_fd_sc_hd__$base.functional.v"
done
for m in udp_dff_p udp_dff_pr udp_dff_ps udp_mux_2to1; do
  get "models/$m/sky130_fd_sc_hd__$m.v"
done

echo "functional models: $(ls pdk/functional | wc -l)"
echo "verilog files:     $(find pdk/verilog -name '*.v' | wc -l)"
