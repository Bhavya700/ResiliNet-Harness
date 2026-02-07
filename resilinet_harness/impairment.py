import logging
from pyroute2 import IPRoute, NetNS

# Configure logging
logger = logging.getLogger(__name__)

class NetworkConditioner:
    """
    Applies network impairments using Linux Traffic Control (tc) and netem.
    """
    def __init__(self, namespace=None):
        """
        Initialize the conditioner.
        
        Args:
            namespace (str): Optional network namespace to operate in. 
                             If None, operates in the default namespace.
        """
        self.namespace = namespace

    def _get_ip_route(self):
        """Returns an IPRoute or NetNS object based on configuration."""
        if self.namespace:
            return NetNS(self.namespace)
        return IPRoute()

    def apply_profile(self, interface, profile):
        """
        Applies a traffic shaping profile to an interface.
        
        Args:
            interface (str): Name of the interface to impair.
            profile (dict): Dictionary of impairments. Supported keys:
                            - latency: str (e.g., '100ms') or dict {'delay': '100ms', 'jitter': '10ms'}
                            - loss: float (percentage)
                            - reorder: float (percentage)
        """
        netem_options = {}
        
        # Parse Latency/Jitter
        latency = profile.get('latency')
        if latency:
            if isinstance(latency, dict):
                netem_options['delay'] = latency.get('delay', '0ms')
                netem_options['jitter'] = latency.get('jitter', '0ms')
            else:
                netem_options['delay'] = str(latency)

        # Parse Loss
        loss = profile.get('loss')
        if loss is not None:
            netem_options['loss'] = float(loss)

        # Parse Reorder
        reorder = profile.get('reorder')
        if reorder is not None:
            netem_options['reorder'] = float(reorder)
            # Reordering usually requires some delay to be effective in netem
            if 'delay' not in netem_options:
                netem_options['delay'] = '10ms'
                logger.warning(f"Adding 10ms delay to interface {interface} to enable packet reordering.")

        if not netem_options:
            logger.info(f"No valid impairments found in profile for {interface}. Skipping.")
            return

        try:
            with self._get_ip_route() as ip:
                # Get interface index
                idx_list = ip.link_lookup(ifname=interface)
                if not idx_list:
                    raise ValueError(f"Interface {interface} not found.")
                idx = idx_list[0]

                # Remove existing qdiscs (root) to ensure clean state
                try:
                    ip.tc('del', 'root', idx)
                except Exception:
                    pass # Ignore if no qdisc exists

                # Add netem qdisc
                # handle 1: is standard for root
                ip.tc('add', 'netem', handle='1:', parent='root', dev=idx, **netem_options)
                
                logger.info(f"Applied profile {profile} to {interface} in ns={self.namespace}")

        except Exception as e:
            logger.error(f"Failed to apply profile to {interface}: {e}")
            raise

    def clear_impairments(self, interface):
        """
        Removes all impairments from an interface.
        """
        try:
            with self._get_ip_route() as ip:
                idx_list = ip.link_lookup(ifname=interface)
                if not idx_list:
                    return
                idx = idx_list[0]
                ip.tc('del', 'root', idx)
                logger.info(f"Cleared impairments from {interface} in ns={self.namespace}")
        except Exception as e:
             # It's fine if it fails because it didn't exist
             logger.debug(f"Could not clear impairments (might not exist): {e}")

