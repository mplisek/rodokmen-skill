#!/bin/bash
# matricula_batch.sh URLFILE PREFIX  (URLFILE: řádky "<snímek> <url obrázku>" vytažené z prohlížeče) -> stáhne PREFIX_<pg>.jpg (+ _s.jpg zmenšeninu 1900px)
tr -d '"' < "$1" | sed 's/\\n/\n/g' | grep -E '^[0-9]+ https' | while read p u; do
  out="${2}_$p.jpg"; [ -s "$out" ] || bash "$(dirname "$0")/matricula_dl.sh" "$u" "$out"; magick "$out" -resize 1900x "${2}_${p}_s.jpg"; done
