import argparse

import psutil

parser = argparse.ArgumentParser()

parser.add_argument("process_name", help="the name of the process to watch for")
parser.add_argument("limit", help="memory limit as percentage of total")

args = parser.parse_args()

process_name = args.process_name
limit = float(args.limit)

for process in psutil.process_iter():
    if process.name() != process_name:
        continue
    if process.memory_percent() > limit:
        print(
            "Killing process {process_name} (PID {process.pid}), as memory usage {memory_percent}% ({memory_mb}MB) is more than {limit}%".format(
            process_name=process.name(),
            process=process,
            memory_percent=process.memory_percent(),
            memory_mb=(process.memory_info().rss / 1024 / 1024),
            limit=limit,
        ))
        process.kill()
