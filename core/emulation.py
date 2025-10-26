from core.utils import *
from core.monitor import *
from multiprocessing import Process
from core.config import *

import time
import json
import threading 

class Emulation:
    def __init__(self, network, network_config = None, traffic_config = None, path='.', interval=1, pcap=False, idx=0, data_generation={}):
        self.network = network
        self.network_config = network_config
        self.traffic_config = traffic_config
        self.sending_nodes = []
        self.receiving_nodes = []
        
        flow_lengths = []
        for config in self.traffic_config:
            flow_lengths.append(config.start + config.duration)
        
        self.sysstat_length = max(flow_lengths)

        self.interval = interval
        self.waitoutput = []
        self.call_first = []
        self.call_second = []
        self.path = path
        self.qmonitors = []
        self.start_time = 0
        self.orca_flows_counter = 0
        self.sage_flows_counter = 0
        self.astraea_flows_counter = 0
        self.counter = 0
        self.sysstat = False
        self.idx = idx
        self.pcap = pcap
        self.flip = True
        self.data_generation = data_generation

    def configure_network(self, network_config=None):
        if network_config:
            if not self.network_config:
                self.network_config = network_config
            else:
                print("WARNING: exp already has a network config set. Overriding.")

        if not self.network_config:
            print("ERROR: no network config set for this experiment")
            exit(-1)

        # Configuration is a list of namedTuples that contain: source, dest, bw, delay, qsize
        for config in self.network_config:
            links = self.network.linksBetween(self.network.get(config.node1), self.network.get(config.node2))
            for link in links:
                self.configure_link(link, config.bw, config.delay, config.qsize, config.bidir, aqm=config.aqm, loss=config.loss)
    
    def configure_link(self, link, bw, delay, qsize, bidir, aqm='fifo', loss=None, command='add'):
        interfaces = [link.intf1, link.intf2]
        printC(f"intf 1: {link.intf1}, intf 2: {link.intf2}", "magenta_fill", ALL)
        if bidir:
            n = 2
        else:
            n = 1
        for i in range(n):
            intf_name = interfaces[i].name
            node = interfaces[i].node
            if delay and not bw:
                cmd = f"sudo tc qdisc {command} dev {intf_name} root handle 3:0 netem delay {delay}ms limit {100000}"
                if (loss is not None) and (float(loss) > 0):
                    cmd += f" loss {loss}%"

            elif bw and not delay:
                burst = int(10*bw*(2**20)/250/8)
                cmd = f"sudo tc qdisc {command} dev {intf_name} root handle 1:0 tbf rate {bw}mbit burst {burst} limit {qsize * 22 if aqm != 'fifo' else qsize} "
                printC(cmd, "magenta", ALL)
                if aqm == 'fq_codel':
                    cmd += f"&& sudo tc qdisc {command} dev {intf_name} parent 1: handle 2: fq_codel limit {int(qsize/1500)} target 5ms interval 100ms flows 100"
                elif aqm == 'codel':
                    cmd += f"&& sudo tc qdisc {command} dev {intf_name} parent 1: handle 2: codel limit {int(qsize/1500)} target 5ms interval 100ms"
                elif aqm == 'sfq':
                    cmd += f"&& sudo tc qdisc {command} dev {intf_name} parent 1: handle 2: sfq perturb 10"
                elif aqm == 'cake':
                    cmd += f"&& sudo tc qdisc {command} dev {intf_name} parent 1: handle 2: cake no-split-gso bandwidth {bw}mbit rtt 50.0ms"
                elif aqm == 'fq':
                    cmd += f"&& sudo tc qdisc {command} dev {intf_name} parent 1: handle 2: fq limit {int(qsize/1500)}"
                elif aqm == 'fq_pie':
                    cmd += f"&& sudo tc qdisc {command} dev {intf_name} parent 1: handle 2: fq_pie limit {int(qsize/1500)}"
                elif aqm == 'sfb':
                    blue_burst = min(max(int(int(qsize/1500) * 0.05), 5), 20)
                    cmd += f"&& sudo tc qdisc {command} dev {intf_name} parent 1: handle 2: sfb penalty_burst {blue_burst}"

            elif delay and bw:
                burst = int(10*bw*(2**20)/250/8)
                cmd = f"sudo tc qdisc {command} dev {intf_name} root handle 1:0 netem delay {delay}ms limit {100000} && sudo tc qdisc {command} dev {intf_name} parent 1:1 handle 10:0 tbf rate {bw}mbit burst {burst} limit {qsize}"

            else:
                print("ERROR: either the delay or bandiwdth must be specified")

            if 's' in intf_name:
                printC(f"Running the following command in root terminal: {cmd}", "yellow", ALL)
                # os.system("sudo tc qdisc del dev %s  root 2> /dev/null" % intf_name)
                os.system(cmd)
            else:
                printC(f"Running the following command in {node.name}'s terminal: {cmd}", "yellow", ALL)
                # node.cmd("sudo tc qdisc del dev %s  root 2> /dev/null" % intf_name)
                node.cmd(cmd)

    def cut_link(self, node_name: str, if_name: str, interrupt: int, duration: int, interval: int): 
        node = self.network.get(node_name)
        cmd = f"ifconfig {node_name}-{if_name}"
        for i in range(interval, duration, interval):
            time.sleep(interval)
            printC(f"Running '{cmd} down'", "yellow", ALL)
            node.cmd(f"{cmd} down")
            printC(f"waiting for {interrupt / 1000.0 } s", "yellow", ALL)
            time.sleep(interrupt / 1000.0)
            printC(f"Running '{cmd} up'", "yellow", ALL)
            node.cmd(f"{cmd} up")


    def configure_routing(self, num_pairs):
        "Configure static routing on routers"
        r1a, r2a, r3a = self.network.get('r1a', 'r2a', 'r3a')
        r1b, r2b, r3b = self.network.get('r1b', 'r2b', 'r3b')

        # FIRST DUMBBELL
        r1a.setIP('10.0.1.1/24', intf='r1a-eth0')

        r2a.setIP('10.0.1.2/24', intf='r2a-eth0')
        r2a.setIP('10.0.2.1/24', intf='r2a-eth1')
        
        r3a.setIP('10.0.2.2/24', intf='r3a-eth0')

        r1a.setIP('10.0.5.1/24', intf='r1a-eth1')
        r3a.setIP('10.0.6.1/24', intf='r3a-eth1')
        
        # SECOND DUMBBELL
        r1b.setIP('10.0.3.1/24', intf='r1b-eth0')

        r2b.setIP('10.0.3.2/24', intf='r2b-eth0')
        r2b.setIP('10.0.4.1/24', intf='r2b-eth1')

        r3b.setIP('10.0.4.2/24', intf='r3b-eth0')

        r1b.setIP('10.0.5.2/24', intf='r1b-eth1')
        r3b.setIP('10.0.6.2/24', intf='r3b-eth1')

        # Configure routing for the client-server pairs
        for i in range(1, num_pairs + 1):
            # interfaces between 1 and 3 nodes and the c and x nodes in their respective dumbbells
            r1a.setIP(f'192.168.{i}.1/24', intf=f'r1a-eth{i+1}')
            r3a.setIP(f'192.168.{i+num_pairs}.1/24', intf=f'r3a-eth{i+1}')

            r1b.setIP(f'192.168.{i+2*num_pairs}.1/24', intf=f'r1b-eth{i+1}')
            r3b.setIP(f'192.168.{i+3*num_pairs}.1/24', intf=f'r3b-eth{i+1}')

            x1_subnet = f'192.168.{i+num_pairs}.0/24'
            c1_subnet = f'192.168.{i}.0/24'

            x2_subnet = f'192.168.{i+3*num_pairs}.0/24'
            c2_subnet = f'192.168.{i+2*num_pairs}.0/24'
            
            # Dumbbell 1 
            r1a.cmd(f'ip route add {x1_subnet} via 10.0.1.2')
            r2a.cmd(f'ip route add {x1_subnet} via 10.0.2.2')
            r2a.cmd(f'ip route add {c1_subnet} via 10.0.1.1')
            r3a.cmd(f'ip route add {c1_subnet} via 10.0.2.1')


            # Dumbbell 2
            r1b.cmd(f'ip route add {x2_subnet} via 10.0.3.2')
            r2b.cmd(f'ip route add {x2_subnet} via 10.0.4.2')
            r2b.cmd(f'ip route add {c2_subnet} via 10.0.3.1')
            r3b.cmd(f'ip route add {c2_subnet} via 10.0.4.1')
            

            # CROSS-LINKS BETWEEN DUMBBELLS
            r1a.cmd(f'ip route add {x2_subnet} via 10.0.1.2')
            r3a.cmd(f'ip route add {x2_subnet} via 10.0.6.2')

            r3a.cmd(f'ip route add {c2_subnet} via 10.0.2.1')
            r1a.cmd(f'ip route add {c2_subnet} via 10.0.5.2')

            r2a.cmd(f'ip route add {x2_subnet} via 10.0.2.2')
            r2a.cmd(f'ip route add {c2_subnet} via 10.0.1.1')    

    def reroute_traffic(self, n_flows, flip):
        printC("Rerouting traffic", "yellow", ALL)
        r1b, r3b = self.network.get('r1b', 'r3b')
        # thsi is for the case of HARD handover  ??
        #r2b.cmd('ifconfig r2b-eth1 down')

        if flip:
            for i in range(1, n_flows + 1):
                x2_subnet = f'192.168.{i+3*n_flows}.0/24'
                c2_subnet = f'192.168.{i+2*n_flows}.0/24'
                r1b.cmd(f'ip route replace {x2_subnet} via 10.0.5.1')
                r3b.cmd(f'ip route replace {c2_subnet} via 10.0.6.1')
        else:
            for i in range(1, n_flows + 1):
                x2_subnet = f'192.168.{i+3*n_flows}.0/24'
                c2_subnet = f'192.168.{i+2*n_flows}.0/24'
                r1b.cmd(f'ip route replace {x2_subnet} via 10.0.3.2')
                r3b.cmd(f'ip route replace {c2_subnet} via 10.0.4.1')

    def configure_traffic(self, traffic_config=None):
        '''
        This function should return two iterables:
        - One containing the list of set-up calls for each flow's server
        - One containing the list of set-up calls for each flow client
        '''
        if traffic_config:
            if not self.traffic_config:
                self.traffic_config = traffic_config
            else:
                print("WARNING: exp already has a network config set. Overriding.")

        if not self.traffic_config:
            print("ERROR: no network config set for this experiment")
            exit(-1)

        for flowconfig in self.traffic_config:
            start_time = flowconfig.start
            duration = flowconfig.duration
            source_node = flowconfig.source
            destination = flowconfig.dest
            protocol = flowconfig.protocol

            if protocol != 'tbf' and protocol != 'netem' and protocol != 'cross_traffic':
                self.waitoutput.append(source_node)
                self.waitoutput.append(destination)

                self.sending_nodes.append(source_node)
                self.receiving_nodes.append(destination)

            if 'orca' in protocol:
                params = (source_node,duration)
                command = self.start_orca_sender
                self.call_first.append(Command(command, params, None, source_node))

                params = (destination,source_node)
                command = self.start_orca_receiver
                self.call_second.append(Command(command, params, start_time, destination))

            elif 'sage' in protocol:
                params = (source_node,duration)
                command = self.start_sage_sender
                self.call_first.append(Command(command, params, None, source_node))

                params = (destination,source_node)
                command = self.start_sage_receiver
                self.call_second.append(Command(command, params, start_time, destination))

            elif 'astraea' in protocol:
                # Create server start up call
                params = (destination,)
                command = self.start_astraea_server
                self.call_first.append(Command(command, params, None, destination))

                # Create client start up call
                params = (source_node, destination, duration, ('tcpdatagen' in protocol))
                command = self.start_astraea_client
                self.call_second.append(Command(command, params, start_time, source_node))
                
            elif protocol == 'vivace-uspace':
                # Create server start up call
                params = (source_node, destination, duration)
                command = self.start_vivace_sender
                self.call_second.append(Command(command, params, start_time, source_node))
                # Create client start up call
                command = self.start_vivace_receiver
                params = (destination, duration)
                self.call_first.append(Command(command, params, None, destination))
                
            elif 'tcpdatagen' == protocol:
                destination = flowconfig.source
                source_node = flowconfig.dest
                # Create server start up call
                params = (destination, duration)
                command = self.start_tcpdatagen_sender
                self.call_first.append(Command(command, params, None, destination))

                # Create client start up call
                params = (source_node,destination)
                command = self.start_tcpdatagen_receiver
                self.call_second.append(Command(command, params, start_time, source_node))
            elif protocol == 'tbf' or protocol == 'netem':
                # Change the tbf rate to the value provided
                params = list(flowconfig.params)
                nodes_names = params[0]
                params[0] = self.network.linksBetween(self.network.get(nodes_names[0]), self.network.get(nodes_names[1]))[0]
                command = self.configure_link
                self.call_second.append(Command(command, params, start_time, 'TBF'))

            else:
                # Create server start up call
                params = (destination, 1)
                command = self.start_iperf_server
                self.call_first.append(Command(command, params, None, destination))

                # Create client start up call
                params = (source_node, destination, duration, protocol, self.interval)
                command = self.start_iperf_client
                self.call_second.append(Command(command, params, start_time, source_node))
    # if you are reading this and you are not me, then i am sorry for this run and how confusing it is. the way it works is that you send a command to a mininet host, and then you call waitOutput on it in a separate thread. this is because waitOutput is blocking, and will wait for a signal from the appliation its using to indicate successful termination.
    # this way is cringe, because if the application crashes or something, then the whole emulation will hang forever. if it is successful, its terminal output is saved to a file. This standard again is a little cringe, but it works quite well, very hard to debug
    # again, sorry, bla bla bla tech debt bla bla bla
    def run(self):
        """
        The main function that runs the experiment. It works by starting the senders first, the monitors and then the receivers.

        """
        tcpdump_processes = []
        wait_threads = []

        def start_tcpdump(node_name, interface, port):
            """
            Start tcpdump on the specified node and interface.
            The pcap file will be saved in the path specified during class initialization.
            """
            node = self.network.get(node_name)
            pcap_file = f"{self.path}/{node_name}_{interface}_trace.pcap"
            #                                      snaplen 
            tcpdump_cmd = f"tcpdump -w {pcap_file} -s 120 --count 100000000 port {port} -i {interface} &"
            print(f"Starting tcpdump on {node_name} ({interface}) with command: {tcpdump_cmd}")
            process = node.popen(tcpdump_cmd, shell=True)
            tcpdump_processes.append(process)

        def stop_tcpdump():
            """
            Stop all running tcpdump processes after the experiment ends.
            """
            for process in tcpdump_processes:
                process.terminate()

        def wait_thread(node_name: str) -> None:
            """
            This thread is used to wait for the output of the given node.
            """
            host = self.network.get(node_name)
            #printC(host.waitOutput(verbose = True), "red", DEBUG)
            output = host.waitOutput(verbose = True)
            mkdirp(self.path)
            with open( f"{self.path}/{node_name}_output.txt", 'w') as fout:
                fout.write(output)

        def host_thread(call: Command) -> None:
            """
            These threads are used to start the receivers at a specific time, independent of other flows. 
            """
            time.sleep(call.waiting_time)
            call.command(*call.params)
            t = threading.Thread(target=wait_thread, args=(call.node,))
            t.start()
            wait_threads.append(t)

        def traffic_change_thread(call: Command) -> None:
            time.sleep(call.waiting_time)
            call.command(*call.params)

        for call in self.call_first:
            call.command(*call.params)
            t = threading.Thread(target=wait_thread, args=(call.node,))
            t.start()
            wait_threads.append(t)

        for monitor in self.qmonitors:
            monitor.start()

        if self.sysstat:
            start_sysstat(1,self.sysstat_length,self.path) 
            if any("r2a" in config.node1 for config in self.network_config):
                start_sysstat(1,self.sysstat_length,self.path, self.network.get("r2a")) 
                start_sysstat(1,self.sysstat_length,self.path, self.network.get("r2b")) 
            # run sysstat on each sender to collect ETCP and UDP stats
            for node_name in self.sending_nodes:
                start_sysstat(1,self.sysstat_length,self.path, self.network.get(node_name))
                # Start tcpdump on all sender and receiver nodes
        if self.pcap:
            for node_name in self.sending_nodes:
                start_tcpdump(node_name, f"{node_name}-eth0", 11111 )

            for node_name in self.receiving_nodes:
                start_tcpdump(node_name, f"{node_name}-eth0", 5201)  

        for call in self.call_second:
            # start all the receivers at the same time, they will individually wait for the correct time
            if call.node == 'TBF':
                threading.Thread(target=traffic_change_thread, args=(call,)).start()
                continue
            threading.Thread(target=host_thread, args=(call,)).start()
        
        #here we wait untill all the waitOutput threads are finished, indicating that all flows are done
        for t in wait_threads:
            t.join()

        if self.pcap:
            stop_tcpdump()  
        printC("All flows have finished", "green_fill", ALL)
        
        for monitor in self.qmonitors:
            if monitor is not None:
                monitor.terminate()
                
        if self.sysstat:
            if any("r2a" in config.node1 for config in self.network_config):
                self.sending_nodes.append("r2a")
                self.sending_nodes.append("r2b")
            stop_sysstat(self.path, self.sending_nodes)


    def set_monitors(self, monitors, interval_sec=0.1):
        if "sysstat" in monitors:
            self.sysstat = True
            monitors.remove("sysstat")
        for monitor in monitors:
            node, interface = monitor.split('-')
            if 's' in node:
                iface = f"{node}-{interface}"
                monitor = Process(target=monitor_qlen, args=(iface, interval_sec,f"{self.path}/queues"))
                self.qmonitors.append(monitor)
            elif 'r' in node:
                iface = f"{node}-{interface}"
                mininode = self.network.get(node)
                monitor = Process(target=monitor_qlen_on_router, args=(iface, mininode, interval_sec,f"{self.path}/queues"))
                self.qmonitors.append(monitor)

    def start_iperf_server(self, node_name: str, monitor_interval=1, port=5201):
        """
        Start a one-off iperf3 server on the given node with the given port at a default interval of 1 second
        """
        node = self.network.get(node_name)
        cmd = f"iperf3 -p {port} -i {monitor_interval} --one-off --json -s"
        printC(f"Sending command '{cmd}' to host {node.name}", "blue_fill", ALL)
        node.sendCmd(cmd)

    def start_iperf_client(self, node_name: str, destination_name: str, duration: int, protocol: str, monitor_interval=0.1, port=5201):
        """
        Start a iperf3 client on the given node with the given destination and port at a default interval of 1 second. 
        Additioanlly, the SS script is started on the client node with a default interval of 0.01 seconds (lowest possible). 
        Later versions of iperf3 will have the rtt and cwnd in its json output.
        """
        node = self.network.get(node_name)

        sscmd = f"{SS_PATH}/ss_script_iperf3.sh 0.1 {self.path}/{node.name}_ss.csv &"
        printC(f'Sending command {sscmd} to host {node.name}', "blue", ALL)
        node.cmd(sscmd)

        iperfCmd = (
            f"iperf3 -p {port} --cport=11111 " + 
            f"-i {monitor_interval} -C {protocol} --json -t {duration} -c {self.network.get(destination_name).IP()}"
        ).replace("  ", " ").strip()       
        printC(f'Sending command {iperfCmd} to host {node.name}', "blue", ALL)
        node.sendCmd(iperfCmd)

    def start_tcpdatagen_sender(self, node_name: str, duration: int,  monitor_interval=1, port=44279):
        """
        Starts a tcpdatagen connection
        """
        node = self.network.get(node_name)
        # sscmd = f"./core/ss/ss_script.sh 0.1 {(self.path + '/' + node.name + '_ss.csv')} &"
        # print(f"Sending command '{sscmd}' to host {node.name}")
        # node.cmd(sscmd)
        flows_str = ",".join(map(str, self.data_generation['flows_order']))     
        getter = self.data_generation.get('timestamp')
        time_stamp = int(getter) if getter is not None else int(time.time() * 1000)
        cmd = f"{TCPDATAGEN_INSTALL_FOLDER}/bin/{self.data_generation['actor_version']} {port} \"{flows_str}\" {self.data_generation['env_bw']} {self.data_generation['scheme']} delay {self.data_generation['trace_set']}/{self.data_generation['trace_file']} {duration} reserved {time_stamp} {self.data_generation['bw2']} {self.data_generation['bw2_flip_period']} "

        printC(f"Sending command '{cmd}' to host {node.name}", "cyan", ALL)
        node.sendCmd(cmd)

    def start_tcpdatagen_receiver(self, node_name: str, destination_name: str, port=44279):
        node = self.network.get(node_name)
        cmd = f"{TCPDATAGEN_INSTALL_FOLDER}/bin/client {self.network.get(destination_name).IP()} 0 {port}"
        printC(f"Sending command '{cmd}' to host {node.name}", "cyan_fill", ALL)
        node.sendCmd(cmd)

    def start_astraea_server(self, node_name: str, monitor_interval=1, port=44279):
        """
        Starts a one-off astraea server on the given node with the given port at a default interval of 1 second
        """
        node = self.network.get(node_name)
        cmd = f"sudo -u {USERNAME} {ASTRAEA_INSTALL_FOLDER}/src/build/bin/server --port={port} --perf-interval={monitor_interval * 1000}  --one-off --terminal-out"
        printC(f"Sending command '{cmd}' to host {node.name}", "yellow_fill", ALL)
        node.sendCmd(cmd)

    def start_astraea_client(self, node_name: str, destination_name: str, duration: int, datagen: bool, monitor_interval=1 , port=44279 ):
        node = self.network.get(node_name)
        # Might not need
        # sscmd = f"./ss_script.sh 0.1 {self.path}/{node.name}_ss.csv &" 
        # print(f'Sending command {sscmd} to host {node.name}')
        flows_str = ",".join(map(str, self.data_generation['flows_order']))
        cmd = f"sudo -u {USERNAME} {ASTRAEA_INSTALL_FOLDER}/src/build/bin/client_eval --ip={self.network.get(destination_name).IP()} --port={port} --cong=astraea --interval=20  --terminal-out --pyhelper={ASTRAEA_INSTALL_FOLDER}/python/infer.py --model={ASTRAEA_INSTALL_FOLDER}/models/py/ --duration={duration} --id={self.astraea_flows_counter} " + (f"--tcpdatagen-log={TCPDATAGEN_TRACES_FOLDER+self.data_generation['trace_file']}.txt --bw={self.data_generation['env_bw']} --start-timestamp={int(time.time() * 1_000)} --flow-arrival={flows_str} --bw2={self.data_generation['bw2']}" if datagen else "")
        printC(f"Sending command '{cmd}' to host {node.name}", "yellow", ALL)
        node.sendCmd(cmd)
        self.astraea_flows_counter+= 1


    def start_orca_sender(self, node_name: str, duration: int, port=4444):
        """
        Start the orca sender on the given node with the given duration and port. Also starts a SS script on the node with an interval of 0.01 seconds for the rtt and cwnd.
        """
        node = self.network.get(node_name)
        
        sscmd = f"./core/ss/ss_script.sh 0.1 {(self.path + '/' + node.name + '_ss.csv')} &"
        printC(f"Sending command '{sscmd}' to host {node.name}", "green", ALL)
        node.cmd(sscmd)

        orcacmd = f"sudo -u {USERNAME} EXPERIMENT_PATH={self.path} {ORCA_INSTALL_FOLDER}/sender.sh {port} {self.orca_flows_counter} {duration} {ORCA_INSTALL_FOLDER}"  
        printC(f"Sending command '{orcacmd}' to host {node.name}", "green", ALL)
        node.sendCmd(orcacmd)
        
        self.orca_flows_counter+= 1 

    def start_orca_receiver(self, node_name: str, destination_name: str, port=4444):
        """
        Start the orca receiver on the given node with the given destination and port.
        """
        node = self.network.get(node_name)
        orcacmd = f"sudo -u {USERNAME} {ORCA_INSTALL_FOLDER}/receiver.sh {self.network.get(destination_name).IP()} {port} {0} {ORCA_INSTALL_FOLDER}"
        printC(f"Sending command '{orcacmd}' to host {node.name}", "green_fill", ALL)
        node.sendCmd(orcacmd)

    def start_sage_sender(self, node_name, duration, port=5555):
        node = self.network.get(node_name)
        sscmd = f"{PARENT_DIR}/core/ss/ss_script.sh 0.1 {(self.path + '/' + node.name + '_ss.csv')} &"
        printC(f"Sending command '{sscmd}' to host {node.name}", "magenta", ALL)
        node.cmd(sscmd)

        sagecmd = f"sudo -u {USERNAME} EXPERIMENT_PATH={self.path} {SAGE_INSTALL_FOLDER}/sender.sh {port} {(self.idx if self.idx else '')}{self.sage_flows_counter} {duration} {SAGE_INSTALL_FOLDER} {HOME_DIR}/venvpy38" #  |& tee -a {self.path}/{node.name}_sage_sender_{(self.idx if self.idx else '')}{self.sage_flows_counter}.txt &"
        printC(f"Sending command '{sagecmd}' to host {node.name}", "magenta", ALL)
        node.sendCmd(sagecmd)
        
        self.sage_flows_counter+= 1 

    def start_sage_receiver(self, node_name, destination_name, port=5555):
        node = self.network.get(node_name)
        destination = self.network.get(destination_name)
        sagecmd = f"sudo -u {USERNAME} {SAGE_INSTALL_FOLDER}/receiver.sh {destination.IP()} {port} {0} {SAGE_INSTALL_FOLDER}"
        printC(f"Sending command '{sagecmd}' to host {node.name}", "magenta_fill", ALL)
        node.sendCmd(sagecmd)

    def start_vivace_sender(self, node_name, destination_name, duration, port=6666, perf_interval=1):
        node = self.network.get(node_name)
        destination = self.network.get(destination_name)
        auroracmd = f"sudo -u {USERNAME} LD_LIBRARY_PATH=$LD_LIBRARY_PATH:{PCC_USPACE_INSTALL_FOLDER}/pcc-gradient/sender/src {PCC_USPACE_INSTALL_FOLDER}/pcc-gradient/sender/app/gradient_descent_pcc_client {destination.IP()} {port} 1 --duration {duration} --interval 0.1"        
        printC(f"Sending command '{auroracmd}' to host {node.name}", "red", ALL)
        node.sendCmd(auroracmd)

    def start_vivace_receiver(self, node_name, duration, port=6666, perf_interval=1):
        node = self.network.get(node_name)
        auroracmd = f"sudo -u {USERNAME} LD_LIBRARY_PATH=$LD_LIBRARY_PATH:{PCC_USPACE_INSTALL_FOLDER}/pcc-gradient/receiver/src {PCC_USPACE_INSTALL_FOLDER}/pcc-gradient/receiver/app/appserver --one-off --duration {duration} {port}"
        printC(f"Sending command '{auroracmd}' to host {node.name}", "red_fill", ALL)
        node.sendCmd(auroracmd)

    def dump_info(self):
        emulation_info = {}
        emulation_info['topology'] = str(self.network.topo)
        flows = []
        for config in self.traffic_config:
            flow = [config.source, config.dest, self.network.get(config.source).IP(), self.network.get(config.dest).IP(), config.start, config.duration, config.protocol, config.params]
            flows.append(flow)
        emulation_info['flows'] = flows
        with open(f"{self.path}/emulation_info.json", 'w') as fout:
            json.dump(emulation_info,fout)

