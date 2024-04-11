from mininet.cli import CLI
from mininet.net import Mininet
from mininet.node import RemoteController
from mininet.log import info, setLogLevel
from mininet.link import TCLink, Link
from mininet.util import quietRun

setLogLevel("debug")


if '__main__' == __name__:
    net = Mininet(controller=RemoteController)

    c0 = net.addController('c0', port=6653)

    s1 = net.addSwitch('s1')
    s2 = net.addSwitch('s2')
    s3 = net.addSwitch('s3')
    s4 = net.addSwitch('s4')
    s5 = net.addSwitch('s5')
    s6 = net.addSwitch('s6')

    h1 = net.addHost('h1')
    h2 = net.addHost('h2')
    h3 = net.addHost('h3')
    h4 = net.addHost('h4')
    h5 = net.addHost('h5')
    h6 = net.addHost('h6')

    # per convenzione inserisco prima il collegamento al singolo host in modo da averlo
    # sempre primo ed escluderlo dalla creazione delle tap interface
    net.addLink(s1, h1)
    net.addLink(s2, h2)
    net.addLink(s3, h3)
    net.addLink(s4, h4)
    net.addLink(s5, h5)
    net.addLink(s6, h6)

    net.addLink(s1, s2)
    net.addLink(s2, s3)
    net.addLink(s3, s4)
    net.addLink(s4, s5)
    net.addLink(s5, s6)
    net.addLink(s6, s1)

    net.build()
    c0.start()
    s1.start([c0])
    s2.start([c0])
    s3.start([c0])
    s4.start([c0])
    s5.start([c0])
    s6.start([c0])

    # attivazione tap per dare l'accessa a omnetcpp
    for h in net.switches:
        for i in h.ports:
            if i.name != 'lo':
                if i.name[-1] != "1":
                    if i.name[-1] == "2":
                        h.cmdPrint("sudo ip tuntap add mode tap dev tap" + i.name)

                        h.cmdPrint("sudo ovs-vsctl add-port " + h.name + " tap" + i.name)

                        h.cmdPrint("sudo ip link set tap" + i.name + " up")

                    h.cmdPrint("sudo ovs-vsctl del-port " + h.name + " " + i.name)

    CLI(net)

    for h in net.switches:
        for i in h.ports:
            if i.name != 'lo':
                if i.name[-1] != "1":
                    h.cmdPrint("sudo ip link del tap" + i.name)

    net.stop()
