#!/usr/bin/env python3
import sys
import re

try:
    import serial
except ImportError:
    sys.stderr.write("pyserial not installed.")
    sys.exit(1)

BENCHMARK_PREFIX="[benchmark]"
BENCHMARK_CMD_PREFIX="[benchmark_cmd]"

def handle_command(cmd, cmd_val):
    if cmd == "FINISH" and cmd_val == "y":
        sys.stderr.write("Received FINISHED command. Exiting.")
        return True

def _get_kv(line, prefix):
    if line.startswith(prefix):
        benchmark = line[len(prefix):]
        bench_name, bench_value = benchmark.split(":")
        bench_name, bench_value = bench_name.strip(), bench_value.strip()
        return bench_name, bench_value
    return None


def main():
    ser = serial.Serial("/dev/ttyACM0")
    ser.baudrate = 9600

    finished = False

    while not finished:
        line = ser.read_until()
        
        try:
            line_dec = line.decode()
        except UnicodeEncodeError:
            sys.stderr.write("Could not decode, **ignoring**:", line_dec)
        
        if line_dec.startswith(BENCHMARK_PREFIX):
            name, val = _get_kv(line_dec, BENCHMARK_PREFIX)
            print(f"{name},{val}")
        elif line_dec.startswith(BENCHMARK_CMD_PREFIX):
            name, val = _get_kv(line_dec, BENCHMARK_CMD_PREFIX)
            finished = handle_command(name, val)
        else:
            sys.stderr.write("[DEBUG] " + line_dec)
        
    sys.stderr.write("Finished communication.")

if __name__ == '__main__':
    main()