#!/usr/bin/env python3

import re
import sys

MODULE_NAMES = [
    "wolfssl",
    "PQClean",
    "PQM4",
    "ca_cert"
]

regex_patterns = {}

module_sizes = {}
module_found = {}

for module in MODULE_NAMES:
    regex = module + r"\s+([0-9]+)"
    regex_patterns[module] = regex

for line in sys.stdin:
    for module, regex in regex_patterns.items():
        matches = re.findall(regex, line)
        for m in matches:
            val = int(m)
            if module in module_sizes:
                print(f"Size of {module} already inlcuded. Name must be duplicate. Taking bigger size.", file=sys.stderr)
                if val < module_sizes[module]:
                    val = module_sizes[module]
            module_sizes[module] = val
            module_found[module] = True

if len(module_found) != len(MODULE_NAMES):
    print("Not all module sizes found in output!")
    sys.exit(1)

for module, size in module_sizes.items():
    print(f"rom_size_{module},{size}")
