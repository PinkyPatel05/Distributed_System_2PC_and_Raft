# Assignment 3: Raft Consensus Algorithm Implementation on task schedular

**Course:** CSE 5306 - Distributed Systems  
**Project:** Task Schedular Distributed System
**Implementation:** Raft for Distributed Transactions

Group: 17
Purva Dankhara(1002260167)
Pinky Patel (1002251887)

## 📋 Overview

This project implements the Raft Consensus Algorithm for **Assignment 3** of the **Distributed Systems** course as part of the **Distributed-Task-Scheduler** project.

The implementation covers:

- **Q3: Leader Election** with proper timeouts and fault tolerance
- **Q4: Log Replication** with client request handling and forwarding
- **Q5: Five comprehensive test cases** with documentation and screenshots

---

## 🎯 What is Raft?

Raft is a consensus algorithm that allows a cluster of nodes to agree on a shared state, even when some nodes fail. It is widely used in distributed systems to ensure:

- **Strong consistency:** All nodes see the same data
- **Fault tolerance:** System continues working even if nodes fail
- **Leader-based replication:** One leader manages and coordinates all updates

### Key Components

- **Leader Election:** Nodes elect a leader to coordinate the cluster
- **Log Replication:** Leader replicates operations to all followers
- **Safety:** Ensures no conflicting decisions are made and logs remain consistent

---

## 📁 Project Structure

```text
Distributed-Task-Scheduler/
│
├── raft/                      # Raft Implementation (Q3 & Q4)
│   ├── proto/
│   │   └── raft.proto         # gRPC service definitions
│   │
│   ├── raft_node.py           # Main Raft node server
│   ├── election.py            # Leader election logic (Q3)
│   ├── log_replication.py     # Log replication logic (Q4)
│   ├── client.py              # Test client for submitting operations
│   │
│   ├── Dockerfile             # Container configuration
│   ├── raft_pb2.py            # Generated gRPC code
│   └── raft_pb2_grpc.py       # Generated gRPC code
│
├── tests/                     # Test Cases (Q5)
│   ├── test1_normal_election.sh      # Test Case 1: Normal Election
│   ├── test2_leader_failure.sh       # Test Case 2: Leader Failure
│   ├── test3_log_replication.sh      # Test Case 3: Log Replication
│   ├── test4_request_forwarding.sh   # Test Case 4: Request Forwarding
│   ├── test5_network_partition.sh    # Test Case 5: Network Partition
│   └── run_all_tests.sh              # Run all tests
│
├── docker-compose.raft.yml    # Docker orchestration for 5 nodes
│
└── README.md                  # This file
```

---

## 🔧 Prerequisites

### Required Software

- **Docker:** Version `20.10` or higher
- **Docker Compose:** Version `1.29` or higher
- **Python:** Version `3.9` or higher
- **pip:** Python package manager

### Installation

1. **Install Docker (if not already installed)**

   - **macOS:**
     ```bash
     brew install --cask docker
     ```
   - **Ubuntu/Linux:**
     ```bash
     sudo apt-get update
     sudo apt-get install docker.io docker-compose
     ```
   - **Windows:**
     - Install **Docker Desktop** from the official Docker website.

2. **Install Python Packages**

   ```bash
   pip install grpcio==1.66.1
   pip install grpcio-tools==1.66.1
   ```

3. **Verify Installation**

   ```bash
   # Check Docker
   docker --version
   docker-compose --version

   # Check Python
   python3 --version
   pip list | grep grpc
   ```

   **Expected output (versions may vary but should be compatible):**

   ```text
   Docker version 20.10.x or higher
   docker-compose version 1.29.x or higher
   Python 3.9.x
   grpcio 1.66.1
   grpcio-tools 1.66.1
   protobuf 5.29.5 (auto-installed with grpcio-tools)
   ```

---

## 🚀 Quick Start Guide

### Step 1: Navigate to the Project

```bash
cd ~/Documents/DS\ Fall\ 2025/
# Your project should be in: Distributed-Task-Scheduler/
```

