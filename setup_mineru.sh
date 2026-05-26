#!/usr/bin/env bash
# MinerU first-run model download (Linux / macOS)
#
# Linux/macOS users do NOT have the Windows symlink permission problem,
# so no sudo is needed. This script just triggers the HF model cache
# fetch (~2-3 GB) once.
#
# After this script finishes, the "mineru" markdown engine works
# without any further setup.
set -e
cd "$(dirname "$0")"

if command -v python3 >/dev/null 2>&1; then PY=python3; else PY=python; fi

echo "=== MinerU first-run model download ==="
echo "Downloads about 2-3 GB from Hugging Face Hub."
echo "Expected time: 5-15 minutes (depending on bandwidth)."
echo

if ! command -v mineru >/dev/null 2>&1; then
  echo "[ERROR] mineru CLI not found. Run ./setup.sh first."
  exit 1
fi

echo "Creating temporary 1-page PDF ..."
$PY -c "import fitz; d=fitz.open(); p=d.new_page(); p.insert_text((72,72),'init'); d.save('_tmp_mineru_init.pdf'); d.close()"

echo "Running MinerU once to populate the model cache ..."
set +e
mineru -p _tmp_mineru_init.pdf -o _tmp_mineru_out -m auto -b pipeline -l korean -s 0 -e 0
RC=$?
set -e

rm -f _tmp_mineru_init.pdf
rm -rf _tmp_mineru_out

if [ $RC -eq 0 ]; then
  echo
  echo "=== MinerU is ready ==="
  echo "You can now run ./run.sh as normal."
else
  echo "[WARN] mineru exit code $RC. See messages above (network/disk/etc)."
  exit $RC
fi
