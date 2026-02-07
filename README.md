# ResiliNet Harness

A professional Network Conformance & Regression Harness for testing network protocols and resilience under impairment conditions.

## Features

- **Topology Management**: Create and manage Linux network namespaces and virtual links (`resilinet_harness.topology`).
- **Network Impairment**: Inject latency, jitter, packet loss, and reordering using Linux Traffic Control (`resilinet_harness.impairment`).
- ** conformance Validation**: Verify TCP handshakes, MTU fragmentation, and other protocols (`resilinet_harness.validation`).
- **Automated Runner**: CLI tool to orchestrate full test lifecycles with automatic setup and cleanup (`resilinet_harness.runner`).

## Installation

This harness requires **Linux** with root privileges (due to `ip netns` and `tc` usage).

1. Clone the repository:
   ```bash
   git clone https://github.com/Bhavya700/ResiliNet-Harness.git
   cd ResiliNet-Harness
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

### CLI Runner

The easiest way to run tests is using the built-in CLI runner. It sets up a client-server topology, applies impairments, and verifies connectivity.

```bash
# Run with default settings (High Latency Profile)
sudo python3 -m resilinet_harness.runner --profile latency

# Run with Packet Loss Profile (5% loss)
sudo python3 -m resilinet_harness.runner --profile loss

# Run with Packet Reordering Profile
sudo python3 -m resilinet_harness.runner --profile reorder

# Run without impairments (Baseline)
sudo python3 -m resilinet_harness.runner --profile none
```

### Module Structure

- **`resilinet_harness/topology.py`**:
  - `NamespaceManager`: Handles creation/deletion of `ip netns` namespaces and veth pairs.
  
- **`resilinet_harness/impairment.py`**:
  - `NetworkConditioner`: Interfaces with `tc` (NetEm) to inject faults like delay and loss.

- **`resilinet_harness/validation.py`**:
  - `ProtocolAssertion`: Contains static methods to run validation tests (e.g., `test_tcp_handshake`, `test_mtu_fragmentation`) using Scapy and `multiprocessing`.

- **`resilinet_harness/runner.py`**:
  - Orchestrates the setup -> impairment -> validation -> cleanup workflow.

### Manual Python Usage

You can build custom test scripts using the modules directly:

```python
from resilinet_harness.topology import NamespaceManager
from resilinet_harness.impairment import NetworkConditioner
from resilinet_harness.validation import ProtocolAssertion

# 1. Setup Topology
nm = NamespaceManager()
nm.create_node("h1")
nm.create_node("h2")
nm.link_nodes("h1", "h2", "10.0.0.1", "10.0.0.2", 24)

# 2. Apply Impairments
nc = NetworkConditioner(namespace="h1")
nc.apply_profile("veth-h1", {"latency": "50ms", "loss": 1})

# 3. Validation
try:
    ProtocolAssertion.test_tcp_handshake("h1", "h2", "10.0.0.2")
    print("Test Passed!")
except AssertionError as e:
    print(f"Test Failed: {e}")

# 4. Cleanup
nm.cleanup()
```

## Requirements

- Python 3.8+
- Linux Kernel (support for namespaces and netem)
- `iproute2` installed on the system