from core.utils import *
from core.monitor import *
from multiprocessing import Process
from core.config import *
import time
import json

class Emulation:
    def __init__(self, network, network_config = None, traffic_config = None, path='.'):
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

    
        self.waitoutput = []
        self.call_first = []
        self.call_second = []
        self.path = path
        self.qmonitors = []
        self.tcp_probe = False

        self.orca_flows_counter = 0
        self.sage_flows_counter = 0

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
                print("Running the following command in root terminal: %s" % cmd)
                # os.system("sudo tc qdisc del dev %s  root 2> /dev/null" % intf_name)
                os.system(cmd)
            else:
                print("Running the following command in %s's terminal: %s" % (node.name, cmd))
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

            if protocol != 'tbf' and protocol != 'netem':
                self.waitoutput.append(source_node)
                self.waitoutput.append(destination)

                self.sending_nodes.append(source_node)
                self.receiving_nodes.append(destination)
            # ANSI escape code for green color
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
                params = (destination,)
                command = self.start_iperf_server
                self.call_first.append(Command(command, params, None))

                # Create client start up call
                params = (source_node,destination,duration, protocol)
                command = self.start_iperf_client
                self.call_second.append(Command(command, params, start_time - previous_start_time))

            else:
                print("ERROR: Protocol %s not recognised. Terminating..." % (protocol))


            previous_start_time = start_time

    def run(self):
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
            time.sleep(call.waiting_time)
            call.command(*call.params)

        for node_name in self.waitoutput:
            host = self.network.get(node_name)
            
            print(host)
            output = host.waitOutput()

            mkdirp(self.path)
            with open( '%s/%s_output.txt' % (self.path, node_name), 'w') as fout:
                fout.write(output)
        
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
                

    def start_iperf_server(self, node_name, port=5201, monitor_interval=1):
        node = self.network.get(node_name)
        iperfArgs = 'iperf3 -p %d -i %s --one-off --json ' % (port, monitor_interval)
        cmd = iperfArgs + '-s' 
        print("\033[94mSending command '%s' to host %s\033[0m" % (cmd, node.name))
        node.sendCmd(cmd)

    def start_iperf_client(self, node_name, destination_name, duration, protocol, port=5201, monitor_interval=1):
        node = self.network.get(node_name)

        sscmd = './ss_script.sh 0.01 %s &' % (self.path + '/' + node.name + '_ss.csv')
        print("\033[94mSending command '%s' to host %s\033[0m" % (sscmd, node.name))
        node.cmd(sscmd)

        iperfCmd = 'iperf3 -p %d -i %s -C %s --json -t %d -c %s' % (port, monitor_interval, protocol, duration, self.network.get(destination_name).IP())
        print("\033[94mSending command '%s' to host %s\033[0m" % (iperfCmd, node.name))
        node.sendCmd(iperfCmd)


    def start_orca_sender(self,node_name, duration, port=4444):
        node = self.network.get(node_name)
        
        orcacmd = 'sudo -u %s  EXPERIMENT_PATH=%s %s/sender.sh %s %s %s ' % (USERNAME, self.path, ORCA_INSTALL_FOLDER, port,  self.orca_flows_counter, duration)
        sscmd = './ss_script.sh 0.01 %s &' % (self.path + '/' + node.name + '_ss.csv')

        print("\033[92mSending command '%s' to host %s\033[0m" % (orcacmd, node.name))
        node.cmd(sscmd)
        print("\033[93mSending command '%s' to host %s\033[0m" % (sscmd, node.name))
        node.sendCmd(orcacmd)
        self.orca_flows_counter+= 1 

    def start_orca_receiver(self, node_name, destination_name, port=4444):
        node = self.network.get(node_name)
        destination = self.network.get(destination_name)
        orcacmd = 'sudo -u %s %s/receiver.sh %s %s %s' % (USERNAME,ORCA_INSTALL_FOLDER,destination.IP(), port, 0)
        print("\033[92mSending command '%s' to host %s\033[0m" % (orcacmd, node.name))
        node.sendCmd(orcacmd)


    def start_sage_sender(self,node_name, duration, port=5555):
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
        auroracmd = 'sudo -u %s EXPERIMENT_PATH=%s LD_LIBRARY_PATH=$LD_LIBRARY_PATH:%s/src/core %s/src/app/pccclient send %s %s %s %s --pcc-rate-control=python3.7 -pyhelper=loaded_client -pypath=%s/src/udt-plugins/testing/ --history-len=10 --pcc-utility-calc=linear --model-path=%s' % (USERNAME, self.path, PCC_USPACE_INSTALL_FOLDER, PCC_USPACE_INSTALL_FOLDER, destination.IP(), port, perf_interval, duration, PCC_RL_INSTALL_FOLDER, model_path)        
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

