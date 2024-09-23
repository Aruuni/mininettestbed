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
        self.flip = False
        self.orca_flows_counter = 0
        self.sage_flows_counter = 0
        self.counter = 0

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
                printTC("Running the following command in %s's terminal: %s" % (node.name, cmd))
                # node.cmd("sudo tc qdisc del dev %s  root 2> /dev/null" % intf_name)
                node.cmd(cmd)

 

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
            protocol = flowconfig.proto

            if protocol != 'tbf' and protocol != 'netem' and protocol != 'cross_traffic':
                self.waitoutput.append(source_node)
                self.waitoutput.append(destination)

                self.sending_nodes.append(source_node)
                self.receiving_nodes.append(destination)

            if protocol == 'orca':
                params = (source_node,duration)
                command = self.start_orca_sender
                self.call_first.append(Command(command, params, None))

                params = (destination,source_node)
                command = self.start_orca_receiver
                self.call_second.append(Command(command, params, start_time - previous_start_time))

            elif protocol == 'sage':
                params = (source_node,duration)
                command = self.start_sage_sender
                self.call_first.append(Command(command, params, None))

                params = (destination,source_node)
                command = self.start_sage_receiver
                self.call_second.append(Command(command, params, start_time - previous_start_time))

            elif protocol == 'aurora':
                # Create server start up call
                params = (destination, duration)
                command = self.start_aurora_server
                self.call_first.append(Command(command, params, None))

                # Create client start up call
                params = (source_node,destination,duration,"%s/mininettestbed/saved_models/icml_paper_model" % HOME_DIR)
                command = self.start_aurora_client
                self.call_second.append(Command(command, params, start_time - previous_start_time))
                
            elif protocol == 'tbf' or protocol == 'netem':
                # Change the tbf rate to the value provided
                params = list(flowconfig.params)
                nodes_names = params[0]
                params[0] = self.network.linksBetween(self.network.get(nodes_names[0]), self.network.get(nodes_names[1]))[0]
                command = self.configure_link
                self.call_second.append(Command(command, params, start_time - previous_start_time))

            elif protocol != 'aurora' and protocol != 'orca' and protocol != 'sage':
                # Create server start up call
                params = (destination, self.interval)
                command = self.start_iperf_server
                self.call_first.append(Command(command, params, None))

                # Create client start up call
                params = (source_node,destination,duration, protocol, self.interval)
                command = self.start_iperf_client
                self.call_second.append(Command(command, params, start_time - previous_start_time))

            else:
                print("ERROR: Protocol %s not recognised. Terminating..." % (protocol))

            previous_start_time = start_time

    def run(self):
        """
        The main function that runs the experiment. It starts the servers, then the clients, and waits for all the flows to finish. The flows "finish" whent the waitOutput of the node returns the full output of its commandline output.
        Also to note: 
        1. the first flow MUST start at time 0, and any subsequent flows after that can start after, I presume that all flows haev to have an increasing start time. e.g. flow 1 start at time 0, flow 2 starts at time 10 and flow 3 at time 0 will not work.

        TODO: FIX THIS 
        """
        for call in self.call_first:
            call.command(*call.params)
        for monitor in self.qmonitors:
            monitor.start()

        if self.sysstat:
            start_sysstat(1,self.sysstat_length,self.path) 
            # run sysstat on each sender to collect ETCP and UDP stats
            for node_name in self.sending_nodes:
                start_sysstat(1,self.sysstat_length,self.path, self.network.get(node_name))

        for call in self.call_second:
            printDebug3(call.waiting_time)
            time.sleep(call.waiting_time)
            call.command(*call.params)
        

        for node_name in self.waitoutput:
            host = self.network.get(node_name)
            printDebug2("Waiting for %s to finish" % node_name)
            #printDebug3(host.waitOutput(verbose = True))
            output = host.waitOutput(verbose = True)
            mkdirp(self.path)
            with open( '%s/%s_output.txt' % (self.path, node_name), 'w') as fout:
                fout.write(output)
        printDebug2("All flows have finished")
        for monitor in self.qmonitors:
            if monitor is not None:
                monitor.terminate()

        if self.sysstat:
            stop_sysstat(self.path, self.sending_nodes)


    def set_monitors(self, monitors, interval_sec=1):
        if "sysstat" in monitors:
            self.sysstat = True
            monitors.remove("sysstat")

        for monitor in monitors:
            node, interface = monitor.split('-')
            if 's' in node:
                iface = '%s-%s' % (node, interface)
                monitor = Process(target=monitor_qlen, args=(iface, interval_sec,'%s/queues' % (self.path)))
                self.qmonitors.append(monitor)

    def shift_traffic(self, delay=3):
        printDebug3("Shifting traffic")
        print("Updating flow rules")
        self.network.configLinkStatus('s1a', 's1b', 'up')
        self.network.configLinkStatus('s3a', 's3b', 'up')
        self.network.configLinkStatus('s2b', 's3b', 'down')
        self.network.configLinkStatus('s1b', 's2b', 'down')
        node = self.network.get('s1a')
        printDebug3(node.cmd('ifconfig'))
        #self.network.configLinkStatus('s1a', 's1b', 'down')
        print("Link Status:")
        for link in self.network.links:
            intf1 = link.intf1
            intf2 = link.intf2
            status1 = self.network.configLinkStatus(intf1.node, intf2.node, 'status')
            print(f"{intf1.node}-{intf1} <-> {intf2.node}-{intf2} : {status1}")

    def start_handovers(self, delay, interval=15):
        printDebug(f"Starting handovers total duration is {self.sysstat_length} seconds")
        self.counter += 1
        
        # Perform the handover
        self.network.configLinkStatus('s1', 's2', 'down')
        threading.Timer(delay * 3 / 1000, self.network.configLinkStatus, args=('s1', 's2', 'up')).start()
        
        # Schedule the next handover after `interval` seconds
        if (self.counter * interval) < self.sysstat_length:
            threading.Timer(interval, self.start_handovers, args=[delay, interval]).start()


    def start_iperf_server(self, node_name: str, monitor_interval=1, port=5201):
        """
        Start a one off iperf3 server on the given node with the given port at a default interval of 1 second
        """
        node = self.network.get(node_name)
        cmd = f"iperf3 -p {port} -i {monitor_interval} --one-off --json -s"
        printIperf3(f"Sending command '{cmd}' to host {node.name}")
        node.sendCmd(cmd)

    def start_iperf_client(self, node_name: str, destination_name: str, duration: int, protocol: str, monitor_interval=1, port=5201):
        """
        Start a iperf3 client on the given node with the given destination and port at a default interval of 1 second. 
        Additioanlly, the SS script is started on the client node with a default interval of 0.01 seconds (lowest possible). 
        Later versions of iperf3 will have the rtt and cwnd in its json output.
        """
        node = self.network.get(node_name)

        sscmd = f"./ss_script.sh 0.01 {self.path}/{node.name}_ss.csv &" 
        printIperf3SS(f'Sending command {sscmd} to host {node.name}')
        node.cmd(sscmd)

        iperfCmd = f"iperf3 -p {port} -i {monitor_interval} -C {protocol} --json -t {duration} -c {self.network.get(destination_name).IP()}" 
        printIperf3(f'Sending command {iperfCmd} to host {node.name}')
        node.sendCmd(iperfCmd)


    def start_orca_sender(self, node_name: str, duration: int, port=4444):
        """
        Start the orca sender on the given node with the given duration and port. Also starts a SS script on the node with an interval of 0.01 seconds for the rtt and cwnd.
        """
        node = self.network.get(node_name)
        
        sscmd = f"./ss_script.sh 0.01 {(self.path + '/' + node.name + '_ss.csv')} &"
        printOrcaSS(f"Sending command '{orcacmd}' to host {node.name}")
        node.cmd(sscmd)
        
        orcacmd = f"sudo -u {USERNAME} EXPERIMENT_PATH={self.path} {ORCA_INSTALL_FOLDER}/sender.sh {port} {self.orca_flows_counter} {duration}"  
        printOrca(f"Sending command '{sscmd}' to host {node.name}")
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
        printOrca(f"Sending command '{orcacmd}' to host {node.name}")
        node.sendCmd(orcacmd)


    def start_sage_sender(self, node_name, duration, port=5555):
        node = self.network.get(node_name)
        
        sagecmd = 'sudo -u %s  EXPERIMENT_PATH=%s %s/sender.sh %s %s %s' % (USERNAME, self.path, SAGE_INSTALL_FOLDER, port, self.sage_flows_counter, duration)
        sscmd = './ss_script.sh 0.01 %s &' % (self.path + '/' + node.name + '_ss.csv')

        print("\033[35mSending command '%s' to host %s\033[0m" % (sagecmd, node.name))
        node.cmd(sscmd)
        print("\033[93mSending command '%s' to host %s\033[0m" % (sscmd, node.name))
        node.sendCmd(sagecmd)
        self.sage_flows_counter+= 1 

    def start_sage_receiver(self, node_name, destination_name, port=5555):
        node = self.network.get(node_name)
        destination = self.network.get(destination_name)
        sagecmd = 'sudo -u %s %s/receiver.sh %s %s %s' % (USERNAME, SAGE_INSTALL_FOLDER,destination.IP(), port, 0)
        print("\033[35mSending command '%s' to host %s\033[0m" % (sagecmd, node.name))
        node.sendCmd(sagecmd)


    def start_aurora_client(self, node_name, destination_name, duration, model_path, port=9000, perf_interval=1):
        node = self.network.get(node_name)
        destination = self.network.get(destination_name)
        auroracmd = 'sudo -u %s EXPERIMENT_PATH=%s LD_LIBRARY_PATH=$LD_LIBRARY_PATH:%s/src/core %s/src/app/pccclient send %s %s %s %s --pcc-rate-control=python3 -pyhelper=loaded_client -pypath=%s/src/udt-plugins/testing/ --history-len=10 --pcc-utility-calc=linear --model-path=%s' % (USERNAME, self.path, PCC_USPACE_INSTALL_FOLDER, PCC_USPACE_INSTALL_FOLDER, destination.IP(), port, perf_interval, duration, PCC_RL_INSTALL_FOLDER, model_path)        
        print("Sending command '%s' to host %s" % (auroracmd, node.name))
        node.sendCmd(auroracmd)

    def start_aurora_server(self, node_name, duration, port=9000, perf_interval=1):
        node = self.network.get(node_name)
        auroracmd = 'sudo -u %s LD_LIBRARY_PATH=$LD_LIBRARY_PATH:%s/src/core %s/src/app/pccserver recv %s %s %s' % (USERNAME,PCC_USPACE_INSTALL_FOLDER,PCC_USPACE_INSTALL_FOLDER,port, perf_interval, duration)
        print("Sending command '%s' to host %s" % (auroracmd, node.name))
        node.sendCmd(auroracmd)

    def dump_info(self):
        emulation_info = {}
        emulation_info['topology'] = str(self.network.topo)
        flows = []
        for config in self.traffic_config:
            flow = [config.source, config.dest, self.network.get(config.source).IP(), self.network.get(config.dest).IP(), config.start, config.proto, config.params]
            flows.append(flow)
        emulation_info['flows'] = flows
        with open(self.path + "/emulation_info.json", 'w') as fout:
            json.dump(emulation_info,fout)

