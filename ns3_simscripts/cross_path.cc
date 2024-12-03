#include "ns3/core-module.h"
#include "ns3/network-module.h"
#include "ns3/internet-module.h"
#include "ns3/point-to-point-module.h"
#include "ns3/applications-module.h"
#include "ns3/ipv4-global-routing-helper.h"
#include "ns3/icmpv4-l4-protocol.h"

#define COUT(log) std::cout << log << std::endl;

using namespace ns3;

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
void RerouteTraffic(uint32_t numClients, 
                    Ptr<Node> router1_1, Ptr<Node> router2_1, 
                    Ptr<Node> router1_2, Ptr<Node> router2_2,
                    const Ipv4InterfaceContainer& bottleneckInterfaces_1,
                    const Ipv4InterfaceContainer& crossInterfaces1,
                    const Ipv4InterfaceContainer& crossInterfaces2) 
{
    Ipv4StaticRoutingHelper routingHelper;

    // Remove specific routes from Router 1_2 and Router 2_2
    Ptr<Ipv4StaticRouting> router1_2Routing = routingHelper.GetStaticRouting(router1_2->GetObject<Ipv4>());
    router1_2Routing->RemoveRoute(5);
    router1_2Routing->RemoveRoute(6);
    COUT(crossInterfaces2.Get(0).second);
    router1_2Routing->AddNetworkRouteTo(Ipv4Address("10.4.0.0"), Ipv4Mask("255.255.255.0"), crossInterfaces1.GetAddress(1), crossInterfaces1.Get(1).second);
    router1_2Routing->AddNetworkRouteTo(Ipv4Address("10.4.1.0"), Ipv4Mask("255.255.255.0"), crossInterfaces1.GetAddress(1), crossInterfaces1.Get(1).second);

    Ptr<Ipv4StaticRouting> router2_2Routing = routingHelper.GetStaticRouting(router2_2->GetObject<Ipv4>());
    router2_2Routing->RemoveRoute(5);
    router2_2Routing->RemoveRoute(6);
    router2_2Routing->AddNetworkRouteTo(Ipv4Address("10.2.0.0"), Ipv4Mask("255.255.255.0"), crossInterfaces2.GetAddress(1), crossInterfaces1.Get(1).second);
    router2_2Routing->AddNetworkRouteTo(Ipv4Address("10.2.1.0"), Ipv4Mask("255.255.255.0"), crossInterfaces2.GetAddress(1), crossInterfaces1.Get(1).second);

    // // Update Router 1_1 to forward Dumbbell 2 traffic through its bottleneck link
    // Ptr<Ipv4StaticRouting> router1_1Routing = routingHelper.GetStaticRouting(router1_1->GetObject<Ipv4>());
    // router1_1Routing->AddNetworkRouteTo(Ipv4Address("10.4.0.0"), Ipv4Mask("255.255.255.0"),
    //                                     bottleneckInterfaces_1.GetAddress(1), 1);

    // // Update Router 2_1 to forward return traffic for Dumbbell 2 through its bottleneck link
    // Ptr<Ipv4StaticRouting> router2_1Routing = routingHelper.GetStaticRouting(router2_1->GetObject<Ipv4>());
    // router2_1Routing->AddNetworkRouteTo(Ipv4Address("10.2.0.0"), Ipv4Mask("255.255.255.0"),
    //                                     bottleneckInterfaces_1.GetAddress(0), 1);

    // // Ensure that cross-routing through Dumbbell 1 works both ways
    // Ptr<Ipv4StaticRouting> router1_2CrossRouting = routingHelper.GetStaticRouting(router1_2->GetObject<Ipv4>());
    // router1_2CrossRouting->AddNetworkRouteTo(Ipv4Address("10.3.0.0"), Ipv4Mask("255.255.255.0"),
    //                                          crossInterfaces1.GetAddress(1), 1);

    // Ptr<Ipv4StaticRouting> router2_2CrossRouting = routingHelper.GetStaticRouting(router2_2->GetObject<Ipv4>());
    // router2_2CrossRouting->AddNetworkRouteTo(Ipv4Address("10.3.1.0"), Ipv4Mask("255.255.255.0"),
    //                                          crossInterfaces2.GetAddress(1), 1);

    COUT("Traffic successfully rerouted through Dumbbell 1 bottleneck.");
}


