# ResiliNet-Harness: Network Conformance & Chaos Engineering Framework

**ResiliNet-Harness** is a Linux-native network validation system designed to automate protocol conformance testing and regression analysis. 

Unlike passive packet sniffers, this framework actively orchestrates isolated network topologies using **Linux Network Namespaces**, injects deterministic faults (latency, jitter, loss) using **Traffic Control (tc)**, and performs stateful assertions on packet flows. It serves as a lightweight, code-first alternative to heavy virtualization tools, optimized for CI/CD pipelines.

---

## Key Features

### 1. Dynamic Topology Orchestration (`topology.py`)
- **Infrastructure-as-Code:** Programmatically spins up isolated network nodes (namespaces) and connects them via virtual ethernet (`veth`) pairs using `pyroute2` and direct Linux syscalls.
- **Isolation:** Ensures test environments are hermetic, preventing pollution from host network traffic.

### 2. Network Impairment & Chaos (`impairment.py`)
- **Reliability Testing:** Interfaces with the Linux kernel's `netem` (Network Emulator) qdisc to simulate hostile network conditions.
- **Profiles:**
  - `latency`: Inject fixed delays (e.g., 100ms) with variance (jitter) to test TCP RTT estimation.
  - `loss`: Probabilistic packet dropping (e.g., 5%) to verify retransmission logic.
  - `reordering`: Randomizes packet arrival to test protocol reassembly capabilities.

### 3. Stateful Protocol Validation (`validation.py`)
- **Assertion Engine:** Uses **Scapy** to not just capture packets, but validate protocol state machines.
- **Conformance Checks:**
  - **TCP Handshake:** Verifies 3-way handshake timing and sequence number incrementation (SYN -> SYN-ACK -> ACK).
  - **MTU & Fragmentation:** Validates that packets exceeding the Link MTU are correctly fragmented and reassembled.

### 4. Automated Regression Runner (`runner.py`)
- **CI/CD Integration:** Orchestrates the full lifecycle: `Setup -> Impair -> Execute -> Validate -> Teardown`.
- **Reporting:** Generates console pass/fail reports and structured logs for automated pipelines.

---

## Architecture

The system follows a layered architecture to separate infrastructure management from test logic:

```text
resilinet-harness/
├── resilinet/
│   ├── __init__.py
│   ├── topology.py       # Namespace & Veth management (pyroute2)
│   ├── impairment.py     # TC/Netem wrapper for fault injection
│   ├── validation.py     # Scapy-based protocol assertions
│   └── runner.py         # CLI Entrypoint & Test Orchestrator
├── tests/                # Unit tests for the harness itself
├── requirements.txt      # Dependencies
└── README.md