import logging
import time
from pyroute2 import IPRoute, NDB, NetNS
from pyroute2.netlink.exceptions import NetlinkError

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class NamespaceManager:
    """
    Manages Linux network namespaces and virtual links for network testing.
    """
    def __init__(self):
        self.created_namespaces = []
        self.created_interfaces = []
        self.ndb = NDB()

    def create_node(self, name):
        """
        Creates a new network namespace.
        
        Args:
            name (str): The name of the namespace to create.
        """
        try:
            NetNS(name)
            self.created_namespaces.append(name)
            logger.info(f"Created namespace: {name}")
        except OSError as e:
            if e.errno == 17: # File exists
                logger.warning(f"Namespace {name} already exists.")
                self.created_namespaces.append(name) # Track it to clean it up later if needed
            else:
                logger.error(f"Failed to create namespace {name}: {e}")
                raise

    def link_nodes(self, node_a, node_b, ip_a, ip_b, subnet_mask):
        """
        Links two interfaces in different namespaces via a veth pair.
        
        Args:
            node_a (str): Name of the first namespace.
            node_b (str): Name of the second namespace.
            ip_a (str): IP address for the interface in node_a (e.g., '10.0.0.1').
            ip_b (str): IP address for the interface in node_b (e.g., '10.0.0.2').
            subnet_mask (int): Subnet mask CIDR (e.g., 24).
        """
        if_a_name = f"veth-{node_a[-4:]}" # Shorten name to avoid length limits
        if_b_name = f"veth-{node_b[-4:]}"
        
        try:
            # Create veth pair in the default namespace initially
            with IPRoute() as ip:
                ip.link('add', ifname=if_a_name, kind='veth', peer=if_b_name)
                self.created_interfaces.append(if_a_name) # Track for cleanup if move fails

                # Move interfaces to their respective namespaces
                idx_a = ip.link_lookup(ifname=if_a_name)[0]
                idx_b = ip.link_lookup(ifname=if_b_name)[0]
                
                ip.link('set', index=idx_a, net_ns_fd=node_a)
                ip.link('set', index=idx_b, net_ns_fd=node_b)
                
            # Configure Interface A
            with NetNS(node_a) as ns:
                idx = ns.link_lookup(ifname=if_a_name)[0]
                ns.link('set', index=idx, state='up')
                ns.addr('add', index=idx, address=ip_a, mask=subnet_mask)
                # Bring up loopback as well
                lo_idx = ns.link_lookup(ifname='lo')[0]
                ns.link('set', index=lo_idx, state='up')

            # Configure Interface B
            with NetNS(node_b) as ns:
                idx = ns.link_lookup(ifname=if_b_name)[0]
                ns.link('set', index=idx, state='up')
                ns.addr('add', index=idx, address=ip_b, mask=subnet_mask)
                # Bring up loopback as well
                lo_idx = ns.link_lookup(ifname='lo')[0]
                ns.link('set', index=lo_idx, state='up')
                
            logger.info(f"Linked {node_a} ({ip_a}) <--> {node_b} ({ip_b})")

        except Exception as e:
            logger.error(f"Failed to link nodes {node_a} and {node_b}: {e}")
            raise

    def cleanup(self):
        """
        Removes all created namespaces and interfaces.
        """
        logger.info("Cleaning up network resources...")
        with IPRoute() as ip:
            for ifname in self.created_interfaces:
                try:
                    if ip.link_lookup(ifname=ifname):
                        ip.link('del', ifname=ifname)
                        logger.info(f"Removed interface: {ifname}")
                except Exception:
                    pass # Interface might have been moved or already deleted

        for ns_name in self.created_namespaces:
            try:
                # pyroute2 doesn't have a clean 'delete info' for NetNS, usually we just remove the file
                # But creating a NetNS object and closing it just wraps a file descriptor.
                # To delete, we effectively just need to unmount/remove the file in /var/run/netns
                # Or use the remove method if available in the version.
                # Specifically for pyroute2.NetNS, 'remove' is available as a static method on newer versions
                # or we can use the 'netns' module from pyroute2
                from pyroute2 import netns
                netns.remove(ns_name)
                logger.info(f"Removed namespace: {ns_name}")
            except Exception as e:
                logger.warning(f"Failed to remove namespace {ns_name}: {e}")
        
        self.created_namespaces = []
        self.created_interfaces = []
        self.ndb.close()