### Step 2: Generate gRPC Code

```bash
cd Distributed-Task-Scheduler/raft

python -m grpc_tools.protoc   -I./proto   --python_out=.   --grpc_python_out=.   ./proto/raft.proto

cd ..
```

Verify generated files exist:

```bash
ls raft/raft_pb2.py
ls raft/raft_pb2_grpc.py
```

### Step 3: Build Docker Images

```bash
docker-compose -f docker-compose.raft.yml build
```

Typical output:

```text
[+] Building 45.2s (10/10) FINISHED
 => [internal] load build definition
 => => transferring dockerfile
 ...
 => => naming to docker.io/library/distributed-task-scheduler-raft-node1
```

### Step 4: Start the Raft Cluster

```bash
docker-compose -f docker-compose.raft.yml up
```

Expected output:

```text
Creating raft_node1 ... done
Creating raft_node2 ... done
Creating raft_node3 ... done
Creating raft_node4 ... done
Creating raft_node5 ... done
Attaching to raft_node1, raft_node2, raft_node3, raft_node4, raft_node5

raft_node1 | 🔧 Node node1: Initializing...
raft_node1 | Raft Port: 50061
raft_node1 | Client Port: 50151
raft_node1 | ✅ Node node1: Raft node started
raft_node1 | 🗳️ Node node1: Election loop started (role: follower)

raft_node2 | ⚡ Node node2: Starting election for term 1
raft_node2 | 👑 Node node2: Became LEADER in term 1 with 5/5 votes
```

✅ **Success indicators:**

- All 5 nodes start successfully
- Exactly one node becomes **LEADER** (e.g., `👑 Node node2: Became LEADER`)
- Other nodes remain **followers**
- Heartbeat messages appear approximately every 1 second

### Step 5: Submit a Test Operation

Open a new terminal:

```bash
cd Distributed-Task-Scheduler/

# Submit operation (interactive mode)
python3 raft/client.py
```

Interactive session (example):

```text
============================================================
Raft Client - Operation Submission Tool
============================================================

Available nodes:
  0: localhost:50151 (node1)
  1: localhost:50152 (node2)
  2: localhost:50153 (node3)
  3: localhost:50154 (node4)
  4: localhost:50155 (node5)

Select node (0-4): 0

Enter operation (e.g., 'SET x=10'): 100

 Targeting: Node 1 at localhost:50151

 Submitting operation to localhost:50151
   Operation: 100
 Response:
   Success: False
   Message: No leader currently available
   Leader:
```

---

## 📖 Detailed Implementation

### Q3: Leader Election ✅

#### Requirements Met

- **Timeout Settings:**

  - Heartbeat timeout: **1 second**
  - Election timeout: **1.5–3 seconds** (randomized)

- **Election Process:**

  - All nodes start as **followers**
  - Timeout triggers **election**
  - Node becomes **candidate** and requests votes
  - Majority election (3/5 votes needed)
  - Leader sends periodic heartbeats to followers

- **RPC Logging:**

  - Client-side format:  
    `Node <id> sends RPC <name> to Node <id>`
  - Server-side format:  
    `Node <id> runs RPC <name> called by Node <id>`

- **Containerization:**
  - 5 Raft nodes running in separate Docker containers
  - All nodes communicate via gRPC

#### Key Files

- `raft/proto/raft.proto` – gRPC service definitions:

  ```protobuf
  service Raft {
    rpc RequestVote (VoteRequest) returns (VoteResponse);
    rpc AppendEntries (AppendEntriesRequest) returns (AppendEntriesResponse);
  }
  ```

- `raft/election.py` – Leader election logic:

  - `ElectionManager` class handles:
    - Election process
    - Randomized election timeouts (1.5–3 s)
    - Vote request handling
    - Heartbeat management (1 s interval)

- `raft/raft_node.py` – Main server:
  - Starts gRPC servers for inter-node and client communication
  - Coordinates election and replication managers
  - Handles RPC routing

#### How to Verify Q3

```bash
# Start cluster
docker-compose -f docker-compose.raft.yml up
```

