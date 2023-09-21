import inet.node.inet.AdhocHost;
import inet.networklayer.configurator.ipv4.Ipv4NetworkConfigurator;
import inet.physicallayer.wireless.ieee80211.packetlevel.Ieee80211ScalarRadioMedium;
import inet.visualizer.contract.IIntegratedVisualizer;
import inet.physicallayer.wireless.common.medium.RadioMedium;

network BabelShowcase
{
    parameters:
        @display("bgb=600,400");
		@figure[title](type=label; pos=0,-1; anchor=sw; color=darkblue);

        @figure[rcvdPkText](type=indicatorText; pos=380,20; anchor=w; font=,18; textFormat="packets received: %g"; initialValue=0);
        @statistic[packetReceived](source=host0.wlan[0].packetDropInterfaceDown; record=figure(count); targetFigure=rcvdPkText);
    submodules:
        visualizer: <default(firstAvailableOrEmpty("IntegratedMultiCanvasVisualizer"))> like IIntegratedVisualizer if typename != "" {
            parameters:
                @display("p=176,350;is=s");
        }
        radioMedium: Ieee80211ScalarRadioMedium {
            parameters:
                @display("p=62,352;is=s");
        }
        host0: AdhocHost {
            parameters:
                @display("r=,,#707070;p=349,200");
        }
        host1: AdhocHost {
            parameters:
                @display("r=,,#707070;p=248,200");
        }
}
