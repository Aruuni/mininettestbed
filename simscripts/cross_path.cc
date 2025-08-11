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
std::string outpath;


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


// static void
// doubleTracer(Ptr<OutputStreamWrapper> stream, double, double newval)
// {
//     *stream->GetStream() 
//         << Simulator::Now().GetSeconds() 
//         << ", " 
//         << newval 
//         << std::endl;
// }
// static void
// DataRateTracer(Ptr<OutputStreamWrapper> stream, DataRate, DataRate newval)
// {
//     *stream->GetStream() 
//         << Simulator::Now().GetSeconds() 
//         << ", " << newval.GetBitRate() 
//         << std::endl;
// }

void
QueueSizeTrace(uint32_t nodeID, uint32_t deviceID)
{
    Ptr<OutputStreamWrapper> qtrace = ascii.CreateFileStream(outpath + "queueSize-" + std::to_string(nodeID) + "_" + std::to_string(deviceID) + ".csv");
    *qtrace->GetStream() << "time,root_pkts" << std::endl;
    Config::ConnectWithoutContext("/NodeList/" + std::to_string(nodeID) + "/DeviceList/" + std::to_string(deviceID) + 
                                  "/$ns3::PointToPointNetDevice/TxQueue/PacketsInQueue", MakeBoundCallback(&uint32Tracer, qtrace));
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
TraceThroughput(Ptr<FlowMonitor> monitor, Ptr<OutputStreamWrapper> stream, uint32_t flowID, uint32_t prevTxBytes, Time prevTime) 
{
    FlowMonitor::FlowStatsContainer stats = monitor->GetFlowStats();
    FlowMonitor::FlowStats statsNode = stats[flowID];
    *stream->GetStream() 
        << Simulator::Now().GetSeconds() 
        << ", "
        << 8 * (statsNode.txBytes - prevTxBytes) / (1000000 * (Simulator::Now().GetSeconds() - prevTime.GetSeconds()))
        //<< 8 * (statsNode.txBytes - prevTxBytes) / ((Simulator::Now().GetSeconds() - prevTime.GetSeconds()))
        << std::endl;
    Simulator::Schedule(Seconds(1), &TraceThroughput, monitor, stream, flowID, statsNode.txBytes, Simulator::Now());
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
socketTrace(uint32_t nidx, uint32_t didx, uint32_t idx, std::string varName, std::string path, auto callback)
{
    Ptr<OutputStreamWrapper> fstream = ascii.CreateFileStream(outpath + traffic_config.flows[idx].congestion_control + "-" + std::to_string(didx) + "_" + std::to_string(idx+1) + "-" + varName + ".csv");
    *fstream->GetStream() << "time," << varName << std::endl;
    Config::ConnectWithoutContext("/NodeList/" + std::to_string(nidx) + 
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
    uint32_t numClients = 2;
    int packetSize = 1448;

    int seed{123456789};
    int startTime{0};
    int bottleneck_bw_1{10};
    int bottleneck_bw_2{10};

    int bottleneck_delay_1{5};
    int bottleneck_delay_2{10};

    int queue_size_1{100};
    int queue_size_2{150};
    std::string json_file;



    CommandLine cmd;
    cmd.AddValue("numClients", "Number of client-server pairs, per dumbbell", numClients);
    cmd.AddValue("configJSON", "json cofig file", json_file);
    cmd.AddValue("path", "Output directory, sbsolute path required, if set, will create the directory", outpath);
    cmd.AddValue("delay1", "One way delay in ms of dumbbell 1", bottleneck_delay_1);
    cmd.AddValue("delay2", "One way delay in ms of dumbbell 2", bottleneck_delay_2);
    cmd.AddValue("bandwidth1", "Bandwidth in mbps of dumbbell 1", bottleneck_bw_1);
    cmd.AddValue("bandwidth2", "Bandwidth in mbps of dumbbell 2", bottleneck_bw_2);
    cmd.AddValue("queuesize1", "Queue size in packets of dumbbell 1", queue_size_1);
    cmd.AddValue("queuesize2", "Queue size in packets of dumbbell 2", queue_size_2);
    cmd.AddValue("seed", "Seed of the simulation", seed);    
    cmd.Parse(argc, argv);


    
    traffic_config = parseData(json_file);
    for (const auto& flow : traffic_config.flows) {
        if (flow.duration >= startTime){
            startTime = flow.duration;
        }
    }
    Time stopTime = Seconds(startTime);
    system(("mkdir -p "+ outpath).c_str());

    SeedManager::SetSeed(seed);
    Config::SetDefault("ns3::TcpSocket::SndBufSize", UintegerValue(4194304));
    Config::SetDefault("ns3::TcpSocket::RcvBufSize", UintegerValue(4194304));
    Config::SetDefault("ns3::TcpSocket::InitialCwnd", UintegerValue(10)); 
    Config::SetDefault("ns3::TcpSocket::InitialSlowStartThreshold", UintegerValue(10)); 
    Config::SetDefault("ns3::TcpSocket::DelAckCount", UintegerValue(0));
    Config::SetDefault("ns3::TcpSocket::SegmentSize", UintegerValue(packetSize));
    Config::SetDefault("ns3::TcpSocketState::EnablePacing", BooleanValue(true));
    Config::SetDefault("ns3::TcpL4Protocol::RecoveryType", TypeIdValue(TypeId::LookupByName("ns3::TcpClassicRecovery")));    
    Config::SetDefault("ns3::TcpSocketBase::Sack", BooleanValue(true)); 
    Config::SetDefault("ns3::TcpSocketBase::MinRto", TimeValue(MilliSeconds(200))); 

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

    PointToPointHelper clientLink_1, bottleneckLink_1, serverLink_1;
    clientLink_1.SetDeviceAttribute("DataRate", StringValue("100Gbps"));
    clientLink_1.SetChannelAttribute("Delay", TimeValue(MilliSeconds(bottleneck_delay_1)));
    clientLink_1.SetQueue("ns3::DropTailQueue", "MaxSize", QueueSizeValue(QueueSize(std::to_string(queue_size_1) + "p")));

    bottleneckLink_1.SetDeviceAttribute("DataRate", StringValue(std::to_string(bottleneck_bw_1) + "Mbps"));
    bottleneckLink_1.SetChannelAttribute("Delay", StringValue("0ms"));
    bottleneckLink_1.SetQueue("ns3::DropTailQueue", "MaxSize", QueueSizeValue(QueueSize(std::to_string(queue_size_1) + "p")));

    serverLink_1.SetDeviceAttribute("DataRate", StringValue("100Gbps"));
    serverLink_1.SetChannelAttribute("Delay", StringValue("0ms"));
    serverLink_1.SetQueue("ns3::DropTailQueue", "MaxSize", QueueSizeValue(QueueSize(std::to_string(queue_size_1) + "p")));

    PointToPointHelper clientLink_2, bottleneckLink_2, serverLink_2;
    clientLink_2.SetDeviceAttribute("DataRate", StringValue("100Gbps"));
    clientLink_2.SetChannelAttribute("Delay", TimeValue(MilliSeconds(bottleneck_delay_2)));
    clientLink_2.SetQueue("ns3::DropTailQueue", "MaxSize", QueueSizeValue(QueueSize(std::to_string(queue_size_2) + "p")));

    bottleneckLink_2.SetDeviceAttribute("DataRate", StringValue(std::to_string(bottleneck_bw_2) + "Mbps"));
    bottleneckLink_2.SetChannelAttribute("Delay", StringValue("0ms"));
    bottleneckLink_2.SetQueue("ns3::DropTailQueue", "MaxSize", QueueSizeValue(QueueSize(std::to_string(queue_size_2) + "p")));

    serverLink_2.SetDeviceAttribute("DataRate", StringValue("100Gbps"));
    serverLink_2.SetChannelAttribute("Delay", StringValue("0ms"));
    serverLink_2.SetQueue("ns3::DropTailQueue", "MaxSize", QueueSizeValue(QueueSize(std::to_string(queue_size_2) + "p")));


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
        NetDeviceContainer link_1 = clientLink_1.Install(clients_1.Get(i), router1_1);
        Ipv4InterfaceContainer iface_1 = ipv4_1.Assign(link_1);
        clientInterfaces_1.push_back(iface_1);
        ipv4_1.NewNetwork();

        NetDeviceContainer link_2 = clientLink_2.Install(clients_2.Get(i), router1_2);
        Ipv4InterfaceContainer iface_2 = ipv4_2.Assign(link_2);
        clientInterfaces_2.push_back(iface_2);
        ipv4_2.NewNetwork();
    }

    NetDeviceContainer bottleneckDevices_1 = bottleneckLink_1.Install(router1_1, router2_1);
    NetDeviceContainer bottleneckDevices_2 = bottleneckLink_2.Install(router1_2, router2_2);
    ipv4_1.SetBase("11.1.0.0", "255.255.255.0");
    ipv4_2.SetBase("11.2.0.0", "255.255.255.0");

    Ipv4InterfaceContainer bottleneckInterfaces_1 = ipv4_1.Assign(bottleneckDevices_1);
    Ipv4InterfaceContainer bottleneckInterfaces_2 = ipv4_2.Assign(bottleneckDevices_2);
    ipv4_1.SetBase("10.3.0.0", "255.255.255.0");
    ipv4_2.SetBase("10.4.0.0", "255.255.255.0");

    for (uint32_t i = 0; i < numClients; ++i) {
        NetDeviceContainer link_1 = serverLink_1.Install(router2_1, servers_1.Get(i));
        Ipv4InterfaceContainer iface_1 = ipv4_1.Assign(link_1);
        serverInterfaces_1.push_back(iface_1);
        ipv4_1.NewNetwork();

        NetDeviceContainer link_2 = serverLink_2.Install(router2_2, servers_2.Get(i));
        Ipv4InterfaceContainer iface_2 = ipv4_2.Assign(link_2);
        serverInterfaces_2.push_back(iface_2);
        ipv4_2.NewNetwork();
    }
    
    // Create cross-links
    NetDeviceContainer crossLink1 = serverLink_1.Install(router1_2, router1_1);
    NetDeviceContainer crossLink2 = serverLink_2.Install(router2_2, router2_1);


    Ipv4AddressHelper crossIps1, crossIps2;
    crossIps1.SetBase("12.1.0.0", "255.255.255.0");
    crossIps2.SetBase("12.2.0.0", "255.255.255.0");

    Ipv4InterfaceContainer crossInterfaces1 = crossIps1.Assign(crossLink1);
    Ipv4InterfaceContainer crossInterfaces2 = crossIps2.Assign(crossLink2);

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
    for (uint32_t i = 0; i < traffic_config.flows.size()/2; i++) { 
        Config::Set("/NodeList/" + std::to_string(clients_1.Get(i)->GetId()) + "/$ns3::TcpL4Protocol/SocketType", TypeIdValue(TypeId::LookupByName("ns3::" + traffic_config.flows[i].congestion_control))); 
        Config::Set("/NodeList/" + std::to_string(clients_2.Get(i)->GetId()) + "/$ns3::TcpL4Protocol/SocketType", TypeIdValue(TypeId::LookupByName("ns3::" + traffic_config.flows[i+numClients].congestion_control))); 
    }

    uint16_t basePort = 8080;
    rxBytes.resize(numClients, 0);
    rxBytes2.resize(numClients, 0);
    FlowMonitorHelper flowmonHelperSender;
    for (uint32_t i = 0; i < numClients; ++i) {
        Address serverAddress_1(InetSocketAddress(serverInterfaces_1[i].GetAddress(1), basePort + i));
        BulkSendHelper bulkSend_1("ns3::TcpSocketFactory", serverAddress_1);
        bulkSend_1.SetAttribute("MaxBytes", UintegerValue(0));

        Address serverAddress_2(InetSocketAddress(serverInterfaces_2[i].GetAddress(1), basePort + i));
        BulkSendHelper bulkSend_2("ns3::TcpSocketFactory", serverAddress_2);
        bulkSend_2.SetAttribute("MaxBytes", UintegerValue(0));

        ApplicationContainer clientApps_1 = bulkSend_1.Install(clients_1.Get(i));
        clientApps_1.Start(Seconds(traffic_config.flows[i].start_time));
        clientApps_1.Stop(Seconds(traffic_config.flows[i].duration));

        ApplicationContainer clientApps_2 = bulkSend_2.Install(clients_2.Get(i));
        clientApps_2.Start(Seconds(traffic_config.flows[i + numClients].start_time));
        clientApps_2.Stop(Seconds(traffic_config.flows[i + numClients].duration));

        Simulator::Schedule(Seconds(traffic_config.flows[i].start_time) + MilliSeconds(1), &socketTrace<decltype(&TimeTracer)>, clients_1.Get(i)->GetId(), 1, i, "rtt", "RTT",  &TimeTracer);
        Simulator::Schedule(Seconds(traffic_config.flows[i].start_time) + MilliSeconds(1), &socketTrace<decltype(&uint32Tracer)>, clients_1.Get(i)->GetId(), 1, i, "bytes", "BytesInFlight",  &uint32Tracer);
        Simulator::Schedule(Seconds(traffic_config.flows[i].start_time) + MilliSeconds(1), &socketTrace<decltype(&uint32Tracer)>, clients_1.Get(i)->GetId(), 1, i, "cwnd", "CongestionWindow",  &uint32Tracer);
        
        
        
        Simulator::Schedule(Seconds(traffic_config.flows[i + numClients].start_time) + MilliSeconds(1), &socketTrace<decltype(&TimeTracer)>, clients_2.Get(i)->GetId(), 2, i , "rtt", "RTT",  &TimeTracer);
        Simulator::Schedule(Seconds(traffic_config.flows[i + numClients].start_time) + MilliSeconds(1), &socketTrace<decltype(&uint32Tracer)>, clients_2.Get(i)->GetId(), 2, i, "bytes", "BytesInFlight",  &uint32Tracer);
        Simulator::Schedule(Seconds(traffic_config.flows[i + numClients].start_time) + MilliSeconds(1), &socketTrace<decltype(&uint32Tracer)>, clients_2.Get(i)->GetId(), 2, i, "cwnd", "CongestionWindow",  &uint32Tracer);
        
        // Simulator::Schedule(Seconds(traffic_config.flows[i].start_time) + MilliSeconds(1), &socketTrace<decltype(&uint32Tracer)>,  clients_1.Get(i)->GetId(), "bytes", "BytesInFlight",  &uint32Tracer);
        // Simulator::Schedule(Seconds(traffic_config.flows[i].start_time) + MilliSeconds(1), &socketTrace<decltype(&uint32Tracer)>,  clients_1.Get(i)->GetId(), "cwnd", "CongestionWindow", &uint32Tracer);

        PacketSinkHelper packetSinkHelper_1("ns3::TcpSocketFactory", InetSocketAddress(Ipv4Address::GetAny(), basePort + i));
        ApplicationContainer serverApps_1 = packetSinkHelper_1.Install(servers_1.Get(i));
        serverApps_1.Start(Seconds(traffic_config.flows[i].start_time));
        serverApps_1.Stop(stopTime);

        PacketSinkHelper packetSinkHelper_2("ns3::TcpSocketFactory", InetSocketAddress(Ipv4Address::GetAny(), basePort + i));
        ApplicationContainer serverApps_2 = packetSinkHelper_2.Install(servers_2.Get(i));
        serverApps_2.Start(Seconds(0.1));
        serverApps_2.Stop(stopTime);

        Ptr<PacketSink> sink_1 = DynamicCast<PacketSink>(serverApps_1.Get(0));
        sink_1->TraceConnectWithoutContext("Rx", MakeBoundCallback(&ReceivedPacket, i));
        Ptr<PacketSink> sink_2 = DynamicCast<PacketSink>(serverApps_2.Get(0));
        sink_2->TraceConnectWithoutContext("Rx", MakeBoundCallback(&ReceivedPacket2, i));

         
        Ptr<OutputStreamWrapper> goodputStream_1 = ascii.CreateFileStream(outpath + traffic_config.flows[i].congestion_control + "-1_" + std::to_string(i + 1) + "-goodput.csv");
        *goodputStream_1->GetStream() << "time,goodput\n";
        Simulator::Schedule(Seconds(1), &TraceGoodput, goodputStream_1, i, 0, Seconds(0));

        Ptr<OutputStreamWrapper> goodputStream_2 = ascii.CreateFileStream(outpath + traffic_config.flows[i + numClients].congestion_control + "-2_"+ std::to_string(i + 1) + "-goodput.csv");
        *goodputStream_2->GetStream() << "time,goodput\n";
        Simulator::Schedule(Seconds(1), &TraceGoodput2, goodputStream_2, i, 0, Seconds(0));

        Ptr<FlowMonitor> flowMonitorS_1 = flowmonHelperSender.Install(clients_1.Get(i));   
        Ptr<FlowMonitor> flowMonitorS_2 = flowmonHelperSender.Install(clients_2.Get(i));   
        Ptr<OutputStreamWrapper> throughputStream_1 = ascii.CreateFileStream(outpath + traffic_config.flows[i].congestion_control + "-1_" + std::to_string(i + 1) + "-throughput.csv");
        *throughputStream_1->GetStream() << "time,throughput\n";
        Simulator::Schedule(Seconds(1), &TraceThroughput, flowMonitorS_1, throughputStream_1, i+1, 0, Seconds(0));

        Ptr<OutputStreamWrapper> throughputStream_2 = ascii.CreateFileStream(outpath + traffic_config.flows[i + numClients].congestion_control + "-2_"+ std::to_string(i + 1) + "-throughput.csv");
        *throughputStream_2->GetStream() << "time,throughput\n";
        Simulator::Schedule(Seconds(1), &TraceThroughput, flowMonitorS_2, throughputStream_2, i+1+numClients, 0, Seconds(0));
    }
    QueueSizeTrace(router1_1->GetId(),3);
    QueueSizeTrace(router1_2->GetId(),3);

    Simulator::Schedule(Seconds(100), &RerouteTraffic, numClients, clientInterfaces_2, serverInterfaces_2, router1_2, router2_2, crossInterfaces1, crossInterfaces2, true);
    Simulator::Schedule(Seconds(200), &RerouteTraffic, numClients, clientInterfaces_2, serverInterfaces_2, router1_2, router2_2, bottleneckInterfaces_2, bottleneckInterfaces_2, false);

    // bottleneckLink.EnablePcap("scratch/cross_path/r12_r11_bottleneckDevices_1", bottleneckDevices_1, true);
    // bottleneckLink.EnablePcap("scratch/cross_path/r22_r21_bottleneckDevices_2", bottleneckDevices_2, true);
    
    Simulator::Stop(stopTime);
    Simulator::Run();
    Simulator::Destroy();
    COUT("Simulation finished.");
    return 0;
}