int main(int argc, char *argv[]) {
    Config::SetDefault("ns3::TcpL4Protocol::SocketType", TypeIdValue(TypeId::LookupByName("ns3::TcpBbr")));
    double duration = 40.0;
    uint32_t numClients = 2;
    std::string bottleneckBw = "10Mbps";
    std::string bottleneckDelay = "10ms";

    CommandLine cmd;
    cmd.AddValue("numClients", "Number of client-server pairs", numClients);
    cmd.Parse(argc, argv);

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

    PointToPointHelper clientLink, bottleneckLink, serverLink, infLink;
    clientLink.SetDeviceAttribute("DataRate", StringValue("100Gbps"));
    clientLink.SetChannelAttribute("Delay", StringValue("0ms"));

    bottleneckLink.SetDeviceAttribute("DataRate", StringValue(bottleneckBw));
    bottleneckLink.SetChannelAttribute("Delay", StringValue(bottleneckDelay));

    serverLink.SetDeviceAttribute("DataRate", StringValue("100Gbps"));
    serverLink.SetChannelAttribute("Delay", StringValue("0ms"));

    infLink.SetDeviceAttribute("DataRate", StringValue("10Mbps"));
    infLink.SetChannelAttribute("Delay", StringValue("10ms"));

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
        COUT("Client_1_" << i + 1 << " IP: " << iface_1.GetAddress(0));


        NetDeviceContainer link_2 = clientLink.Install(clients_2.Get(i), router1_2);
        Ipv4InterfaceContainer iface_2 = ipv4_2.Assign(link_2);
        clientInterfaces_2.push_back(iface_2);
        ipv4_2.NewNetwork();
        COUT("Client_2_" << i + 1 << " IP: " << iface_2.GetAddress(0));
    }

    NetDeviceContainer bottleneckDevices_1 = bottleneckLink.Install(router1_1, router2_1);
    NetDeviceContainer bottleneckDevices_2 = infLink.Install(router1_2, router2_2);

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
        COUT("Server_1_" << i + 1 << " IP: " << iface_1.GetAddress(1));

        NetDeviceContainer link_2 = serverLink.Install(router2_2, servers_2.Get(i));
        Ipv4InterfaceContainer iface_2 = ipv4_2.Assign(link_2);
        serverInterfaces_2.push_back(iface_2);
        ipv4_2.NewNetwork();
        COUT("Server_2_" << i + 1 << " IP: " << iface_2.GetAddress(1));
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
        // Client 1 (Node 0): Route to Server 1 via Router 1
        Ptr<Ipv4StaticRouting> clientRouting_1 = routingHelper.GetStaticRouting(clients_1.Get(i)->GetObject<Ipv4>());
        clientRouting_1->AddNetworkRouteTo(serverInterfaces_1[i].GetAddress(1), Ipv4Mask("255.255.255.0"),
                                            //via
                                            bottleneckInterfaces_1.GetAddress(0), 1);

        // Router 1 (Node 2): Forward traffic to Router 2 via bottleneck link
        Ptr<Ipv4StaticRouting> router1Routing_1 = routingHelper.GetStaticRouting(router1_1->GetObject<Ipv4>());
        router1Routing_1->AddNetworkRouteTo(serverInterfaces_1[i].GetAddress(1), Ipv4Mask("255.255.255.0"),
                                            //via
                                            bottleneckInterfaces_1.GetAddress(1), numClients+1);
        router1Routing_1->AddNetworkRouteTo(serverInterfaces_2[i].GetAddress(1), Ipv4Mask("255.255.255.0"),
                                            //via
                                            bottleneckInterfaces_1.GetAddress(1), numClients+1);
        router1Routing_1->AddNetworkRouteTo(clientInterfaces_2[i].GetAddress(0), Ipv4Mask("255.255.255.0"),
                                            //via
                                            crossInterfaces1.GetAddress(0), crossInterfaces1.Get(0).second);

        // Router 2 (Node 3): Forward traffic to Server 1
        Ptr<Ipv4StaticRouting> router2Routing_1 = routingHelper.GetStaticRouting(router2_1->GetObject<Ipv4>());
        router2Routing_1->AddNetworkRouteTo(clientInterfaces_1[i].GetAddress(0), Ipv4Mask("255.255.255.0"),
                                            //via
                                            bottleneckInterfaces_1.GetAddress(0), 1);
        router2Routing_1->AddNetworkRouteTo(clientInterfaces_2[i].GetAddress(0), Ipv4Mask("255.255.255.0"),
                                            //via
                                            bottleneckInterfaces_1.GetAddress(0), 1);
        router2Routing_1->AddNetworkRouteTo(serverInterfaces_2[i].GetAddress(0), Ipv4Mask("255.255.255.0"),
                                            //via
                                            crossInterfaces2.GetAddress(0), crossInterfaces2.Get(0).second);

        // Server 1 (Node 1): Return traffic to Client 1 via Router 2
        Ptr<Ipv4StaticRouting> serverRouting_1 = routingHelper.GetStaticRouting(servers_1.Get(i)->GetObject<Ipv4>());
        serverRouting_1->AddNetworkRouteTo(clientInterfaces_1[i].GetAddress(0), Ipv4Mask("255.255.255.0"),
                                            //via
                                            bottleneckInterfaces_1.GetAddress(1), 1);
    }

    for (uint32_t i = 0; i < numClients; ++i) {
        // Client 2 (Node 4): Route to Server 2 via Router 1
        Ptr<Ipv4StaticRouting> clientRouting_2 = routingHelper.GetStaticRouting(clients_2.Get(i)->GetObject<Ipv4>());
        clientRouting_2->AddNetworkRouteTo(serverInterfaces_2[i].GetAddress(1), Ipv4Mask("255.255.255.0"),
                                            //via
                                            bottleneckInterfaces_1.GetAddress(0), 1);

        // Router 1 (Node 6): Forward traffic to Router 2 via bottleneck link
        Ptr<Ipv4StaticRouting> router1Routing_2 = routingHelper.GetStaticRouting(router1_2->GetObject<Ipv4>());
        router1Routing_2->AddNetworkRouteTo(serverInterfaces_2[i].GetAddress(1), Ipv4Mask("255.255.255.0"),
                                            // via
                                            bottleneckInterfaces_2.GetAddress(1), numClients+1);


        // Router 2 (Node 7): Forward traffic to Server 2
        Ptr<Ipv4StaticRouting> router2Routing_2 = routingHelper.GetStaticRouting(router2_2->GetObject<Ipv4>());
        router2Routing_2->AddNetworkRouteTo(clientInterfaces_2[i].GetAddress(0), Ipv4Mask("255.255.255.0"),
                                            //via
                                            bottleneckInterfaces_2.GetAddress(0), 1);

        // Server 2 (Node 5): Return traffic to Client 2 via Router 2
        Ptr<Ipv4StaticRouting> serverRouting_2 = routingHelper.GetStaticRouting(servers_2.Get(i)->GetObject<Ipv4>());
        serverRouting_2->AddNetworkRouteTo(clientInterfaces_2[i].GetAddress(0), Ipv4Mask("255.255.255.0"),
                                            //via
                                            bottleneckInterfaces_1.GetAddress(1), 1);
    }
    AsciiTraceHelper ascii;
    Ipv4GlobalRoutingHelper::PrintRoutingTableAllAt(Seconds(1), ascii.CreateFileStream("scratch/cross_path/routes_before.txt"));
    Ipv4GlobalRoutingHelper::PrintRoutingTableAllAt(Seconds(30), ascii.CreateFileStream("scratch/cross_path/routes_after.txt"));
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

Simulator::Schedule(Seconds(30), &RerouteTraffic, numClients, 
                    router1_1, router2_1, router1_2, router2_2,
                    bottleneckInterfaces_1, crossInterfaces1, crossInterfaces2);
    bottleneckLink.EnablePcap("scratch/cross_path/r12_r11_bottleneckDevices_1", bottleneckDevices_1, true);
    bottleneckLink.EnablePcap("scratch/cross_path/r22_r21_bottleneckDevices_2", bottleneckDevices_2, true);

    Simulator::Stop(Seconds(duration));
    Simulator::Run();
    Simulator::Destroy();
    COUT("Simulation finished.");
    return 0;
}
