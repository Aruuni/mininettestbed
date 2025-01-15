import re
import pandas as pd
import json
import os
from core.utils import *
from collections import defaultdict
def parse_tc_show_output(output):
    '''
    Parse tc show dev output. Assumes that dev can only have one netem and/or one tbf. 
    Returns a dict where key is type of qdisc and value is another dict with dropped, bytes queues and pkts queued.
    '''
    ret = {}
    input_string = output.split('\n')
    for index,line in enumerate(input_string):
        if "netem" in line or "tbf" in line:
            if "netem" in line:
                qdisc_type = 'netem'
                # Get number of dropped pkts from this qdisc
            elif "tbf" in line:
                qdisc_type = 'tbf'


            dropped = 0
            bytes_queued = 0
            packets_queued = 0

            pattern = re.compile(r'.*\(dropped (\d+),')    
            
            matches = pattern.findall(input_string[index+1])
            if matches:
                dropped = int(matches[0][0])

            pattern = re.compile(r'.*backlog\s+(\d+)b\s+(\d+)p')    
            matches = pattern.findall(input_string[index+2])
            
            if matches:
                bytes_queued = int(matches[0][0])
                packets_queued = int(matches[0][1])
            
            ret[qdisc_type] = {'dropped': dropped, 'bytes': bytes_queued, 'pkts': packets_queued}
    
    return ret



def parse_ss_output(file_path, offset=0):
    #df = pd.read_csv(file_path)
    patterns = {
        "time": r"^(\d+\.\d+),",  # Timestamp at the beginning
        "state": r"\sESTAB\s",  # Match exact ESTAB state
        "cwnd": r"cwnd:(\d+)",
        "srtt": r"rtt:([\d.]+)/",  # Extract srtt
        "rttvar": r"rtt:[\d.]+/([\d.]+)",  # Extract rttvar
        "retr": r"retrans:(\d+)/"   
    }
    data = defaultdict(list)  # Initializes a dictionary where values are lists
    with open(file_path, "r") as f:
        for line in f:
            # Filter for exact ESTAB state
            if not re.search(patterns["state"], line):
                continue

            # Extract timestamp
            time_match = re.search(patterns["time"], line)
            if not time_match:
                continue
            timestamp = float(time_match.group(1))
            data["time"].append(timestamp)

            # Extract metrics
            for key, pattern in patterns.items():
                if key == "time" or key == "state":
                    continue
                match = re.search(pattern, line)
                value = float(match.group(1)) if match else None
                data[key].append(value if value is not None else 0)
    df = pd.DataFrame(data)

    if df.empty:
        raise ValueError("No ESTAB state entries found in the input file.")

    # Convert the 'time' column to relative time (seconds since the minimum timestamp)
    min_time = df['time'].min()
    df['time'] = df['time'] - min_time + offset
    return df



def parse_iperf_output(output):
    """Parse iperf output and return bandwidth.
    iperfOutput: string
    returns: result string"""
    
    r_client =  r"\[\s*(\d+)\]\s+(\d+\.?\d*-\d+\.?\d*)\s+sec\s+(\d+\.?\d*\s+[KMG]?Bytes)\s+(\d+\.?\d*\s+[KMG]?bits/sec)\s+(\d+)\s+(\d+\.?\d*\s+[KMG]?Bytes)"
    values_client = re.findall(r_client, iperfOutput )
    
    r_server =  r"\[\s*(\d+)\]\s+(\d+\.?\d*-\d+\.?\d*)\s+sec\s+(\d+\.?\d*\s+[KMG]?Bytes)\s+(\d+\.?\d*\s+[KMG]?bits/sec)"
    values_server = re.findall(r_server, iperfOutput )

    if len(values_client) > 2:
        if mode == 'last':
            # TODO:
            return values_client[-1]
        elif mode == 'series':
            ids = []
            time = []
            transferred = []
            bandwidth = []
            retr = []
            cwnd = []
            for x in values_client:
                ids.append(x[0])
                time.append(float(x[1].split('-')[-1]) + time_offset)
                transferred.append(convert_to_mega_units(x[2]))
                bandwidth.append(convert_to_mega_units(x[3]))
                retr.append(x[4])
                cwnd.append(convert_to_mega_units(x[5])*(2**20)/1500)

            return [time, transferred, bandwidth, retr, cwnd]
        else:
            print( 'mode not accepted')
    elif len(values_server) > 2:
        if mode == 'last':
            # TODO:
            return values_server[-1]
        elif mode == 'series':
            ids = []
            time = []
            transferred = []
            bandwidth = []
            for x in values_server:
                ids.append(x[0])
                time.append(float(x[1].split('-')[-1]) + time_offset)
                transferred.append(convert_to_mega_units(x[2]))
                bandwidth.append(convert_to_mega_units(x[3]))

            return [time, transferred, bandwidth]
        else:
            print( 'mode not accepted')
    
    else:
        # was: raise Exception(...)
        print( 'could not parse iperf output: ' + iperfOutput )
        return ''