In another terminal:

```bash
# Check for leader
docker logs raft_node1 raft_node2 raft_node3 raft_node4 raft_node5 2>&1 | grep "Became LEADER"

# Verify heartbeats on a node
docker logs raft_node1 | grep "Heartbeat"
```

Expected:

- Exactly one node logs `Became LEADER`
- Followers show regular heartbeat messages every ~1 second

---

### Q4: Log Replication ✅

#### Requirements Met

- **Log Management:**

  - Each node maintains a log of operations
  - Log entries include: `term`, `command`, and `index`

- **Leader Operations:**

  1. Receives client request
  2. Appends `<operation, term, index>` to its log
  3. Replicates entries to all followers
  4. Waits for majority ACKs
  5. Commits and applies operation
  6. Returns result to client

- **Follower Operations:**

  - Copies log entries from leader
  - Sends ACKs back to leader
  - Applies committed entries in order
  - Forwards client requests to leader if contacted directly

- **RPC Logging:**

  - Client- and server-side logging for all replication RPCs

- **Containerization:**
  - All 5 nodes support log replication

#### Key Files

- `raft/log_replication.py` – Log replication logic:

  - `LogReplicationManager` class
  - Log structure:
    ```python
    log = [
      {"term": <term>, "command": <command>, "index": <index>},
      ...
    ]
    ```
  - Majority ACK counting
  - Commit index tracking and application

- `raft/client.py` – Client for submitting operations:
  - Can send to any node (leader or follower)
  - Follower automatically forwards to leader
  - Response includes **leader ID**

#### How to Verify Q4

```bash
# Start cluster in background
docker-compose -f docker-compose.raft.yml up -d
sleep 10

# Submit operation
python3 raft/client.py "SET x=10" 0
```

Check replication:

```bash
for i in {1..5}; do
  echo "=== Node $i ==="
  docker logs raft_node$i 2>&1 | grep "Applying entry"
done
```

Expected:

```text
=== Node 1 ===
... Applying entry 1: SET x=10
=== Node 2 ===
... Applying entry 1: SET x=10
...
=== Node 5 ===
... Applying entry 1: SET x=10
```

---

### Q5: Test Cases ✅

All five test cases are implemented as shell scripts under `tests/` and are designed to validate correctness and fault tolerance.

---

## 🧪 Test Cases

### Test Case 1: Normal Leader Election

- **Purpose:** Verify basic election mechanism works correctly.

**Run:**

```bash
bash tests/test1_normal_election.sh
```

**Expected Result:**

```text
=====================================
TEST 1: Normal Leader Election
======================================
[+] Running 5/5
 ✔ Container raft_node5  Running                                                                                                                   0.0s
 ✔ Container raft_node2  Running                                                                                                                   0.0s
 ✔ Container raft_node1  Running                                                                                                                   0.0s
 ✔ Container raft_node4  Running                                                                                                                   0.0s
 ✔ Container raft_node3  Running                                                                                                                   0.0s
Waiting 10 seconds for election...

--- Checking for leader ---
   Node 1 is a follower
 Node 2 is the LEADER
   Node 3 is a follower
   Node 4 is a follower
   Node 5 is a follower

 Test 1 Complete
```

Verifies:

- Exactly one leader is elected
- Other nodes remain followers
- Election completes within 10 seconds
- Leader gets majority votes (≥ 3/5)

---

### Test Case 2: Leader Failure & Re-election

- **Purpose:** Verify fault tolerance and automatic leader recovery.

**Run:**

```bash
bash tests/test2_leader_failure.sh
```

**Expected Result:**

```text
======================================
TEST 2: Leader Failure & Re-election
======================================

--- Finding current leader ---
 Current leader: Node 3

--- Stopping leader (Node 3) ---
raft_node3
Waiting 10 seconds for re-election...

--- Checking for new leader ---
 New leader elected: Node 1

 Test 2 Complete: Leader failover successful
```

Verifies:

- Failed leader is detected
- New election is triggered automatically
- New leader is elected by remaining nodes
- Cluster continues to operate

---

### Test Case 3: Log Replication

- **Purpose:** Verify operations replicate correctly to all nodes.

**Run:**

```bash
bash tests/test3_log_replication.sh
```

**Expected Result:**

```text
======================================
TEST 3: Log Replication
======================================

--- Finding leader ---
 Leader found on port 50151 (Node 1)

--- Submitting operations ---
 Submitting: SET x=10
 Submitting: SET y=20
 Submitting: SET z=30

--- Replication Summary ---
Node 1: 3 entries applied
Node 2: 3 entries applied
Node 3: 3 entries applied
Node 4: 3 entries applied
Node 5: 3 entries applied

 Test 3 Complete
```

Verifies:

- Leader accepts operations
- Operations replicate to all followers
- All nodes apply entries in the same order
- Log consistency across the cluster

---

### Test Case 4: Request Forwarding

- **Purpose:** Verify followers forward client requests to the leader.

**Run:**

```bash
bash tests/test4_request_forwarding.sh
```

**Expected Result:**

```text
======================================
TEST 4: Request Forwarding
======================================

--- Identifying leader and follower ---
 Leader: Node 2
 Follower selected: Node 1

--- Submitting operation to FOLLOWER (Node 1) ---

 Response:
Success: True
Message: Operation committed successfully
Leader: node2

--- Checking follower logs ---
 Follower correctly forwarded request to leader

 Test 4 Complete
```

Verifies:

- Follower receives client request
- Follower detects it is not leader
- Follower forwards request to correct leader
- Operation commits successfully
- Client receives leader ID in response

---

### Test Case 5: Network Partition (Split-Brain Prevention)

- **Purpose:** Verify system prevents split-brain during network partition.

**Run:**

```bash
bash tests/test5_network_partition.sh
```

**Expected Result:**

```text
======================================
TEST 5: Network Partition
======================================

--- Finding current leader ---
 Current leader: Node 3

--- Creating network partition ---
Minority partition: Nodes 1, 2 (cannot elect leader)
Majority partition: Nodes 3, 4, 5 (can elect leader)
 Paused nodes 1 and 2

Waiting 10 seconds for partition effects...

--- Checking majority partition ---
 Majority partition elected leader: Node 4

--- Healing partition ---
 Unpaused nodes 1 and 2

--- Verifying minority nodes rejoined ---
 Node 1 rejoined cluster
 Node 2 rejoined cluster

 Test 5 Complete: Split brain prevented
```

Verifies:

- Minority partition (2/5 nodes) cannot elect a leader
- Majority partition (3/5 nodes) can elect/maintain a leader
- No split-brain scenario occurs
- Nodes automatically rejoin after partition heals

---

## Test Execution Durations

All tests have been executed and timed for performance verification:

| Test Case  | Description                  | Duration          |
| ---------- | ---------------------------- | ----------------- |
| **Test 1** | Normal Leader Election       | **11.15 seconds** |
| **Test 2** | Leader Failure & Re-election | **30.70 seconds** |
| **Test 3** | Log Replication              | **25.36 seconds** |
| **Test 4** | Request Forwarding           | **20.58 seconds** |
| **Test 5** | Network Partition            | **25.79 seconds** |
| **TOTAL**  | **Complete Test Suite**      | **3:11.50**       |

**Test Results:** 5/5 PASSED (100% success rate)

**Notes:**

- Test 2 takes longest due to 10-second re-election wait period
- Test 1 is fastest as it only requires initial startup and election
- Average test duration: ~22.7 seconds per test
- All tests completed successfully in a single execution

---

## Running All Tests

### Complete Test Suite

First time only, make scripts executable:

```bash
chmod +x tests/*.sh
```

Then run all tests:

```bash
bash tests/run_all_tests.sh
```

To time the complete test suite:

```bash
time bash tests/run_all_tests.sh
```

Expected summary:

