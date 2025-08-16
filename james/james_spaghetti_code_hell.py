import ipaddress
import random

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

# for x in range (1, 10):
#     for y in range (1, 10):
#         print(x)
#         print(y)
#         print(f"{0:011x}{x:02d}0{y:02d}")
host_positions = [(x, y) for x in range(1, 6) for y in range(1, 6)]
random.shuffle(host_positions)
print(host_positions)
