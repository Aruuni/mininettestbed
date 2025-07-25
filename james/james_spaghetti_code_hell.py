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

better_ip()