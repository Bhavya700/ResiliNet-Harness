import logging
from scapy.all import sniff, IP, TCP, UDP

# Configure logging
logging.basicConfig(filename='network_traffic.log', level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

class PacketSniffer:
    """
    Captures and logs network packets using Scapy.
    """
    def __init__(self, interface=None, max_packets=20):
        """
        Initialize the packet sniffer.
        
        Args:
            interface (str): Network interface to sniff on (e.g., 'eth0', 'veth0'). If None, sniffs all.
            max_packets (int): Maximum number of packets to log detailed info for.
        """
        self.interface = interface
        self.max_packets = max_packets
        self.packet_count = 0

    def packet_callback(self, packet):
        """
        Callback function to process each captured packet.
        """
        if self.packet_count < self.max_packets:
            logger.info(packet.summary())
            
            # Capture more details based on the packet type
            if packet.haslayer(IP):
                ip_layer = packet[IP]
                logger.info(f"Source IP: {ip_layer.src}, Destination IP: {ip_layer.dst}, Protocol: {ip_layer.proto}")

            if packet.haslayer(TCP):
                tcp_layer = packet[TCP]
                logger.info(f"Source Port: {tcp_layer.sport}, Destination Port: {tcp_layer.dport}")

            if packet.haslayer(UDP):
                udp_layer = packet[UDP]
                logger.info(f"Source Port: {udp_layer.sport}, Destination Port: {udp_layer.dport}")

            self.packet_count += 1
    
    def start(self, timeout=None, count=0):
        """
        Start sniffing.
        
        Args:
           timeout (int): Stop after this many seconds.
           count (int): Stop after this many packets.
        """
        print(f"Starting packet capture on {self.interface if self.interface else 'all interfaces'}. Press Ctrl+C to stop.")
        try:
            sniff(iface=self.interface, prn=self.packet_callback, store=0, timeout=timeout, count=count)
        except KeyboardInterrupt:
            print("Packet capture stopped.")
        except Exception as e:
            print(f"An error occurred: {e}")
