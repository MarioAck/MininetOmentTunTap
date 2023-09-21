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

    h1 = net.addHost('h1')
    h2 = net.addHost('h2')
    #h3 = net.addHost('h3')

    # per convenzione inserisco prima il collegamento al singolo host in modo da averlo
    # sempre primo ed escluderlo dalla creazione delle tap interface
    net.addLink(s1, h1)
    net.addLink(s2, h2)
    #net.addLink(s3, h3)

    net.addLink(s1, s2)
    #net.addLink(s2, s3)
    #net.addLink(s3, s1)

    net.build()
    c0.start()
    s1.start([c0])
    s2.start([c0])
    #s3.start([c0])

    # attivazione tap per dare l'accessa a omnetcpp
    for h in net.switches:
        for i in h.ports:
            if i.name != 'lo':
                if i.name != h.name + "-eth1":

                    h.cmdPrint("sudo ip tuntap add mode tap dev tap" + i.name)
                    h.waitOutput()

                    h.cmdPrint("sudo ovs-vsctl add-port " + h.name + " tap" + i.name)

                    h.cmdPrint("sudo ip link set tap" + i.name + " up")
                    h.waitOutput()

                    h.cmdPrint("sudo ovs-vsctl del-port " + h.name + " " + i.name)

    CLI(net)

    for h in net.switches:
        for i in h.ports:
            if i.name != 'lo':
                if i.name[-1] != "1":
                    h.cmdPrint("sudo ip link del tap" + i.name)
                    h.waitOutput()

    net.stop()
