import pytest
import os
from resilinet_harness.topology import NamespaceManager

# Skip if not running as root or on Linux, as namespaces require privileges
# This is a basic check; robust CI would handle this differently
skip_insufficient_privileges = pytest.mark.skipif(
    os.geteuid() != 0,
    reason="Need root privileges to create network namespaces"
)

@pytest.fixture
def ns_manager():
    manager = NamespaceManager()
    yield manager
    manager.cleanup()

@skip_insufficient_privileges
def test_create_node(ns_manager):
    node_name = "test_node_1"
    ns_manager.create_node(node_name)
    assert node_name in ns_manager.created_namespaces

@skip_insufficient_privileges
def test_link_nodes(ns_manager):
    node_a = "node_a"
    node_b = "node_b"
    
    ns_manager.create_node(node_a)
    ns_manager.create_node(node_b)
    
    ns_manager.link_nodes(node_a, node_b, "10.0.0.1", "10.0.0.2", 24)
    
    # In a real test, we would ping or check interfaces exists
    assert len(ns_manager.created_interfaces) > 0