```text
==========================================
RAFT IMPLEMENTATION - COMPLETE TEST SUITE
==========================================

Cleaning up previous runs...

==========================================
Running: test1_normal_election.sh
==========================================
... [test output] ...
test1_normal_election.sh
PASSED
...
==========================================
TEST SUITE SUMMARY
==========================================
Total Tests: 5
Passed: 5
Failed: 0

 All tests passed!
```

### Run Individually

```bash
# Test 1: Normal Election
bash tests/test1_normal_election.sh

# Test 2: Leader Failure
bash tests/test2_leader_failure.sh

# Test 3: Log Replication
bash tests/test3_log_replication.sh

# Test 4: Request Forwarding
bash tests/test4_request_forwarding.sh

# Test 5: Network Partition
bash tests/test5_network_partition.sh
```

---

## 📊 Manual Testing & Verification

### Check Cluster Status

```bash
# View all containers
docker ps

# Check which node is leader
for i in {1..5}; do
  if docker logs raft_node$i 2>&1 | grep -q "Became LEADER"; then
    echo "Node $i is the LEADER"
  else
    echo "Node $i is a follower"
  fi
done
```

### View Node Logs

```bash
# View specific node
docker logs raft_node1

# Follow logs in real-time
docker logs -f raft_node2

# View last 20 lines
docker logs --tail 20 raft_node3

# View all nodes (concise)
docker-compose -f docker-compose.raft.yml logs --tail=10
```

### Submit Operations Manually

```bash
# Interactive mode
python3 raft/client.py

# Command line mode - submit to node 1
python3 raft/client.py "SET x=10" 0

# Submit to node 3
python3 raft/client.py "SET y=20" 2

# Submit multiple operations
python3 raft/client.py "SET a=1" 0
python3 raft/client.py "SET b=2" 0
python3 raft/client.py "SET c=3" 0
```

### Verify Log Consistency

```bash
# Check all nodes have the same entries
for i in {1..5}; do
  echo "=== Node $i Log ==="
  docker logs raft_node$i 2>&1 | grep "Applying entry"
done

# Count entries per node
for i in {1..5}; do
  COUNT=$(docker logs raft_node$i 2>&1 | grep -c "Applying entry")
  echo "Node $i: $COUNT entries"
done
```

### Manual Leader Failure Test

```bash
# 1. Find current leader
LEADER=$(docker logs raft_node1 raft_node2 raft_node3 raft_node4 raft_node5 2>&1 | grep "Became LEADER" | head -1 | grep -o 'node[0-9]')
echo "Current leader: $LEADER"

# 2. Stop the leader
docker stop raft_$LEADER

# 3. Watch for new election (in another terminal)
watch -n 1 'docker logs raft_node1 raft_node2 raft_node4 raft_node5 2>&1 | grep -E "Starting election|Became LEADER" | tail -5'

# 4. Restart stopped node
docker start raft_$LEADER

# 5. Verify it rejoined
docker logs raft_$LEADER | tail -20
```

---

## Troubleshooting

### Issue 1: "Connection refused" when running client

**Symptom:**

```text
 Error: failed to connect to all addresses
```

**Solution:**

```bash
# Check if containers are running
docker ps | grep raft_node

# If not running, start them
docker-compose -f docker-compose.raft.yml up -d
sleep 10

# Verify ports are exposed
docker port raft_node1
# Expected:
# 50061/tcp -> 0.0.0.0:50061
# 50151/tcp -> 0.0.0.0:50151
```

---

### Issue 2: No leader elected

**Symptom:**

```text
 No leader found!
```

**Solution:**

```bash
# Check logs for election attempts
docker logs raft_node1 | grep "Starting election"

# Check for gRPC errors
docker logs raft_node1 | grep -i "error"

# Restart cluster
docker-compose -f docker-compose.raft.yml down -v
docker-compose -f docker-compose.raft.yml up
```

---

### Issue 3: Logs not replicating

**Symptom:**

```text
Node 1: 3 entries
Node 2: 0 entries   #  Missing entries
```

**Solution:**

