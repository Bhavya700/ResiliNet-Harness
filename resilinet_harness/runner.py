import argparse
import sys
import time
import logging
from contextlib import contextmanager
from resilinet_harness.topology import NamespaceManager
from resilinet_harness.impairment import NetworkConditioner
from resilinet_harness.validation import ProtocolAssertion

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger("Runner")

# ANSI Color Codes
GREEN = "\033[92m"
RED = "\033[91m"
RESET = "\033[0m"

@contextmanager
def setup_topology():
    """
    Context manager to setup and automatically cleanup the network topology.
    """
    nm = NamespaceManager()
    try:
        logger.info("Setting up topology (Client <-> Server)...")
        nm.create_node("client")
        nm.create_node("server")
        
        # Link them: Client 10.0.0.1 <--> Server 10.0.0.2
        nm.link_nodes("client", "server", "10.0.0.1", "10.0.0.2", 24)
        
        yield nm
    finally:
        logger.info("Cleaning up topology...")
        nm.cleanup()

def run_test(impairment_profile):
    """
    Orchestrates the test execution.
    """
    with setup_topology() as nm:
        # 1. Apply Impairment to Client's interface (veth-clie -> veth0 inside client)
        # Note: In our topology.py, interfaces inside NS are named veth-XXXX usually or moved.
        # Let's check topology.py logic:
        # if_a_name = f"veth-{node_a[-4:]}" -> moved to node_a
        # link_nodes("client", "server"...)
        # client interface: veth-ient
        # server interface: veth-rver
        
        client_iface = "veth-ient"
        server_iface = "veth-rver"
        
        if impairment_profile:
            logger.info(f"Applying Impairment Profile: {impairment_profile}")
            nc = NetworkConditioner(namespace="client")
            nc.apply_profile(client_iface, impairment_profile)
        
        # Give time for things to settle
        time.sleep(1)
        
        # 2. Run Verification
        logger.info("Running TCP Handshake Verification...")
        try:
            # Test: Client (10.0.0.1) -> Server (10.0.0.2)
            # Server IP match what we set in setup_topology
            ProtocolAssertion.test_tcp_handshake("client", "server", "10.0.0.2", interface=server_iface)
            print(f"{GREEN}[PASS] TCP Handshake Verification Successful!{RESET}")
        except AssertionError as e:
            print(f"{RED}[FAIL] TCP Handshake Failed: {e}{RESET}")
        except Exception as e:
            print(f"{RED}[ERROR] Test Crashing: {e}{RESET}")

def main():
    parser = argparse.ArgumentParser(description="ResiliNet Harness - Network Reliability Runner")
    parser.add_argument("--profile", choices=['latency', 'loss', 'reorder', 'none'], default='latency', 
                        help="Impairment profile to apply")
    
    args = parser.parse_args()
    
    profile = {}
    if args.profile == 'latency':
        profile = {'latency': '100ms', 'jitter': '20ms'}
    elif args.profile == 'loss':
        profile = {'loss': 5}
    elif args.profile == 'reorder':
        profile = {'reorder': 10, 'latency': '10ms'} # Delay needed for reorder
    elif args.profile == 'none':
        profile = {}

    run_test(profile)

if __name__ == "__main__":
    main()
