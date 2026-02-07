import logging
import multiprocessing
import time
import os
from scapy.all import sniff, send, IP, TCP, ICMP, conf
from pyroute2 import NetNS

# Configure logging
logger = logging.getLogger(__name__)

def _target_wrapper(ns_name, queue, target, args, kwargs):
    """
    Wrapper to run a function inside a network namespace.
    """
    try:
        # Open namespace file
        ns_path = f"/var/run/netns/{ns_name}"
        if not os.path.exists(ns_path):
            queue.put((False, f"Namespace {ns_name} not found"))
            return

        # Switch namespace
        # We use open(ns_path) to get a fd, then setns. 
        # ctypes or pyroute2 can do this. pyroute2.netns.setns is convenient if available,
        # otherwise we manually do it. 
        # For simplicity and standard compliance with pyroute2:
        with open(ns_path) as f:
            from pyroute2 import netns
            netns.setns(f.fileno())
        
        # Execute target
        result = target(*args, **kwargs)
        queue.put((True, result))
    except Exception as e:
        queue.put((False, str(e)))

def run_in_ns(ns_name, target, *args, **kwargs):
    """
    Runs a function in a separate process within a network namespace.
    
    Args:
        ns_name (str): Name of the namespace.
        target (callable): Function to run.
        *args: Arguments for target.
        **kwargs: Keyword arguments for target.
        
    Returns:
        The return value of target.
        
    Raises:
        Exception: If the target function fails or namespace issues occur.
    """
    queue = multiprocessing.Queue()
    p = multiprocessing.Process(target=_target_wrapper, args=(ns_name, queue, target, args, kwargs))
    p.start()
    p.join()
    
    if queue.empty():
        raise Exception("Process died without returning result")
        
    success, result = queue.get()
    if not success:
        raise Exception(f"Error in namespace {ns_name}: {result}")
    return result

# --- Helper Functions for Scapy Actions ---

def _sniff_packets(interface, count=1, filter_expr=None, timeout=5):
    """Sniffs packets and returns them."""
    packets = sniff(iface=interface, count=count, filter=filter_expr, timeout=timeout)
    return packets

def _send_syn(dst_ip, dport):
    """Sends a TCP SYN packet."""
    pkt = IP(dst=dst_ip)/TCP(dport=dport, flags="S")
    send(pkt, verbose=False)
    return pkt

def _send_large_icmp(dst_ip, payload_size):
    """Sends a large ICMP packet."""
    payload = "A" * payload_size
    pkt = IP(dst=dst_ip)/ICMP()/payload
    send(pkt, verbose=False)
    return pkt

# --- Main Class ---

class ProtocolAssertion:
    """
    Validates network protocols and conformance.
    """
    
    @staticmethod
    def test_tcp_handshake(node_a, node_b, dst_ip, dport=80, interface="veth0"):
        """
        Verifies TCP SYN arrival from Node A to Node B.
        
        Args:
            node_a (str): Source namespace.
            node_b (str): Destination namespace.
            dst_ip (str): Destination IP (IP of Node B).
        """
        logger.info(f"Testing TCP Handshake: {node_a} -> {node_b} ({dst_ip}:{dport})")
        
        # Start Sniffer on Node B (Expect SYN)
        # We run this in a non-blocking process or just use a short timeout with synchronization.
        # Ideally: Start sniffer -> Wait for it to be ready -> Send packet.
        # For simplicity in this harness: Start sniffer with timeout, wait a bit, send packet.
        
        def start_sniffer_b():
            return _sniff_packets(interface, count=1, filter_expr=f"tcp and dst host {dst_ip} and tcp[tcpflags] & tcp-syn != 0")

        queue_b = multiprocessing.Queue()
        p_b = multiprocessing.Process(target=_target_wrapper, args=(node_b, queue_b, start_sniffer_b, (), {}))
        p_b.start()
        
        # Give sniffer time to start
        time.sleep(1)
        
        # Send SYN from Node A
        try:
            run_in_ns(node_a, _send_syn, dst_ip, dport)
        except Exception as e:
            p_b.terminate()
            raise e

        p_b.join()
        
        if queue_b.empty():
             raise AssertionError("Sniffer on Node B failed to capture packet or timeout.")
             
        success, packets = queue_b.get()
        if not success:
             raise AssertionError(f"Sniffer error on Node B: {packets}")
             
        if not packets:
            raise AssertionError("TCP SYN packet not received at Node B")
            
        logger.info("TCP Handshake (SYN delivery) Verified.")
        return True

    @staticmethod
    def test_mtu_fragmentation(node_a, node_b, dst_ip, mtu=1500, payload_size=2000, interface="veth0"):
        """
        Verifies that packets larger than MTU are fragmented.
        """
        logger.info(f"Testing MTU Fragmentation: {node_a} -> {node_b} (Size: {payload_size}, MTU: {mtu})")
        
        # Start Sniffer on Node B (Expect Fragments)
        # We expect at least 2 fragments for a 2000 byte packet on 1500 MTU
        def start_sniffer_b():
            return _sniff_packets(interface, count=2, filter_expr=f"icmp and dst host {dst_ip}", timeout=5)

        queue_b = multiprocessing.Queue()
        p_b = multiprocessing.Process(target=_target_wrapper, args=(node_b, queue_b, start_sniffer_b, (), {}))
        p_b.start()
        
        time.sleep(1)
        
        # Send Large ICMP from Node A
        run_in_ns(node_a, _send_large_icmp, dst_ip, payload_size)
        
        p_b.join()
        
        if queue_b.empty():
             raise AssertionError("Sniffer on Node B failed.")
             
        success, packets = queue_b.get()
        if not success:
             raise AssertionError(f"Sniffer error: {packets}")
             
        # Check for fragmentation
        # Scapy reassembles automaticall usually, but sniff returns packets.
        # We can check IP flags or just count.
        if len(packets) < 2:
            raise AssertionError(f"Expected fragmentation (>= 2 packets), got {len(packets)}")
            
        logger.info("MTU Fragmentation Verified.")
        return True
