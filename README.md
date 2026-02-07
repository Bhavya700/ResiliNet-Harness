# ResiliNet Harness

A Network Conformance & Regression Harness for testing network protocols and resilience.

## Features

- **Topology Management**: Create and manage Linux network namespaces and virtual links (`resilinet_harness.topology`).
- **Packet Sniffing**: Modular packet sniffer using Scapy (`resilinet_harness.sniffer`).
- **Test Runner**: Integrated with `pytest` for automated regression testing.

## Installation

Requires Linux with root privileges for namespace management.

```bash
pip install -r requirements.txt
pip install -e .
```

## Structure

- `resilinet_harness/`: Main package.
  - `topology.py`: Manages `ip netns` and veth pairs.
  - `sniffer.py`: Packet capture logic.
- `tests/`: Pytest tests.

## Usage

### Running Tests

```bash
sudo pytest tests/
```

### Manual Topology

```python
from resilinet_harness.topology import NamespaceManager

nm = NamespaceManager()
nm.create_node('node1')
nm.create_node('node2')
nm.link_nodes('node1', 'node2', '10.0.0.1', '10.0.0.2', 24)
# ... run tests ...
nm.cleanup()
```