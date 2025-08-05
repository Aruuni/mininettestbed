import ipaddress

def spaghetti_ip():
    for nodes_visited in range(0, 9999999999):
        a = int(nodes_visited /256/256/256%256)
        b = int(nodes_visited /256/256%256)
        c = int(nodes_visited /256%256)
        d = int(nodes_visited %256)
        ip = f'{a}.{b}.{c}.{d}/16'
        print(ip)

def better_ip():
    for nodes_visited in range(0, 9999999999):
        print(ipaddress.IPv4Address(nodes_visited))

def calculate_jains_index(bandwidths):
    """Calculate Jain's Fairness Index for a given set of bandwidth values."""
    print(f'{bandwidths}: ')
    n = len(bandwidths)
    sum_bw = sum(bandwidths)
    sum_bw_sq = sum(bw ** 2 for bw in bandwidths)
    jains = (sum_bw ** 2) / (n * sum_bw_sq) if sum_bw_sq != 0 else 0
    print(jains)
    return jains


calculate_jains_index([20, 40, 43, 80, 80, 100])