```bash
# Check if leader is sending
docker logs raft_node1 | grep "sends RPC AppendEntries"

# Check if followers are receiving
docker logs raft_node2 | grep "runs RPC AppendEntries"

# Look for errors
docker logs raft_node2 | grep "success.*False"

# Restart node with issues
docker restart raft_node2
```

---

### Issue 4: Tests fail or hang

**Solution:**

```bash
# Clean everything and start fresh
docker-compose -f docker-compose.raft.yml down -v
docker system prune -f

# Rebuild from scratch
docker-compose -f docker-compose.raft.yml build --no-cache

# Start and wait longer
docker-compose -f docker-compose.raft.yml up -d
sleep 15

# Run test again
bash tests/test1_normal_election.sh
```

---

### Issue 5: Port already in use

**Symptom:**

```text
Error: port is already allocated
```

**Solution:**

```bash
# Find what's using the port
lsof -i :50151

# Kill the process
kill -9 <PID>

# Or use different ports in docker-compose.raft.yml
# Example: change "50151:50151" to "50161:50151"
```

---

## Understanding the Logs

### Election

```text
⚡ Node node2: Starting election for term 1
Node node2 sends RPC RequestVote to Node node1
Node node1 runs RPC RequestVote called by Node node2
Node node1: Voted for node2 in term 1
Node node2: Became LEADER in term 1 with 5/5 votes
```

### Heartbeats

```text
Node node2 sends RPC AppendEntries to Node node1
Node node1 runs RPC AppendEntries called by Node node2
 Node node1: Heartbeat received from leader node2
```

### Log Replication

```text
 Node node2: Received client request
Operation: SET x=10
 Node node2: Processing as leader
 Node node2 (LEADER): Appended entry at index 1: SET x=10
Node node2 sends RPC AppendEntries to Node node1 (entries: 1)
Node node1 runs RPC AppendEntries called by Node node2 (entries: 1)
Node node1 (FOLLOWER): Replicated 1 entries from leader
Node node2: Received ACKs from majority (5/5)
Node node2 (LEADER): Committed entry at index 1
Node node2: Applying entry 1: SET x=10
Node node1: Applying entry 1: SET x=10
```

---

## Clean Up

### Stop Cluster

```bash
# Stop containers (keep data)
docker-compose -f docker-compose.raft.yml stop

# Stop and remove containers
docker-compose -f docker-compose.raft.yml down

# Stop and remove everything (including volumes)
docker-compose -f docker-compose.raft.yml down -v
```

### Complete Cleanup

```bash
# Remove all Raft containers and images
docker-compose -f docker-compose.raft.yml down -v
docker rmi $(docker images | grep raft | awk '{print $3}')

# Clean Docker system
docker system prune -af --volumes
```

## Capturing Screenshots for Report

For each test case, capture:

1. **Test execution command**
2. **Test output showing success**
3. **Relevant logs** showing the internal Raft behavior

### Example Workflow (Test 1: Normal Election)

```bash
# 1. Start fresh
docker-compose -f docker-compose.raft.yml down -v
docker-compose -f docker-compose.raft.yml up -d

# 2. Wait for election
sleep 10

# 3. Show running containers
docker ps

# 4. Show election logs
docker logs raft_node1 raft_node2 raft_node3 raft_node4 raft_node5 2>&1 | grep -E "Starting election|Became LEADER|Voted for"


# 5. Run test script
bash tests/test1_normal_election.sh
```

Repeat similar steps for Tests 2–5.

---

## Common Commands Reference

```bash
# Start cluster
docker-compose -f docker-compose.raft.yml up -d

# Stop cluster
docker-compose -f docker-compose.raft.yml down

# View logs
docker logs raft_node1

# Follow logs
docker logs -f raft_node1

# Run a specific test
bash tests/test1_normal_election.sh

# Submit operation
python3 raft/client.py "SET x=10" 0

# Check leader
docker logs raft_node1 raft_node2 raft_node3 raft_node4 raft_node5 2>&1 | grep "Became LEADER"

# Clean everything
docker-compose -f docker-compose.raft.yml down -v
```