def parse_iperf_json(file, offset):

    with open(file, 'r') as fin:
        iperfOutput = json.load(fin)
    
    snd_mss = iperfOutput['start']['tcp_mss_default']

    time = []
    transferred = []
    bandwidth = []
    retr = []
    cwnd = []
    rtt = []
    rttvar = []
    bytes_total = 0
    for interval in iperfOutput['intervals']:
        interval_data = interval['streams'][0]
        bytes_total = bytes_total + (interval_data['bytes'] / (2**20))
        time.append(interval_data['end'] + offset)
        transferred.append(bytes_total)
        bandwidth.append(interval_data['bits_per_second'] / (2**20))
        if 'retransmits' in list(interval_data.keys()):
            retr.append(interval_data['retransmits'])
        if 'snd_cwnd' in list(interval_data.keys()):
            cwnd.append(interval_data['snd_cwnd'] / snd_mss)
        if 'rtt' in list(interval_data.keys()):
            rtt.append(interval_data['rtt'] / 1000)
        if 'rttvar' in list(interval_data.keys()):
            rttvar.append(interval_data['rttvar'] / 1000)


    data_dict = {'time': time, 'transferred': transferred, 'bandwidth': bandwidth}
    if len(retr) > 0:
        data_dict['retr'] = retr
    if len(cwnd) > 0:
        data_dict['cwnd'] = cwnd
    if len(rtt) > 0:
        data_dict['srtt'] = rtt
    if len(rttvar) > 0:
        data_dict['rttvar'] = rttvar
    

    df = pd.DataFrame(data_dict)
    return df

def parse_orca_output(file, offset):
    with open(file, 'r') as fin:
        orcaOutput = fin.read()
    start_index = orcaOutput.find("----START----")
    end_index = orcaOutput.find("----END----")
    orcaOutput = orcaOutput[start_index:end_index]
 
    lines = orcaOutput.strip().split("\n")
    lines = [line for line in lines if line.strip() != '']
    
    
    # Extract the relevant information
    data = [line.split(",") for line in lines[1:]]
    columns = ["time", "bandwidth", "bytes"] if len(data[0]) == 3 else ["time", "bandwidth", "bytes", "totalgoodput"]

    # Create a pandas DataFrame
    df = pd.DataFrame(data, columns=columns)
    # Convert columns to appropriate types
    df["time"] = df["time"].astype(float)
    if len(columns) > 3:
        df["time"] = df["time"] + offset
    df["bandwidth"] = df["bandwidth"].astype(float) / 1000000
    df["bytes"] = df["bytes"].astype(float)
    if len(columns) > 3:
        df["totalgoodput"] = df["totalgoodput"].astype(float)
    
    return df

def parse_astraea_output(file, offset):
    with open(file, 'r') as fin:
        out = fin.read()
    start_index = out.find("----START----")
    end_index = out.find("----END----")
    out = out[start_index:end_index]
 
    lines = out.strip().split("\n")
    lines = [line for line in lines if line.strip() != '']
    
    
    # Extract the relevant information
    data = [line.split(",") for line in lines[1:]]
    #time,min_rtt,avg_urtt,cnt,srtt_us,avg_thr,thr_cnt,pacing_rate,loss_bytes,packets_out,retrans_out,max_packets_out,CWND in Kernel,CWND to Assign
    columns = ["time", "min_rtt", "avg_urtt", "cnt", "srtt", "bandwidth", "thr_cnt", "pacing_rate", "loss_bytes", "packets_out", "retr", "max_packets_out", "cwnd", "CWND to Assign"] if len(data[0]) == 14 else ["time", "bandwidth"]

    # Create a pandas DataFrame
    df = pd.DataFrame(data, columns=columns)
    # Convert columns to appropriate types
    df["time"] = df["time"].astype(int)
    min_rtt = df["time"].min()    
    df["time"] = df["time"] - min_rtt 
    df["time"] = df["time"]/ 1000

    if len(data[0]) == 14:
        df["time"] = df["time"] + offset


    
    return df


def parse_aurora_output(file, offset):
    with open(file, 'r') as fin:
        auroraOutput = fin.read()

    start_index = auroraOutput.find("new connection")
    if start_index == -1:
        start_index = auroraOutput.find("No connection established within")
        if start_index == -1:
            # Client case
            start_index = auroraOutput.find("finished connect")
            if start_index == -1:
                case = "client"
                success = False
            else:
                case = "client"
                success = True
        
        else:
            case = "server"
            success = False
    else:
        case = "server"
        success = True

    if success:
        auroraOutput = auroraOutput[start_index:]
        auroraOutput = auroraOutput.replace("send/recv: Non-blocking call failure: no buffer available for sending.\n", "")
        end_index =  auroraOutput.find("recv:Connection was broken.")
        if end_index != -1:
             auroraOutput = auroraOutput[:end_index]
        end_index =  auroraOutput.find("recv:Non-blocking call failure: no data available for reading")
        if end_index != -1:
             auroraOutput = auroraOutput[:end_index]
        lines = auroraOutput.strip().split("\n")
        lines = [line for line in lines if line.strip() != '']
        lines = lines[1:] # Remove the first line containing "new connection...."
        columns = lines[0].split(",")
    
        # Extract the relevant information
        data = [line.split(",") for line in lines[1:]]
        data = data[1:] #Remove first data point containing uniitialised values

        data = [[float(val) for val in sublist] for sublist in data]
        # Create a pandas DataFrame
        df = pd.DataFrame(data, columns=columns)
        # Convert columns to appropriate types
        df["time"] = df["time"] / 1000000
        df["time"] = df["time"] + offset
    else:
        if case == 'client':
            df = pd.DataFrame([], columns=['time','bandwidth','rtt','sent','lost','retr'])
        elif case == 'server':
            df = pd.DataFrame([], columns=['time','bandwidth'])

    return df