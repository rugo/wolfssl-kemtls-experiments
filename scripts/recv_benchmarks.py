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
BENCHMARK_ERROR_PREFIX="[benchmark_error]"

class EXIT_CODES:
    SUCCESS = 0
    ERROR = 1

def handle_command(cmd, cmd_val):
    finish = None
    exit_code = None
    if cmd == "finish_success":
        sys.stderr.write("Received FINISHED command. Exiting.")
        finish = True
        if cmd_val == "y":
            exit_code = EXIT_CODES.SUCCESS
        else:
            exit_code = EXIT_CODES.ERROR
    elif cmd == "error":
        sys.stderr.write(f"Received ERROR message: {cmd_val}!")
        # So far errors are purely informational
        finish = False
    
    return (finish, exit_code)


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
    exit_code = EXIT_CODES.ERROR

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
            print(f"CMD_{name},{val}")
            finished, exit_code = handle_command(name, val)
        else:
            sys.stderr.write("[DEBUG] " + line_dec)
        
    sys.stderr.write("Finished communication.")
    return exit_code


if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)