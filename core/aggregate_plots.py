import json
from core.parsers import *
from core.utils import *
import pandas as pd
import matplotlib as mpl
import matplotlib.pyplot as plt
import itertools
import matplotlib.gridspec as gridspec
import numpy as np
import math
from pypdf import PdfReader, PdfWriter
import time


"""
A script for plotting various aggregate metrics from all of my experiments.
Mostly adapted from aggregate plots.py

"""
import os 

if "SUDO_USER" in os.environ:
    USERNAME = os.environ["SUDO_USER"]
    HOME_DIR = os.path.expanduser(f"~{USERNAME}")
else:
    HOME_DIR = os.path.expanduser("~")
    USERNAME = os.path.basename(HOME_DIR)

experiments_folder = f'{HOME_DIR}/cctestbed/JRA_Poster_Experiments'
# I already have the CSVs, so I either need to collect the data into a mega CSV (probably a bad idea) or just loop through all of them and append their states to various dataframes (better, memory intensive?)








def process_raw_outputs(path, emulation_start_time=None):
    with open(path + '/emulation_info.json', 'r') as fin:
        emulation_info = json.load(fin)

    flows = emulation_info['flows']
    flows = list(filter(lambda flow: flow[5] != 'netem' and flow[5] != 'tbf', flows))
    flows.sort(key=lambda x: x[-2])

    csv_path = path + "/csvs"
    mkdirp(csv_path)

    change_all_user_permissions(path)
    for flow in flows:
        sender = str(flow[0])
        receiver = str(flow[1])
        sender_ip = str(flow[2])
        receiver_ip = str(flow[3])
        start_time = int(flow[-4])
        if 'orca' in flow[-2]:
            # Convert sender output into csv
            df = parse_orca_output(path+"/%s_output.txt" % sender, start_time)
            df.to_csv("%s/%s.csv" %  (csv_path, sender), index=False)

            df = parse_ss_output(path+"/%s_ss.csv" % sender, start_time)
            df.to_csv("%s/%s_ss.csv" % (csv_path,sender), index=False)
            # Convert receiver output into csv
            df = parse_orca_output(path+"/%s_output.txt" % receiver, start_time)
            df.to_csv("%s/%s.csv" %  (csv_path, receiver),index=False)
        if flow[-2] == 'sage':
            # Convert sender output into csv
            df = parse_orca_output(path+"/%s_output.txt" % sender, start_time)
            df.to_csv("%s/%s.csv" %  (csv_path, sender), index=False)

            df = parse_ss_sage_output(path+"/%s_ss.csv" % sender, start_time)
            df.to_csv("%s/%s_ss.csv" % (csv_path,sender), index=False)
            # Convert receiver output into csv
            df = parse_orca_output(path+"/%s_output.txt" % receiver, start_time)
            df.to_csv("%s/%s.csv" %  (csv_path, receiver),index=False)
        elif flow[-2] == 'aurora':
            # Convert sender output into csv
            df = parse_aurora_output(path+"/%s_output.txt" % sender, start_time)
            df.to_csv("%s/%s.csv" %  (csv_path, sender), index=False)

            # Convert receiver output into csv
            df = parse_aurora_output(path+"/%s_output.txt" % receiver, start_time)
            df.to_csv("%s/%s.csv" %  (csv_path, receiver),index=False)
        elif flow[-2] == 'astraea':
            # Convert sender output into csv
            df = parse_astraea_output(f"{path}/{sender}_output.txt" , start_time)
            df.to_csv(f"{csv_path}/{sender}.csv", index=False)

            # Convert receiver output into csv
            df = parse_astraea_output(f"{path}/{receiver}_output.txt" , start_time)
            df.to_csv(f"{csv_path}/{receiver}.csv", index=False)
        elif flow[-2] == 'vivace-uspace':
            # Convert sender output into csv
            df = parse_vivace_uspace_output(f"{path}/{sender}_output.txt" , start_time)
            df.to_csv(f"{csv_path}/{sender}.csv", index=False)

            # Convert receiver output into csv
            df = parse_vivace_uspace_output(f"{path}/{receiver}_output.txt" , start_time)
            df.to_csv(f"{csv_path}/{receiver}.csv", index=False)
        elif flow[-2] in IPERF:
            # Convert sender iperf output into csv
            df = parse_iperf_json(f"{path}/{sender}_output.txt", start_time)
            df.to_csv(f"{csv_path}/{sender}.csv", index=False)
            
            # Convert sender ss into csv
            df = parse_ss_output(path+"/%s_ss.csv" % sender, start_time, emulation_start_time=emulation_start_time)
            df.to_csv("%s/%s_ss.csv" % (csv_path,sender), index=False)
            
            # # Convert sender ss_mp into csv
            df = parse_ss_mp_output(path+"/%s_ss_mp.csv" % sender, start_time, emulation_start_time=emulation_start_time)
            df.to_csv("%s/%s_ss_mp.csv" % (csv_path,sender), index=False)

            # Convert sender ifstat into csv
            df = parse_ifstat_output(path+"/%s_ifstat.txt" % sender, start_time)
            df.to_csv("%s/%s_ifstat.csv" % (csv_path,sender), index=False)

            # Convert receiver iperf output into csv
            df = parse_iperf_json(path+"/%s_output.txt" % receiver, start_time) 
            df.to_csv("%s/%s.csv" %  (csv_path, receiver), index=False)

            # Convert receiver ifstat into csv # offset start time something james
            df = parse_ifstat_output(path+"/%s_ifstat.txt" % receiver, 0) # server starts tracking as soon as the experiment begins, even for late flows
            df.to_csv("%s/%s_ifstat.csv" % (csv_path,receiver), index=False)
        else:
            pass
            #printRed("ERROR: analysis.py: " +  str(flow[-2]) + " not supported for analysis. This may lead to x_max error. Have you tried adding it to the protocol list in utils.py?" )
