import subprocess
import sys
import argparse


parser = argparse.ArgumentParser()
parser.add_argument("-r", "--run_location", required=True, help="<Required> Location of run to be analyzed, do not include '/' after run number")
parser.add_argument("-l", "--links", nargs='+', required=True, help="<Required> Links to be analyzed, run as -l [link1] [link2] etc")
parser.add_argument("-t", "--scan_type", required=True, help="<Required> Type of scan run (Threshold, FakeHitRate, etc)")
args = parser.parse_args()

run_location = args.run_location
links = args.links
scan_type = args.scan_type

#link processes
processes = []
print(f"Starting packet tracking on links {links}, should take around 10 minutes!")
for link in links:
    command = 'lz4 -f -d '  + run_location + '/data-link' + str(link) + '.lz4 | ./packet_tracker.py -r ' + str(run_location) + ' -l ' + str(link) + ' -t ' + scan_type
    process = subprocess.Popen(command, shell=True)
    processes.append(process)

output = [p.wait() for p in processes]
print("Packet tracking complete, check the logs under packet_logs!")
