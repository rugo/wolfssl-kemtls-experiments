#!/usr/bin/env python3
import sys
from pathlib import Path
from collections import defaultdict as ddict

prefix_benchmarks = [
    "cycles_connect",
    "ticks_connect",
    "cycles_send",
    "ticks_send",
    "cycles_recv",
    "ticks_recv",
]

def log(msg):
    print("[LOG]", msg, file=sys.stderr)


def main():
    try:
        dir = sys.argv[1]
        output_dir = sys.argv[2]
    except IndexError:
        print(f"Use: {sys.argv[0]} DIR OUTPUT_DIR")
        sys.exit(1)

    path = Path(dir)
    if not path.is_dir():
        print(f"dir is not a path.")
        sys.exit(2)

    files = ddict(lambda: {})

    for subdir in path.iterdir():
        if subdir.is_dir():
            log(f"Using subdir {subdir}")
            for file in subdir.iterdir():
                benchmarks = [x.strip() for x in open(file).readlines()]
                for benchmark in benchmarks:
                    name, val = benchmark.split(",")
                    if name in prefix_benchmarks:
                        name = name + "_" + subdir.name
                    files[file.name][name] = val

    out_path = Path(output_dir)

    if not out_path.exists():
        out_path.mkdir(parents=True)

    for file in files:
        with open(out_path / Path(file), "w") as f:
            for bench_name, val in files[file].items(): 
               f.write(f"{bench_name},{val}\n")

if __name__ == '__main__':
    main()