#include "ns3/core-module.h"
#include "ns3/network-module.h"
#include "ns3/internet-module.h"
#include "ns3/point-to-point-module.h"
#include "ns3/applications-module.h"
#include "ns3/flow-monitor-module.h"

using namespace ns3;

NS_LOG_COMPONENT_DEFINE ("SimulacaoSegurancaPublicaIoT");

int main (int argc, char *argv[])
{
    // Parâmetros configuráveis via linha de comando
    std::string dataRateGateway = "10Mbps";
    std::string delayGateway = "20ms";
    uint32_t packetSize = 1024;
    std::string appDataRate = "2Mbps";

    CommandLine cmd;
    cmd.AddValue ("delayGateway", "Atraso no link dos Gateways para o Servidor", delayGateway);
    cmd.AddValue ("dataRateGateway", "Largura de banda dos Gateways para o Servidor", dataRateGateway);
    cmd.Parse (argc, argv);

    Time::SetResolution (Time::NS);
    LogComponentEnable ("SimulacaoSegurancaPublicaIoT", LOG_LEVEL_INFO);

    NS_LOG_INFO ("Criando Topologia de Segurança Pública...");

    // 1. Criar Nós
    NodeContainer serverNode;
    serverNode.Create (1);

    NodeContainer gatewayNodes;
    gatewayNodes.Create (3);

    NodeContainer conjunto1_Sensors, conjunto2_Sensors, conjunto3_Sensors;
    conjunto1_Sensors.Create (3); // Câmeras
    conjunto2_Sensors.Create (3); // Sensores de Disparo
    conjunto3_Sensors.Create (3); // Bodycams

    // 2. Configurar Canais (Links)
    // Links Sensores -> Gateways
    PointToPointHelper p2pSensor;
    p2pSensor.SetDeviceAttribute ("DataRate", StringValue ("5Mbps"));
    p2pSensor.SetChannelAttribute ("Delay", StringValue ("5ms"));

    // Links Gateways -> Servidor Central
    PointToPointHelper p2pGateway;
    p2pGateway.SetDeviceAttribute ("DataRate", StringValue (dataRateGateway));
    p2pGateway.SetChannelAttribute ("Delay", StringValue (delayGateway));

    // Instanciar Dispositivos de Rede (NetDevices)
    NetDeviceContainer devG1_Serv = p2pGateway.Install (gatewayNodes.Get (0), serverNode.Get (0));
    NetDeviceContainer devG2_Serv = p2pGateway.Install (gatewayNodes.Get (1), serverNode.Get (0));
    NetDeviceContainer devG3_Serv = p2pGateway.Install (gatewayNodes.Get (2), serverNode.Get (0));

    // Instanciar dispositivos dos sensores para seus respectivos gateways
    NetDeviceContainer devC1[3], devC2[3], devC3[3];
    for(int i=0; i<3; i++) {
        devC1[i] = p2pSensor.Install (conjunto1_Sensors.Get (i), gatewayNodes.Get (0));
        devC2[i] = p2pSensor.Install (conjunto2_Sensors.Get (i), gatewayNodes.Get (1));
        devC3[i] = p2pSensor.Install (conjunto3_Sensors.Get (i), gatewayNodes.Get (2));
    }

    // 3. Instalar Pilha de Internet e Roteamento
    InternetStackHelper stack;
    stack.Install (serverNode);
    stack.Install (gatewayNodes);
    stack.Install (conjunto1_Sensors);
    stack.Install (conjunto2_Sensors);
    stack.Install (conjunto3_Sensors);

    Ipv4AddressHelper address;
    Ipv4InterfaceContainer interfacesG1_S, interfacesG2_S, interfacesG3_S;

    // Endereçamento dos Core Links
    address.SetBase ("10.1.1.0", "255.255.255.0");
    interfacesG1_S = address.Assign (devG1_Serv);
    address.SetBase ("10.1.2.0", "255.255.255.0");
    interfacesG2_S = address.Assign (devG2_Serv);
    address.SetBase ("10.1.3.0", "255.255.255.0");
    interfacesG3_S = address.Assign (devG3_Serv);

    // Endereçamento dos sub-elementos
    for(int i=0; i<3; i++) {
        std::ostringstream subnet;
        subnet << "10.2." << i+1 << ".0";
        address.SetBase (subnet.str ().c_str (), "255.255.255.0");
        address.Assign (devC1[i]);

        subnet.str(""); subnet << "10.3." << i+1 << ".0";
        address.SetBase (subnet.str ().c_str (), "255.255.255.0");
        address.Assign (devC2[i]);

        subnet.str(""); subnet << "10.4." << i+1 << ".0";
        address.SetBase (subnet.str ().c_str (), "255.255.255.0");
        address.Assign (devC3[i]);
    }

    Ipv4GlobalRoutingHelper::PopulateRoutingTables ();

    // 4. Aplicações (Tráfego IoT via UDP)
    uint16_t port = 9000;
    
    // Packet Sink no Servidor Central para receber tudo
    PacketSinkHelper packetSinkHelper ("ns3::UdpSocketFactory", Address (InetSocketAddress (Ipv4Address::GetAny (), port)));
    ApplicationContainer sinkApp = packetSinkHelper.Install (serverNode.Get (0));
    sinkApp.Start (Seconds (1.0));
    sinkApp.Stop (Seconds (10.0));

    // Geradores de Tráfego OnOff (Simulando o envio contínuo de dados dos sensores)
    OnOffHelper onoff ("ns3::UdpSocketFactory", Address (InetSocketAddress (interfacesG1_S.GetAddress (1), port))); // Destino: IP do servidor no link G1
    onoff.SetAttribute ("OnTime", StringValue ("ns3::ConstantRandomVariable[Constant=1]"));
    onoff.SetAttribute ("OffTime", StringValue ("ns3::ConstantRandomVariable[Constant=0]"));
    onoff.SetAttribute ("PacketSize", UintegerValue (packetSize));
    onoff.SetAttribute ("DataRate", StringValue (appDataRate));

    ApplicationContainer apps;
    // Instalar nos sensores do Conjunto 1
    apps.Add (onoff.Install (conjunto1_Sensors));
    
    // Mudar destino para a rota do Gateway 2 e instalar no Conjunto 2
    onoff.SetAttribute ("Remote", AddressValue (InetSocketAddress (interfacesG2_S.GetAddress (1), port)));
    apps.Add (onoff.Install (conjunto2_Sensors));

    // Mudar destino para a rota do Gateway 3 e instalar no Conjunto 3
    onoff.SetAttribute ("Remote", AddressValue (InetSocketAddress (interfacesG3_S.GetAddress (1), port)));
    apps.Add (onoff.Install (conjunto3_Sensors));

    apps.Start (Seconds (2.0));
    apps.Stop (Seconds (10.0));

    // 5. Monitor de Fluxo (FlowMonitor) - Extração das Métricas
    FlowMonitorHelper flowmon;
    Ptr<FlowMonitor> monitor = flowmon.InstallAll ();

    Simulator::Stop (Seconds (11.0));
    Simulator::Run ();

    // Processamento dos resultados das métricas
    monitor->CheckForLostPackets ();
    Ptr<Ipv4FlowClassifier> classifier = DynamicCast<Ipv4FlowClassifier> (flowmon.GetClassifier ());
    std::map<FlowId, FlowMonitor::FlowStats> stats = monitor->GetFlowStats ();

    double totalThroughput = 0;
    double totalDelay = 0;
    double totalJitter = 0;
    uint64_t totalTxPackets = 0;
    uint64_t totalRxPackets = 0;
    int rxFlowsCount = 0;

    std::cout << "\n================ METRICAS DA SIMULACAO ================\n";
    for (std::map<FlowId, FlowMonitor::FlowStats>::const_iterator i = stats.begin (); i != stats.end (); ++i)
    {
        Ipv4FlowClassifier::FiveTuple t = classifier->FindFlow (i->first);
        
        // Filtrar apenas fluxos que vão para o Servidor Central (Porta 9000)
        if (t.destinationPort == 9000)
        {
            totalTxPackets += i->second.txPackets;
            totalRxPackets += i->second.rxPackets;
            
            if (i->second.rxPackets > 0)
            {
                rxFlowsCount++;
                // Throughput em Mbps
                double throughput = (i->second.rxBytes * 8.0) / (i->second.timeLastRxPacket.GetSeconds() - i->second.timeFirstRxPacket.GetSeconds()) / 1024 / 1024;
                totalThroughput += throughput;
                
                // Latência / Delay Médio em milissegundos
                totalDelay += (i->second.delaySum.GetSeconds() / i->second.rxPackets) * 1000;
                
                // Jitter Médio em milissegundos
                totalJitter += (i->second.jitterSum.GetSeconds() / (i->second.rxPackets - 1)) * 1000;
            }
        }
    }

    // Exibição Consolidada dos Resultados
    if (rxFlowsCount > 0)
    {
        double packetLoss = ((double)(totalTxPackets - totalRxPackets) / totalTxPackets) * 100;
        
        std::cout << "Throughput Médio da Rede: " << totalThroughput << " Mbps\n";
        std::cout << "Latencia (Delay) Media  : " << (totalDelay / rxFlowsCount) << " ms\n";
        std::cout << "Jitter Medio            : " << (totalJitter / rxFlowsCount) << " ms\n";
        std::cout << "Packet Loss (Perda)     : " << packetLoss << " %\n";
        std::cout << "Pacotes Enviados        : " << totalTxPackets << "\n";
        std::cout << "Pacotes Recebidos       : " << totalRxPackets << "\n";
    }
    else
    {
        std::cout << "Nenhum pacote foi recebido pelo servidor central.\n";
    }
    std::cout << "=======================================================\n\n";

    Simulator::Destroy ();
    return 0;
}