import inet.networklayer.configurator.ipv4.Ipv4NetworkConfigurator;
import inet.node.ethernet.Eth100M;
import inet.node.ethernet.EthernetSwitch;
import inet.node.inet.Router;
import inet.node.inet.StandardHost;
import inet.node.inet.AdhocHost;
import inet.networklayer.configurator.ipv4.Ipv4NetworkConfigurator;
import inet.physicallayer.wireless.ieee80211.packetlevel.Ieee80211ScalarRadioMedium;
import inet.visualizer.contract.IIntegratedVisualizer;
import inet.physicallayer.wireless.common.medium.RadioMedium;
import inet.visualizer.common.IntegratedVisualizer;


network stabelNet
{
    parameters:
        @display("bgb=1000,400");
    submodules:
        visualizer: <default(firstAvailableOrEmpty("IntegratedMultiCanvasVisualizer"))> like IIntegratedVisualizer if typename != "" {
             parameters:
                @display("p=100,200;is=s");
        }
        switch1: EthernetSwitch {
            parameters:
                @display("p=300,300");
        }
        switch2: EthernetSwitch {
            parameters:
                @display("p=700,300");
        }
        //switch3: EthernetSwitch {
         //   parameters:
         //       @display("p=496.97998,198.29");
       // }
    connections:
        switch1.ethg++ <--> Eth100M <--> switch2.ethg++;
        //switch1.ethg++ <--> Eth100M <--> switch3.ethg++;
        //switch3.ethg++ <--> Eth100M <--> switch2.ethg++;
}
