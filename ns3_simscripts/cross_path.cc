#include "ns3/core-module.h"
#include "ns3/network-module.h"
#include "ns3/internet-module.h"
#include "ns3/point-to-point-module.h"
#include "ns3/applications-module.h"
#include "ns3/ipv4-global-routing-helper.h"
#include "ns3/flow-monitor-module.h"
#include "ns3/flow-monitor-helper.h"
#include "ns3/traffic-control-module.h"
#include <iostream>
#include <fstream>
#include <cstdio>
#include <iomanip>
#include <unordered_map>
#include <sys/stat.h>
#include <nlohmann/json.hpp>

using json = nlohmann::json;

#define COUT(log) std::cout << log << std::endl;

using namespace ns3;
AsciiTraceHelper ascii;
std::string outpath = "/home/mihai/ns-3-dev/scratch/cross_path/";


struct Change {
    double time;
    std::string type;
    double value;
};

struct Flow {
    std::string src;
    std::string dest;
    int start_time;
    int duration;
    std::string congestion_control;
};

struct ParsedData {
    std::vector<Flow> flows;
    std::vector<Change> changes;
};

ParsedData parseData(const std::string &file_path) {

    ParsedData parsedData;
    std::ifstream file(file_path);
    json data;
    file >> data;

    for (const auto &flow_data : data["flows"]) {
        Flow flow;
        flow.src = flow_data[0];
        flow.dest = flow_data[1];
        flow.start_time = flow_data[4];
        flow.duration = flow_data[5];
        flow.congestion_control = flow_data[6];
        if (flow_data[7].is_null()) {
            flow.congestion_control[0] = std::toupper(flow.congestion_control[0]);
            flow.congestion_control = "Tcp" + flow.congestion_control;
            parsedData.flows.push_back(flow);
        }
        else{
            if (flow.congestion_control == "tbf"){
                Change change;
                change.time = flow.start_time;
                change.type = "bw";
                change.value = flow_data[7][1];
                parsedData.changes.push_back(change);
            }
            else if (flow.congestion_control == "netem"){
                Change delay, loss;
                loss.time = delay.time = flow.start_time;
                loss.type = "loss";
                delay.type = "delay";
                delay.value = flow_data[7][2];
                if (flow_data[7][6].is_null())
                    loss.value = 0;
                else
                    loss.value = flow_data[7][6];
                parsedData.changes.push_back(delay);
                parsedData.changes.push_back(loss);
            }
        }
    }
    return parsedData;
}

static void
uint32Tracer(Ptr<OutputStreamWrapper> stream, uint32_t, uint32_t newval)
{
    if (newval == 2147483647){
            *stream->GetStream() 
        << Simulator::Now().GetSeconds() 
        << ", " 
        << 0 
        << std::endl;
        return;
    }

    *stream->GetStream() 
        << Simulator::Now().GetSeconds() 
        << ", " 
        << newval 
        << std::endl;
}


static void
doubleTracer(Ptr<OutputStreamWrapper> stream, double, double newval)
{
    *stream->GetStream() 
        << Simulator::Now().GetSeconds() 
        << ", " 
        << newval 
        << std::endl;
}
static void
DataRateTracer(Ptr<OutputStreamWrapper> stream, DataRate, DataRate newval)
{
    *stream->GetStream() 
        << Simulator::Now().GetSeconds() 
        << ", " << newval.GetBitRate() 
        << std::endl;
}

static void
TimeTracer(Ptr<OutputStreamWrapper> stream, Time, Time newval)
{
    *stream->GetStream() 
        << Simulator::Now().GetSeconds() 
        << ", " 
        << newval.GetMilliSeconds() 
        << std::endl;
}

ParsedData traffic_config;


std::vector<double> rxBytes;
std::vector<double> rxBytes2;

void ReceivedPacket(uint32_t flowID, Ptr<const Packet> p, const Address& addr) {
    rxBytes[flowID] += p->GetSize();
}
void ReceivedPacket2(uint32_t flowID, Ptr<const Packet> p, const Address& addr) {
    rxBytes2[flowID] += p->GetSize();
}

