import re, csv, json, os, pandas as pd
from core.utils import *
from collections import defaultdict

def parse_tc_show_output(output: str) -> dict:
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

def parse_ss_to_csv(in_path: str, out_path: str, offset=0.0) -> bool:
    ts_re = re.compile(r'^(\d+\.\d+),')
    ip_port_re = re.compile(r'([\da-fA-F:.]+):(\d+)')
    keyval_colon = re.compile(r'([a-zA-Z_][\w\-]*):([^\s]+)')
    keyval_space = re.compile(r'([a-zA-Z_][\w\-]*)\s+([^\s:]+)')
    section_re = re.compile(r'([A-Za-z_][\w\-]*)\:\(([^)]*)\)')

    SPECIAL = {'rtt': ('rtt', 'rttvar'), 'retrans': ('retrans', 'retrans_total'), 'wscale': ('wscale_snd','wscale_rcv')}
    ms_pct = re.compile(r'([\d.]+)ms(?:\(([\d.]+)%\))?$')
    num_pct = re.compile(r'([\d.]+)\(([\d.]+)%\)$')
    bps = re.compile(r'([\d.]+)bps$')

    def num(x):
        try:
            return int(x) if x.isdigit() else float(x)
        except:
            return x

    def norm(k):
        return k.lower().replace('-', '_')

    def split_pair(k, v):
        if k in SPECIAL and (',' in v or '/' in v):
            a,b = v.replace(',', '/').split('/',1)
            k1,k2 = SPECIAL[k]
            return {k1: num(a), k2: num(b)}
        if ',' in v:
            a,b = v.split(',',1); return {f'{k}_1': num(a), f'{k}_2': num(b)}
        if '/' in v:
            a,b = v.split('/',1); return {f'{k}_1': num(a), f'{k}_2': num(b)}
        return None

    def normalize(k, v):
        k = norm(k)
        sp = split_pair(k, v)
        if sp: return sp
        m = ms_pct.match(v)
        if m:
            out = {f'{k}_ms': num(m.group(1))}
            if m.group(2): out[f'{k}_pct'] = num(m.group(2))
            return out
        m = num_pct.match(v)
        if m: return {k: num(m.group(1)), f'{k}_pct': num(m.group(2))}
        m = bps.match(v)
        if m: return {f'{k}_bps': num(m.group(1))}
        return {k: num(v)}

    def parse_section(sec_key, body):
        out = {}
        for item in body.split(','):
            item = item.strip()
            if not item or ':' not in item:
                continue
            k, v = item.split(':', 1)
            for kk, vv in normalize(f'{sec_key}_{k}', v).items():
                out[kk] = vv
        return out

    base_cols = ['time','state','tx_queue','rx_queue','local_ip','local_port','remote_ip','remote_port','cong']

    try:
        rows, keys = [], set(base_cols)

        with open(in_path, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                line = line.strip()
                if not line or ' ESTAB ' not in line:
                    continue
                m = ts_re.match(line)
                if not m:
                    continue
                ts = float(m.group(1))

                tokens = line.split()
                try:
                    ei = tokens.index('ESTAB')
                except ValueError:
                    continue

                row = {k: None for k in base_cols}
                row['time'], row['state'] = ts, 'ESTAB'

                tx = tokens[ei+1] if ei+1 < len(tokens) and tokens[ei+1].isdigit() else None
                rx = tokens[ei+2] if ei+2 < len(tokens) and tokens[ei+2].isdigit() else None
                row['tx_queue'] = int(tx) if tx else None
                row['rx_queue'] = int(rx) if rx else None

                pairs = ip_port_re.findall(line)
                if len(pairs) >= 2:
                    (lip,lport),(rip,rport) = pairs[:2]
                    row.update(local_ip=lip, local_port=int(lport), remote_ip=rip, remote_port=int(rport))

                cong = None
                if len(pairs) >= 2:
                    ip_seen = 0
                    for i,t in enumerate(tokens):
                        if ip_port_re.fullmatch(t):
                            ip_seen += 1
                            if ip_seen == 2 and i+1 < len(tokens):
                                cand = tokens[i+1]
                                if ':' not in cand and not cand.replace('.','',1).isdigit():
                                    cong = cand
                                break
                row['cong'] = cong

                extras = {}

                for skey, body in section_re.findall(line):
                    skey = norm(skey)
                    extras.update(parse_section(skey, body))

                scrub = section_re.sub(' ', line)

                for k, v in keyval_colon.findall(scrub):
                    if ip_port_re.fullmatch(f'{k}:{v}'):
                        continue
                    extras.update(normalize(k, v))

                scrub2 = keyval_colon.sub(' ', scrub)
                for k, v in keyval_space.findall(scrub2):
                    if ':' in k or ':' in v:
                        continue
                    if ip_port_re.fullmatch(k) or ip_port_re.fullmatch(v):
                        continue
                    nv = normalize(k, v)
                    for kk, vv in nv.items():
                        if kk not in extras:
                            extras[kk] = vv

                for k,v in extras.items():
                    row[k] = v
                    keys.add(k)
                rows.append(row)

        if not rows:
            return False  # nothing parsed

        # Make time relative from 0.0 (plus optional offset)
        t0 = min(r['time'] for r in rows if r['time'] is not None)
        for r in rows:
            r['time'] = (r['time'] - t0) + (offset or 0.0)

        header = base_cols + sorted(k for k in keys if k not in base_cols)

        with open(out_path, 'w', newline='') as fh:
            w = csv.DictWriter(fh, fieldnames=header)
            w.writeheader()
            for r in rows:
                w.writerow({k: r.get(k) for k in header})

        return True

    except Exception:
        return False

def parse_iperf_json(file: str, offset: int) -> pd.DataFrame:

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

def parse_orca_output(file: str, offset: int) -> pd.DataFrame:
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

def parse_vivace_uspace_output(file, offset):
    df = pd.read_csv(
        file,
        encoding="utf-8",
        skip_blank_lines=True,
        engine="python",      
        on_bad_lines="skip" 
    )

    if "time" not in df.columns:
        raise ValueError("Input must contain a column named 'time'.")
    if "srtt" in df.columns:
        df["srtt"] = pd.to_numeric(df["srtt"], errors="coerce")
        df = df[df["time"] >= 1.0]
    df["time"] = pd.to_numeric(df["time"], errors="coerce") + offset
    df = df.dropna(how="all").reset_index(drop=True)
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