from core.utils import *
from core.monitor import *
from multiprocessing import Process
from core.config import *

import time
import json
import threading 

class Emulation:
    def __init__(self, network, network_config = None, traffic_config = None, path='.', interval=1):
        self.network = network
        self.network_config = network_config
        self.traffic_config = traffic_config
        
        # Lists used to run systats
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
        self.tcp_probe = False
        self.start_time = 0
        self.orca_flows_counter = 0
        self.sage_flows_counter = 0
        self.astraea_flows_counter = 0
        self.counter = 0

        self.flip = True

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
        printDebug(f"intf 1: {link.intf1}, intf 2: {link.intf2}")
        if bidir:
            n = 2
        else:
            n = 1
        for i in range(n):
            intf_name = interfaces[i].name
            node = interfaces[i].node
            if delay and not bw:
                
                cmd = 'sudo tc qdisc %s dev %s root handle 1:0 netem delay %sms limit %s' % (command, intf_name, delay,  100000)
                #print(cmd)
                if (loss is not None) and (float(loss) > 0):
                    cmd += " loss %s%%" % (loss)
                if aqm == 'fq_codel':
                    cmd += "&& sudo tc qdisc %s dev %s parent 1: handle 2: fq_codel limit 17476 target 5ms interval 100ms flows 100" % (command, intf_name)
                elif aqm == 'codel':
                    cmd += "&& sudo tc qdisc %s dev %s parent 1: handle 2: codel limit 17476 target 5ms interval 100ms" % (command, intf_name)
                elif aqm == 'fq':
                    cmd += "&& sudo tc qdisc %s dev %s parent 1: handle 2: sfq perturb 10" % (command, intf_name)

            elif bw and not delay:
                burst = int(10*bw*(2**20)/250/8)
                cmd = 'sudo tc qdisc %s dev %s root handle 1:0 tbf rate %smbit burst %s limit %s ' % (command, intf_name, bw, burst, qsize)
                #print(cmd)
                if aqm == 'fq_codel':
                    cmd += "&& sudo tc qdisc %s dev %s parent 1: handle 2: fq_codel limit %s target 5ms interval 100ms flows 100" % (command, intf_name,     int(qsize/1500))
                elif aqm == 'codel':
                    cmd += "&& sudo tc qdisc %s dev %s parent 1: handle 2: codel limit %s target 5ms interval 100ms" % (command, intf_name,   int(qsize/1500))
                elif aqm == 'fq':
                    cmd += "&& sudo tc qdisc %s dev %s parent 1: handle 2: sfq perturb 10" % (command, intf_name)

            elif delay and bw:
                burst = int(10*bw*(2**20)/250/8)
                cmd = 'sudo tc qdisc %s dev %s root handle 1:0 netem delay %sms limit %s && sudo tc qdisc %s dev %s parent 1:1 handle 10:0 tbf rate %smbit burst %s limit %s ' % (command, intf_name, delay,    100000, command, intf_name, bw, burst, qsize)
                #print(cmd)
                if aqm == 'fq_codel':
                    cmd += "&& sudo tc qdisc %s dev %s parent 10: handle 20: fq_codel limit %s target 5ms interval 100ms flows 100" % (command, intf_name,     int(qsize/1500))
                elif aqm == 'codel':
                    cmd += "&& sudo tc qdisc %s dev %s parent 10: handle 20: codel limit %s target 5ms interval 100ms" % (command, intf_name,    int(qsize/1500))
                elif aqm == 'fq':
                    cmd += "&& sudo tc qdisc %s dev %s parent 10: handle 20: sfq perturb 10" % (command, intf_name)

            else:
                print("ERROR: either the delay or bandiwdth must be specified")

            if 's' in intf_name:
                printTC(f"Running the following command in root terminal: {cmd}" )
                # os.system("sudo tc qdisc del dev %s  root 2> /dev/null" % intf_name)
                os.system(cmd)
            else:
                printTC(f"Running the following command in {node.name}'s terminal: {cmd}")
                # node.cmd("sudo tc qdisc del dev %s  root 2> /dev/null" % intf_name)
                node.cmd(cmd)



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
        printDebug3("Rerouting traffic")
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

        previous_start_time = 0

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

            if protocol == 'orca':
                params = (source_node,duration)
                command = self.start_orca_sender
                self.call_first.append(Command(command, params, None, source_node))

                params = (destination,source_node)
                command = self.start_orca_receiver
                self.call_second.append(Command(command, params, start_time, destination))

            elif protocol == 'sage':
                params = (source_node,duration)
                command = self.start_sage_sender
                self.call_first.append(Command(command, params, None, source_node))

                params = (destination,source_node)
                command = self.start_sage_receiver
                self.call_second.append(Command(command, params, start_time, destination))

            elif protocol == 'astraea':
                # Create server start up call
                params = (destination,)
                command = self.start_astraea_server
                self.call_first.append(Command(command, params, None, destination))

                # Create client start up call
                params = (source_node,destination,duration)
                command = self.start_astraea_client
                self.call_second.append(Command(command, params, start_time, source_node))
                
            elif protocol == 'aurora':
                # Create server start up call
                params = (destination, duration)
                command = self.start_aurora_server
                self.call_first.append(Command(command, params, None, ))

                # Create client start up call
                params = (source_node,destination,duration,f"{HOME_DIR}/mininettestbed/saved_models/icml_paper_model" )
                command = self.start_aurora_client
                self.call_second.append(Command(command, params, start_time, destination))
                
            elif protocol == 'tbf' or protocol == 'netem':
                # Change the tbf rate to the value provided
                params = list(flowconfig.params)
                nodes_names = params[0]
                params[0] = self.network.linksBetween(self.network.get(nodes_names[0]), self.network.get(nodes_names[1]))[0]
                command = self.configure_link
                self.call_second.append(Command(command, params, start_time, 'TBF'))

            elif protocol != 'aurora' and protocol not in ORCA:
                # Create server start up call
                params = (destination, 1)
                command = self.start_iperf_server
                self.call_first.append(Command(command, params, None, destination))

                # Create client start up call
                params = (source_node, destination, duration, protocol, self.interval)
                command = self.start_iperf_client
                self.call_second.append(Command(command, params, start_time, source_node))

            else:
                print("ERROR: Protocol %s not recognised. Terminating..." % (protocol))

            previous_start_time = start_time

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
            tcpdump_cmd = f"tcpdump -w {pcap_file} -s 120 -c 100000000 port {port} -i {interface} &"
            print(f"Starting tcpdump on {node_name} ({interface}) with command: {tcpdump_cmd}")
            process = node.popen(tcpdump_cmd, shell=True)
            tcpdump_processes.append(process)

        def stop_tcpdump():
            """
            Stop all running tcpdump processes after the experiment ends.
            """
            for process in tcpdump_processes:
                process.terminate()  # This will stop tcpdump

        def wait_thread(node_name: str) -> None:
            """
            This thread is used to wait for the output of the given node.
            """
            host = self.network.get(node_name)
            #printRed(host.waitOutput(verbose = True))
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
            # run sysstat on each sender to collect ETCP and UDP stats
            for node_name in self.sending_nodes:
                start_sysstat(1,self.sysstat_length,self.path, self.network.get(node_name))
                # Start tcpdump on all sender and receiver nodes
        # for node_name in self.sending_nodes:
        #     start_tcpdump(node_name, f"{node_name}-eth0", 5201)  # Adjust the interface name as per your setup

        # for node_name in self.receiving_nodes:
        #     start_tcpdump(node_name, f"{node_name}-eth0", 5201)  # Adjust the interface name as per your setup

        for call in self.call_second:
            # start all the receivers at the same time, they will individually wait for the correct time
            if call.node == 'TBF':
                threading.Thread(target=traffic_change_thread, args=(call,)).start()
                continue
            threading.Thread(target=host_thread, args=(call,)).start()
        
        #here we wait untill all the waitOutput threads are finished, indicating that all flows are done
        for t in wait_threads:
            t.join()

        #stop_tcpdump()  
        printDebug3("All flows have finished")
        
        for monitor in self.qmonitors:
            if monitor is not None:
                monitor.terminate()
                
        if self.sysstat:
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
        printBlueFill(f"Sending command '{cmd}' to host {node.name}")
        node.sendCmd(cmd)

    def start_iperf_client(self, node_name: str, destination_name: str, duration: int, protocol: str, monitor_interval=1, port=5201):
        """
        Start a iperf3 client on the given node with the given destination and port at a default interval of 1 second. 
        Additioanlly, the SS script is started on the client node with a default interval of 0.01 seconds (lowest possible). 
        Later versions of iperf3 will have the rtt and cwnd in its json output.
        """
        node = self.network.get(node_name)

        sscmd = f"./ss_script.sh 0.1 {self.path}/{node.name}_ss.csv &" 
        printBlue(f'Sending command {sscmd} to host {node.name}')
        node.cmd(sscmd)

        iperfCmd = f"iperf3 -p {port} -i {monitor_interval} -C {protocol} --json -t {duration} -c {self.network.get(destination_name).IP()}" 
        printBlueFill(f'Sending command {iperfCmd} to host {node.name}')
        node.sendCmd(iperfCmd)

    def start_astraea_server(self, node_name: str, monitor_interval=1, port=44279):
        """
        Starts a one-off astraea server on the given node with the given port at a default interval of 1 second
        """
        node = self.network.get(node_name)
        cmd = f"sudo -u {USERNAME} {ASTRAEA_INSTALL_FOLDER}/src/build/bin/server --port={port} --perf-interval={monitor_interval * 1000}  --one-off --terminal-out "
        printPink(f"Sending command '{cmd}' to host {node.name}")
        node.sendCmd(cmd)

    def start_astraea_client(self, node_name: str, destination_name: str, duration: int,  monitor_interval=1, port=44279):
        node = self.network.get(node_name)
        # Might not need
        # sscmd = f"./ss_script.sh 0.1 {self.path}/{node.name}_ss.csv &" 
        # printBlue(f'Sending command {sscmd} to host {node.name}')
        # node.cmd(sscmd)

        cmd = f"sudo  -u {USERNAME} {ASTRAEA_INSTALL_FOLDER}/src/build/bin/client_eval --ip={self.network.get(destination_name).IP()} --port={port} --cong=astraea --interval=30  --terminal-out --pyhelper={ASTRAEA_INSTALL_FOLDER}/python/infer.py --model={ASTRAEA_INSTALL_FOLDER}/models/py/ --duration={duration} --id={self.astraea_flows_counter} "
        printPinkFill(f"Sending command '{cmd}' to host {node.name}")
        node.sendCmd(cmd)
        self.astraea_flows_counter+= 1


    def start_orca_sender(self, node_name: str, duration: int, port=4444):
        """
        Start the orca sender on the given node with the given duration and port. Also starts a SS script on the node with an interval of 0.01 seconds for the rtt and cwnd.
        """
        node = self.network.get(node_name)
        
        sscmd = f"./ss_script.sh 0.1 {(self.path + '/' + node.name + '_ss.csv')} &"
        printGreenFill(f"Sending command '{sscmd}' to host {node.name}")
        node.cmd(sscmd)
        
        orcacmd = f"sudo -u {USERNAME} EXPERIMENT_PATH={self.path} {ORCA_INSTALL_FOLDER}/sender.sh {port} {self.orca_flows_counter} {duration}"  
        printGreen(f"Sending command '{orcacmd}' to host {node.name}")
        node.sendCmd(orcacmd)

        # global flow counter for orca flows
        self.orca_flows_counter+= 1 

    def start_orca_receiver(self, node_name: str, destination_name: str, port=4444):
        """
        Start the orca receiver on the given node with the given destination and port.
        """
        node = self.network.get(node_name)
        destination = self.network.get(destination_name)

        orcacmd = f"sudo -u {USERNAME} {ORCA_INSTALL_FOLDER}/receiver.sh {destination.IP()} {port} {0}"
        printGreenFill(f"Sending command '{orcacmd}' to host {node.name}")
        node.sendCmd(orcacmd)


    def start_sage_sender(self, node_name, duration, port=5555):
        node = self.network.get(node_name)
        sscmd = f"./ss_script.sh 0.01 {(self.path + '/' + node.name + '_ss.csv')} &"
        printPurple(f"Sending command '{sscmd}' to host {node.name}")
        node.cmd(sscmd)

        sagecmd = f"sudo -u {USERNAME}  EXPERIMENT_PATH={self.path} {SAGE_INSTALL_FOLDER}/sender.sh {port} {self.sage_flows_counter} {duration}" 
        printPurple(f"Sending command '{sagecmd}' to host {node.name}")
        node.sendCmd(sagecmd)
        
        self.sage_flows_counter+= 1 

    def start_sage_receiver(self, node_name, destination_name, port=5555):
        node = self.network.get(node_name)
        destination = self.network.get(destination_name)
        sagecmd = f"sudo -u {USERNAME} {SAGE_INSTALL_FOLDER}/receiver.sh {destination.IP()} {port} {0}"
        printPurple(f"Sending command '{sagecmd}' to host {node.name}" )
        node.sendCmd(sagecmd)

    def start_aurora_client(self, node_name, destination_name, duration, model_path, port=9000, perf_interval=1):
        node = self.network.get(node_name)
        destination = self.network.get(destination_name)
        auroracmd = f"sudo -u {USERNAME} EXPERIMENT_PATH={self.path} LD_LIBRARY_PATH=$LD_LIBRARY_PATH:{PCC_USPACE_INSTALL_FOLDER}/src/core {PCC_USPACE_INSTALL_FOLDER}/src/app/pccclient send {destination.IP()} {port} {perf_interval} {duration} --pcc-rate-control=python3 -pyhelper=loaded_client -pypath={PCC_RL_INSTALL_FOLDER}/src/udt-plugins/testing/ --history-len=10 --pcc-utility-calc=linear --model-path={model_path}"        
        print(f"Sending command '{auroracmd}' to host {node.name}")
        node.sendCmd(auroracmd)

    def start_aurora_server(self, node_name, duration, port=9000, perf_interval=1):
        node = self.network.get(node_name)
        auroracmd = f"sudo -u {USERNAME} LD_LIBRARY_PATH=$LD_LIBRARY_PATH:{PCC_USPACE_INSTALL_FOLDER}/src/core {PCC_USPACE_INSTALL_FOLDER}/src/app/pccserver recv {port} {perf_interval} {duration}"
        print("Sending command '%s' to host %s" % (auroracmd, node.name))
        node.sendCmd(auroracmd)

    def dump_info(self):
        emulation_info = {}
        emulation_info['topology'] = str(self.network.topo)
        flows = []
        for config in self.traffic_config:
            flow = [config.source, config.dest, self.network.get(config.source).IP(), self.network.get(config.dest).IP(), config.start, config.duration, config.protocol, config.params]
            flows.append(flow)
        emulation_info['flows'] = flows
        with open(self.path + "/emulation_info.json", 'w') as fout:
            json.dump(emulation_info,fout)