static void
TraceGoodput(Ptr<OutputStreamWrapper> stream, uint32_t flowID, uint32_t prevRxBytes, Time prevTime) {
    *stream->GetStream()
        << Simulator::Now().GetSeconds()
        << ", "
        << 8 * (rxBytes[flowID] - prevRxBytes) / (1000000 * (Simulator::Now().GetSeconds() - prevTime.GetSeconds()))
        << std::endl;
    Simulator::Schedule(Seconds(1), &TraceGoodput, stream, flowID, rxBytes[flowID], Simulator::Now());
}

static void
TraceGoodput2(Ptr<OutputStreamWrapper> stream, uint32_t flowID, uint32_t prevRxBytes, Time prevTime) {
    *stream->GetStream()
        << Simulator::Now().GetSeconds()
        << ", "
        << 8 * (rxBytes2[flowID] - prevRxBytes) / (1000000 * (Simulator::Now().GetSeconds() - prevTime.GetSeconds()))
        << std::endl;
    Simulator::Schedule(Seconds(1), &TraceGoodput2, stream, flowID, rxBytes2[flowID], Simulator::Now());
}

static void
socketTrace(uint32_t idx, std::string varName, std::string path, auto callback)
{
    Ptr<OutputStreamWrapper> fstream = ascii.CreateFileStream(outpath + "bbr" + std::string("-") + std::to_string(idx+1) + "-" + varName +".csv");
    *fstream->GetStream() << "time," << varName << std::endl;
    Config::ConnectWithoutContext("/NodeList/" + std::to_string(idx) + 
                                "/$ns3::TcpL4Protocol/SocketList/0/" + path, 
                                MakeBoundCallback(callback,fstream));
}


void RerouteTraffic(uint32_t numClients, std::vector<Ipv4InterfaceContainer> clients, std::vector<Ipv4InterfaceContainer> servers, 
                    Ptr<Node> router1_2, Ptr<Node> router2_2, const Ipv4InterfaceContainer& interfaces1, const Ipv4InterfaceContainer& interfaces2, bool back) 
{
    Ipv4StaticRoutingHelper routingHelper;
    Ptr<Ipv4StaticRouting> router1_2Routing = routingHelper.GetStaticRouting(router1_2->GetObject<Ipv4>());
    Ptr<Ipv4StaticRouting> router2_2Routing = routingHelper.GetStaticRouting(router2_2->GetObject<Ipv4>());
    
    for (uint32_t i = 0; i < numClients; ++i) {
        router1_2Routing->RemoveRoute(router1_2Routing->GetNRoutes()-1);
        router2_2Routing->RemoveRoute(router2_2Routing->GetNRoutes()-1);
    }


    if (back){
        for (uint32_t i = 0; i < numClients; ++i) {
            router1_2Routing->AddNetworkRouteTo(servers[i].GetAddress(1), Ipv4Mask("255.255.255.0"), interfaces1.GetAddress(1), interfaces1.Get(0).second);
            router2_2Routing->AddNetworkRouteTo(clients[i].GetAddress(0), Ipv4Mask("255.255.255.0"), interfaces2.GetAddress(1), interfaces2.Get(1).second);
            //COUT(servers[i].GetAddress(0) <<  " " << interfaces1.GetAddress(1) << " " << interfaces2.Get(1).second);

        }
    }
    else if (!back){
        for (uint32_t i = 0; i < numClients; ++i) {

            router1_2Routing->AddNetworkRouteTo(servers[i].GetAddress(1), Ipv4Mask("255.255.255.0"), interfaces1.GetAddress(1), numClients+1);
            router2_2Routing->AddNetworkRouteTo(clients[i].GetAddress(0), Ipv4Mask("255.255.255.0"), interfaces2.GetAddress(0), 1);
        }
    }
}


