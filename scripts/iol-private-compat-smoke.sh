#!/usr/bin/env bash
set -euo pipefail

cd /home/felipe/unidac-lab

python3 <<'PY'
import importlib.util
from pathlib import Path

module_path = Path(
    "runtime/iol/iolctl.py"
)

spec = importlib.util.spec_from_file_location(
    "unidac_iolctl",
    module_path,
)

module = importlib.util.module_from_spec(
    spec
)

spec.loader.exec_module(
    module
)

l2 = module.private_compat_check(
    Path(
        "images/store/cisco/"
        "cisco-iol-l2-adventerprise-15-1-20140814/"
        "base.bin"
    )
)

generic = module.private_compat_check(
    Path(
        "/bin/ls"
    )
)

if l2.get(
    "libcrypto_required"
) is not True:
    raise SystemExit(
        "L2 deveria exigir libcrypto.so.4"
    )

if (
    "/opt/unidac-lab/iol-compat/lib/"
    "libcrypto.so.4"
    not in l2.get(
        "libcrypto_source",
        "",
    )
):
    raise SystemExit(
        "L2 nao resolveu private libcrypto"
    )

if generic.get(
    "libcrypto_required"
) is not False:
    raise SystemExit(
        "Imagem sem dependencia foi "
        "marcada incorretamente."
    )

if generic.get(
    "libcrypto_source"
) != "not-required":
    raise SystemExit(
        "Fonte de libcrypto inesperada."
    )

print(
    "L2 legacy libcrypto required : PASS"
)

print(
    "No-libcrypto image path      : PASS"
)
PY

echo "IOL PRIVATE COMPAT SMOKE = PASS"