int main(int argc, char *argv[]) {
    Config::SetDefault("ns3::TcpL4Protocol::SocketType", TypeIdValue(TypeId::LookupByName("ns3::TcpBbr")));
    double duration = 40.0;
    uint32_t numClients = 2;
    uint32_t queue_size = 9000;
    std::string bottleneckBw = "10Mbps";
    std::string bottleneckDelay = "10ms";
    int packetSize = 1448;
        
    // linux default send 4096   16384   4194304
    // linux default recv 4096   131072  6291456
    Config::SetDefault("ns3::TcpSocket::SndBufSize", UintegerValue(4194304));
    Config::SetDefault("ns3::TcpSocket::RcvBufSize", UintegerValue(4194304));
    Config::SetDefault("ns3::TcpSocket::InitialCwnd", UintegerValue(10)); 
    Config::SetDefault("ns3::TcpSocket::InitialSlowStartThreshold", UintegerValue(10)); 
    Config::SetDefault("ns3::TcpSocket::DelAckCount", UintegerValue(0));
    Config::SetDefault("ns3::TcpSocket::SegmentSize", UintegerValue(packetSize));
    Config::SetDefault("ns3::TcpSocketState::EnablePacing", BooleanValue(true));
    Config::SetDefault("ns3::TcpL4Protocol::RecoveryType", TypeIdValue(TypeId::LookupByName("ns3::TcpClassicRecovery")));    
    Config::SetDefault("ns3::TcpSocketBase::Sack", BooleanValue(true)); 



    CommandLine cmd;
    cmd.AddValue("numClients", "Number of client-server pairs", numClients);
    // cmd.AddValue("configJSON", "json cofig file", json_file);
    // cmd.AddValue("path", "output directory", outpath);
    // cmd.AddValue("delay", "delay in ms", bottleneck_delay);
    // cmd.AddValue("bandwidth", "bandwidth in mbps", bottleneck_bw);
    // cmd.AddValue("queuesize", "multiple of bdp for queues", queue_size);
    // cmd.AddValue("seed", "append a flow", seed);
    // cmd.AddValue("delay2", "the base flows rtt ", bottleneck_delay2);
    cmd.Parse(argc, argv);
    // SeedManager::SetSeed(seed);






    NodeContainer clients_1;
    clients_1.Create(numClients);
    NodeContainer servers_1;
    servers_1.Create(numClients);
    Ptr<Node> router1_1 = CreateObject<Node>();
    Ptr<Node> router2_1 = CreateObject<Node>();

    NodeContainer clients_2;
    clients_2.Create(numClients);
    NodeContainer servers_2;
    servers_2.Create(numClients);
    Ptr<Node> router1_2 = CreateObject<Node>();
    Ptr<Node> router2_2 = CreateObject<Node>();

    PointToPointHelper clientLink, bottleneckLink, serverLink;
    clientLink.SetDeviceAttribute("DataRate", StringValue("100Gbps"));
    clientLink.SetChannelAttribute("Delay", StringValue(bottleneckDelay));
    clientLink.SetQueue("ns3::DropTailQueue", "MaxSize", QueueSizeValue(QueueSize(std::to_string(queue_size) + "p")));

    bottleneckLink.SetDeviceAttribute("DataRate", StringValue(bottleneckBw));
    bottleneckLink.SetChannelAttribute("Delay", StringValue("0ms"));
    bottleneckLink.SetQueue("ns3::DropTailQueue", "MaxSize", QueueSizeValue(QueueSize(std::to_string(queue_size) + "p")));

    serverLink.SetDeviceAttribute("DataRate", StringValue("100Gbps"));
    serverLink.SetChannelAttribute("Delay", StringValue("0ms"));
    serverLink.SetQueue("ns3::DropTailQueue", "MaxSize", QueueSizeValue(QueueSize(std::to_string(queue_size) + "p")));


    InternetStackHelper internet;
    internet.InstallAll();

    router1_1->GetObject<Ipv4>()->SetAttribute("IpForward", BooleanValue(true));
    router2_1->GetObject<Ipv4>()->SetAttribute("IpForward", BooleanValue(true));
    router1_2->GetObject<Ipv4>()->SetAttribute("IpForward", BooleanValue(true));
    router2_2->GetObject<Ipv4>()->SetAttribute("IpForward", BooleanValue(true));

    Ipv4AddressHelper ipv4_1, ipv4_2;
    ipv4_1.SetBase("10.1.0.0", "255.255.255.0");
    ipv4_2.SetBase("10.2.0.0", "255.255.255.0");
    std::vector<Ipv4InterfaceContainer> clientInterfaces_1, serverInterfaces_1, clientInterfaces_2, serverInterfaces_2;

    for (uint32_t i = 0; i < numClients; ++i) {
        NetDeviceContainer link_1 = clientLink.Install(clients_1.Get(i), router1_1);
        Ipv4InterfaceContainer iface_1 = ipv4_1.Assign(link_1);
        clientInterfaces_1.push_back(iface_1);
        ipv4_1.NewNetwork();

        NetDeviceContainer link_2 = clientLink.Install(clients_2.Get(i), router1_2);
        Ipv4InterfaceContainer iface_2 = ipv4_2.Assign(link_2);
        clientInterfaces_2.push_back(iface_2);
        ipv4_2.NewNetwork();
    }

    NetDeviceContainer bottleneckDevices_1 = bottleneckLink.Install(router1_1, router2_1);
    NetDeviceContainer bottleneckDevices_2 = bottleneckLink.Install(router1_2, router2_2);

    ipv4_1.SetBase("11.1.0.0", "255.255.255.0");
    ipv4_2.SetBase("11.2.0.0", "255.255.255.0");
    Ipv4InterfaceContainer bottleneckInterfaces_1 = ipv4_1.Assign(bottleneckDevices_1);
    Ipv4InterfaceContainer bottleneckInterfaces_2 = ipv4_2.Assign(bottleneckDevices_2);

    ipv4_1.SetBase("10.3.0.0", "255.255.255.0");
    ipv4_2.SetBase("10.4.0.0", "255.255.255.0");

    for (uint32_t i = 0; i < numClients; ++i) {
        NetDeviceContainer link_1 = serverLink.Install(router2_1, servers_1.Get(i));
        Ipv4InterfaceContainer iface_1 = ipv4_1.Assign(link_1);
        serverInterfaces_1.push_back(iface_1);
        ipv4_1.NewNetwork();

        NetDeviceContainer link_2 = serverLink.Install(router2_2, servers_2.Get(i));
        Ipv4InterfaceContainer iface_2 = ipv4_2.Assign(link_2);
        serverInterfaces_2.push_back(iface_2);
        ipv4_2.NewNetwork();
    }
    
    // Create cross-links
    NetDeviceContainer crossLink1 = bottleneckLink.Install(router1_2, router1_1);
    NetDeviceContainer crossLink2 = bottleneckLink.Install(router2_2, router2_1);

    // Assign IPs for cross-links
    Ipv4AddressHelper crossIps1, crossIps2;
    crossIps1.SetBase("12.1.0.0", "255.255.255.0");
    crossIps2.SetBase("12.2.0.0", "255.255.255.0");
    Ipv4InterfaceContainer crossInterfaces1 = crossIps1.Assign(crossLink1);
    Ipv4InterfaceContainer crossInterfaces2 = crossIps2.Assign(crossLink2);

    // Use global routing
    //Ipv4GlobalRoutingHelper::PopulateRoutingTables();
    Ipv4StaticRoutingHelper routingHelper;

    for (uint32_t i = 0; i < numClients; ++i) {
        Ptr<Ipv4StaticRouting> clientRouting_1 = routingHelper.GetStaticRouting(clients_1.Get(i)->GetObject<Ipv4>());
        Ptr<Ipv4StaticRouting> router1Routing_1 = routingHelper.GetStaticRouting(router1_1->GetObject<Ipv4>());
        Ptr<Ipv4StaticRouting> router2Routing_1 = routingHelper.GetStaticRouting(router2_1->GetObject<Ipv4>());
        Ptr<Ipv4StaticRouting> serverRouting_1 = routingHelper.GetStaticRouting(servers_1.Get(i)->GetObject<Ipv4>());

        clientRouting_1->AddNetworkRouteTo(serverInterfaces_1[i].GetAddress(1), Ipv4Mask("255.255.255.0"), bottleneckInterfaces_1.GetAddress(0), 1);

        router1Routing_1->AddNetworkRouteTo(serverInterfaces_1[i].GetAddress(1), Ipv4Mask("255.255.255.0"), bottleneckInterfaces_1.GetAddress(1), numClients+1);
        router1Routing_1->AddNetworkRouteTo(serverInterfaces_2[i].GetAddress(1), Ipv4Mask("255.255.255.0"), bottleneckInterfaces_1.GetAddress(1), numClients+1);  
        router1Routing_1->AddNetworkRouteTo(clientInterfaces_2[i].GetAddress(0), Ipv4Mask("255.255.255.0"), crossInterfaces1.GetAddress(0), crossInterfaces1.Get(0).second); 

        router2Routing_1->AddNetworkRouteTo(clientInterfaces_1[i].GetAddress(0), Ipv4Mask("255.255.255.0"), bottleneckInterfaces_1.GetAddress(0), 1);
        router2Routing_1->AddNetworkRouteTo(clientInterfaces_2[i].GetAddress(0), Ipv4Mask("255.255.255.0"), bottleneckInterfaces_1.GetAddress(0), 1);
        router2Routing_1->AddNetworkRouteTo(serverInterfaces_2[i].GetAddress(0), Ipv4Mask("255.255.255.0"), crossInterfaces2.GetAddress(0), crossInterfaces2.Get(0).second);

        serverRouting_1->AddNetworkRouteTo(clientInterfaces_1[i].GetAddress(0), Ipv4Mask("255.255.255.0"), bottleneckInterfaces_1.GetAddress(1), 1);

        Ptr<Ipv4StaticRouting> clientRouting_2 = routingHelper.GetStaticRouting(clients_2.Get(i)->GetObject<Ipv4>());
        Ptr<Ipv4StaticRouting> router1Routing_2 = routingHelper.GetStaticRouting(router1_2->GetObject<Ipv4>());  
        Ptr<Ipv4StaticRouting> router2Routing_2 = routingHelper.GetStaticRouting(router2_2->GetObject<Ipv4>());
        Ptr<Ipv4StaticRouting> serverRouting_2 = routingHelper.GetStaticRouting(servers_2.Get(i)->GetObject<Ipv4>());

        clientRouting_2->AddNetworkRouteTo(serverInterfaces_2[i].GetAddress(1), Ipv4Mask("255.255.255.0"), bottleneckInterfaces_1.GetAddress(0), 1);

        router1Routing_2->AddNetworkRouteTo(serverInterfaces_2[i].GetAddress(1), Ipv4Mask("255.255.255.0"), bottleneckInterfaces_2.GetAddress(1), numClients+1);

        router2Routing_2->AddNetworkRouteTo(clientInterfaces_2[i].GetAddress(0), Ipv4Mask("255.255.255.0"), bottleneckInterfaces_2.GetAddress(0), 1);

        serverRouting_2->AddNetworkRouteTo(clientInterfaces_2[i].GetAddress(0), Ipv4Mask("255.255.255.0"), bottleneckInterfaces_1.GetAddress(1), 1);
    }





    AsciiTraceHelper ascii;
    Ipv4GlobalRoutingHelper::PrintRoutingTableAllAt(Seconds(1), ascii.CreateFileStream("scratch/cross_path/routes_seconds_1.txt"));
    Ipv4GlobalRoutingHelper::PrintRoutingTableAllAt(Seconds(15), ascii.CreateFileStream("scratch/cross_path/routes_seconds_15.txt"));
    Ipv4GlobalRoutingHelper::PrintRoutingTableAllAt(Seconds(35), ascii.CreateFileStream("scratch/cross_path/routes_seconds_35.txt"));
    // Set up applications
    uint16_t basePort = 8080;
    rxBytes.resize(numClients, 0);
    rxBytes2.resize(numClients, 0);

    for (uint32_t i = 0; i < numClients; ++i) {
        Address serverAddress_1(InetSocketAddress(serverInterfaces_1[i].GetAddress(1), basePort + i));
        BulkSendHelper bulkSend_1("ns3::TcpSocketFactory", serverAddress_1);
        bulkSend_1.SetAttribute("MaxBytes", UintegerValue(0));

        Address serverAddress_2(InetSocketAddress(serverInterfaces_2[i].GetAddress(1), basePort + i));
        BulkSendHelper bulkSend_2("ns3::TcpSocketFactory", serverAddress_2);
        bulkSend_2.SetAttribute("MaxBytes", UintegerValue(0));

        ApplicationContainer clientApps_1 = bulkSend_1.Install(clients_1.Get(i));
        clientApps_1.Start(Seconds(0.1));
        clientApps_1.Stop(Seconds(duration));

        ApplicationContainer clientApps_2 = bulkSend_2.Install(clients_2.Get(i));
        clientApps_2.Start(Seconds(0.1));
        clientApps_2.Stop(Seconds(duration));

        Simulator::Schedule(Seconds(0.1) + MilliSeconds(1), &socketTrace<decltype(&TimeTracer)>, clients_1.Get(i)->GetId(), "rtt", "RTT",  &TimeTracer);
        Simulator::Schedule(Seconds(0.1) + MilliSeconds(1), &socketTrace<decltype(&TimeTracer)>, clients_2.Get(i)->GetId(), "rtt", "RTT",  &TimeTracer);


        PacketSinkHelper packetSinkHelper_1("ns3::TcpSocketFactory", InetSocketAddress(Ipv4Address::GetAny(), basePort + i));
        ApplicationContainer serverApps_1 = packetSinkHelper_1.Install(servers_1.Get(i));
        serverApps_1.Start(Seconds(0.1));
        serverApps_1.Stop(Seconds(duration));

        PacketSinkHelper packetSinkHelper_2("ns3::TcpSocketFactory", InetSocketAddress(Ipv4Address::GetAny(), basePort + i));
        ApplicationContainer serverApps_2 = packetSinkHelper_2.Install(servers_2.Get(i));
        serverApps_2.Start(Seconds(0.1));
        serverApps_2.Stop(Seconds(duration));

        Ptr<PacketSink> sink_1 = DynamicCast<PacketSink>(serverApps_1.Get(0));
        sink_1->TraceConnectWithoutContext("Rx", MakeBoundCallback(&ReceivedPacket, i));
        Ptr<PacketSink> sink_2 = DynamicCast<PacketSink>(serverApps_2.Get(0));
        sink_2->TraceConnectWithoutContext("Rx", MakeBoundCallback(&ReceivedPacket2, i));

        Ptr<OutputStreamWrapper> goodputStream_1 = ascii.CreateFileStream("scratch/cross_path/Goodput_1_" + std::to_string(i + 1) + ".csv");
        *goodputStream_1->GetStream() << "time,goodput\n";
        Simulator::Schedule(Seconds(1), &TraceGoodput, goodputStream_1, i, 0, Seconds(0));

        Ptr<OutputStreamWrapper> goodputStream_2 = ascii.CreateFileStream("scratch/cross_path/Goodput_2_" + std::to_string(i + 1) + ".csv");
        *goodputStream_2->GetStream() << "time,goodput\n";
        Simulator::Schedule(Seconds(1), &TraceGoodput2, goodputStream_2, i, 0, Seconds(0));
    }

    Simulator::Schedule(Seconds(10), &RerouteTraffic, numClients, clientInterfaces_2, serverInterfaces_2, router1_2, router2_2, crossInterfaces1, crossInterfaces2, true);
    Simulator::Schedule(Seconds(30), &RerouteTraffic, numClients, clientInterfaces_2, serverInterfaces_2, router1_2, router2_2, bottleneckInterfaces_2, bottleneckInterfaces_2, false);

    bottleneckLink.EnablePcap("scratch/cross_path/r12_r11_bottleneckDevices_1", bottleneckDevices_1, true);
    bottleneckLink.EnablePcap("scratch/cross_path/r22_r21_bottleneckDevices_2", bottleneckDevices_2, true);

    Simulator::Stop(Seconds(duration));
    Simulator::Run();
    Simulator::Destroy();
    COUT("Simulation finished.");
    return 0;
}
