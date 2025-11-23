# Assignment 3: Two-Phase Commit Protocol Implementation on ride sharing

**Course:** CSE 5306 - Distributed Systems  
**Project:** Ride-Sharing Distributed System  
**Implementation:** Two-Phase Commit (2PC) for Distributed Transactions

Group: 17
Pinky Patel (1002251887)
Purva Dankhara(1002260167)

## Overview

This project implements a **Two-Phase Commit (2PC) protocol** for distributed transaction management in a ride-sharing application. The implementation includes:

- **Q1: Voting Phase** - Coordinator requests votes from participants, participants vote to commit or abort
- **Q2: Decision Phase** - Coordinator makes final decision based on votes, participants execute commit or abort

### What is Two-Phase Commit?

2PC is a distributed algorithm that ensures all participants in a distributed transaction either commit or abort the transaction, maintaining atomicity across multiple nodes.

**Example Use Case:** Booking a ride requires:

1. **Driver Service** - Reserve driver availability
2. **Payment Service** - Authorize payment
3. **Booking Service** - Create booking record
4. **Notification Service** - Queue notifications
5. **Analytics Service** - Update metrics

All these operations must **succeed together or fail together** (atomicity).

---

## Architecture

### System Components

```
┌─────────────────────────────────────────────────────────────────┐
│                         CLIENT                                   │
│                   (Booking Request)                              │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ↓
┌─────────────────────────────────────────────────────────────────┐
│                      COORDINATOR                                 │
│              (Manages 2PC Protocol)                              │
│                   Port: 50050                                    │
└─────┬──────────┬──────────┬──────────┬──────────┬──────────────┘
      │          │           │          │          │
      ↓          ↓           ↓          ↓          ↓
┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐
│Participant│ │Participant│ │Participant│ │Participant│ │Participant│
│     1     │ │     2     │ │     3     │ │     4     │ │     5     │
│  Driver   │ │  Payment  │ │  Booking  │ │  Notify   │ │ Analytics│
│  Service  │ │  Service  │ │  Service  │ │  Service  │ │  Service  │
│           │ │           │ │           │ │           │ │           │
│ Voting    │ │ Voting    │ │ Voting    │ │ Voting    │ │ Voting    │
│ :50051    │ │ :50052    │ │ :50053    │ │ :50054    │ │ :50055    │
│           │ │           │ │           │ │           │ │           │
│ Decision  │ │ Decision  │ │ Decision  │ │ Decision  │ │ Decision  │
│ :60051    │ │ :60052    │ │ :60053    │ │ :60054    │ │ :60055    │
└──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘
```

### Two-Phase Commit Flow

#### Phase 1: Voting Phase (Q1)

```
1. Coordinator sends VOTE-REQUEST to all participants
2. Each participant evaluates if it can commit
3. Participant responds: VOTE-COMMIT or VOTE-ABORT
4. Coordinator collects all votes
```

#### Phase 2: Decision Phase (Q2)

```
5. If ALL voted COMMIT → Coordinator decides GLOBAL-COMMIT
   If ANY voted ABORT → Coordinator decides GLOBAL-ABORT
6. Coordinator sends decision to all participants
7. Participants execute local commit or abort
8. Participants acknowledge completion
```

## Prerequisites

### Software Requirements

- **Python**: 3.9 or higher
- **Docker**: 20.10 or higher
- **Docker Compose**: 1.29 or higher
- **Git**: For version control

### Python Packages

```bash
pip install grpcio==1.60.0
pip install grpcio-tools==1.60.0
pip install protobuf==4.25.1
```

### System Requirements

- **OS**: Linux, macOS, or Windows (with WSL2)
- **RAM**: 4GB minimum, 8GB recommended
- **Disk**: 2GB free space
- **Network**: All required ports available (50050-50055, 60051-60055)

## Project Structure

```
assignment-3 -Ride-sharing system - 2pc/
two_phase_commit
├── README.md                           # This file
├── two_phase_commit.proto              # gRPC protocol definition
├── coordinator.py                      # Coordinator implementation
├── participant.py                      # Participant implementation
├── test_client.py                      # Test client
├── requirements.txt                    # Python dependencies
├── Dockerfile.coordinator              # Coordinator container
├── Dockerfile.participant              # Participant container
├── docker-compose.yml                  # Container orchestration
├── build_and_run.sh                    # Build and run script
└── screenshots/                        # Test screenshots
    ├── voting_phase/
    └── decision_phase/
```

---

## Installation & Setup

### Step 1: Clone or Navigate to Project Directory

```bash
cd cse-5306-ride-share-ds-project-assignment-2
mkdir two_phase_commit
cd two_phase_commit

```

### Step 2: Copy Project Files

Ensure you have all the files listed in [Project Structure](#project-structure) in this directory.

### Step 3: Install Python Dependencies

```bash
pip install -r requirements.txt
```

### Step 4: Generate gRPC Code

```bash
cd two_phase_commit
python -m grpc_tools.protoc \
    -I. \
    --python_out=. \
    --grpc_python_out=. \
    two_phase_commit.proto
```

This generates:

- `two_phase_commit_pb2.py` - Message definitions
- `two_phase_commit_pb2_grpc.py` - Service definitions

cd ..

**Verify generation:**

```bash
ls -la two_phase_commit_pb2*
```

### Step 5: Make Build Script Executable

```bash
chmod +x build_and_run.sh
```

## Running the System

### Option 1: Automated (Recommended)

```bash
cd
```

This script will:

1. Generate gRPC code
2. Stop any existing containers
3. Build Docker images
4. Start all 6 containers (1 coordinator + 5 participants)
5. Wait for initialization
6. Display system status

**Expected Output:**

```

[1/6] Generating gRPC code from proto file...
Proto code generated successfully

[2/6] Cleaning up existing containers...
Cleanup complete

[3/6] Building Docker images...
Docker images built successfully

[4/6] Starting Docker containers...
Containers started successfully

[5/6] Waiting for services to be ready...
..........

[6/6] Verifying container status...
All 6 containers are running

Running Containers:
NAME                              STATE    PORTS
2pc_coordinator                   Up       0.0.0.0:50050->50050/tcp
participant_driver_service        Up       0.0.0.0:50051->50051/tcp, 0.0.0.0:60051->60051/tcp
participant_payment_service       Up       0.0.0.0:50052->50052/tcp, 0.0.0.0:60052->60052/tcp
participant_booking_service       Up       0.0.0.0:50053->50053/tcp, 0.0.0.0:60053->60053/tcp
participant_notification_service  Up       0.0.0.0:50054->50054/tcp, 0.0.0.0:60054->60054/tcp
participant_analytics_service     Up       0.0.0.0:50055->50055/tcp, 0.0.0.0:60055->60055/tcp

System is ready!
```

### Option 2: Manual Steps

```bash
# 1. Generate gRPC code (if not done)
python -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. two_phase_commit.proto

# 2. Build Docker images
docker-compose build

# 3. Start containers
docker-compose up -d

# 4. Wait for startup
sleep 10

# 5. Verify all containers running
docker-compose ps
```

### Verify System is Running

```bash
# Check all 6 containers are "Up"
docker-compose ps

# Expected output: 6 containers with "Up" status
```

## 🧪 Testing

### Test 1: Single Transaction

```bash
python test_client.py single
```

**Expected Output:**

```
Waiting for services to be ready...

====================================================
  TWO-PHASE COMMIT TEST - Ride Booking Transaction
====================================================

--- Transaction Details ---
Transaction ID: 63746d0d-cb12-4aae-b5ef-b4d627d0e4e7
Operation: BOOK_RIDE
Parameters:
  • destination: DFW Airport
  • driver_id: driver_499
  • pickup: Downtown Dallas
  • amount: 69.00
  • rider_id: rider_999

--- Sending Transaction to Coordinator ---
Initiating 2PC protocol...

--- Transaction Result ---
Transaction ID: 63746d0d...
Success: True
Final Decision: GLOBAL_COMMIT
Message: Transaction GLOBAL_COMMIT
Execution Time: 0.038 seconds

 Transaction SUCCESSFUL - GLOBAL_COMMIT
==================================================
```

### Test 2: Multiple Transactions

```bash
python test_client.py multiple 5
```

**Expected Output:**

```
Waiting for services to be ready...

====================================================
  TESTING 5 TRANSACTIONS
====================================================

Transaction 1/5
──────────────────────────────────────────────────

Transaction FAILED - GLOBAL_ABORT
  Reason: Transaction GLOBAL_ABORT

Transaction 2/5
──────────────────────────────────────────────────

Transaction FAILED - GLOBAL_ABORT
  Reason: Transaction GLOBAL_ABORT

Transaction 3/5
──────────────────────────────────────────────────

Transaction FAILED - GLOBAL_ABORT
  Reason: Transaction GLOBAL_ABORT

Transaction 4/5
──────────────────────────────────────────────────

 Transaction SUCCESSFUL - GLOBAL_COMMIT

Transaction 5/5
──────────────────────────────────────────────────

 Transaction SUCCESSFUL - GLOBAL_COMMIT

====================================================
  TEST SUMMARY
====================================================
Total Transactions: 5
 Successful (GLOBAL_COMMIT): 2
 Failed (GLOBAL_ABORT): 3
 Errors: 0

Success Rate: 40.0%
==================================================
```

### Test 3: Interactive Mode

```bash
python test_client.py
```

**Menu Options:**

```
Waiting for services to be ready...

==================================================
  TWO-PHASE COMMIT TEST MENU
==================================================
1. Run single transaction (detailed)
2. Run multiple transactions (5)
3. Run multiple transactions (10)
4. Test failure scenarios
5. Stress test (20 transactions)
6. Exit
==================================================

Enter your choice (1-6): 4

====================================================
  TESTING PARTICIPANT FAILURE SCENARIO
====================================================
Note: Some participants are configured to randomly fail votes
This simulates real-world scenarios like insufficient funds,
unavailable drivers, booking conflicts, etc.


Attempt 1/3:

Transaction FAILED - GLOBAL_ABORT
  Reason: Transaction GLOBAL_ABORT

Attempt 2/3:

 Transaction SUCCESSFUL - GLOBAL_COMMIT

Attempt 3/3:

 Transaction SUCCESSFUL - GLOBAL_COMMIT

Press Enter to continue...
```

---

## 🔍 Monitoring

### View Real-Time Logs

#### All Services

```bash
docker-compose logs -f
```

#### Coordinator Only

```bash
docker-compose logs -f coordinator
```

#### Specific Participant

```bash
docker-compose logs -f participant1
```

### Filter Logs by Phase

#### Voting Phase Logs

```bash
docker-compose logs | grep "Phase VOTING"
```

#### Decision Phase Logs

```bash
docker-compose logs | grep "Phase DECISION"
```

#### RPC Calls

```bash
docker-compose logs | grep "sends RPC\|runs RPC"
```

#### Vote Messages

```bash
docker-compose logs | grep "vote"
```

#### Commit/Abort Decisions

```bash
docker-compose logs | grep "GLOBAL_COMMIT\|GLOBAL_ABORT"
```

**Voting Phase → Decision Phase:**

```python
# participant.py, line ~80
def _notify_decision_phase(self, transaction_id, vote, ...):
    # Connect to local decision phase
    channel = grpc.insecure_channel(f'localhost:{decision_phase_port}')
    stub = IntraNodeDecisionPhaseStub(channel)
    stub.NotifyVote(...)
```

**RPC Logging Format:**

Client side (sending):

```python
logger.info(f"Phase VOTING of Node {self.node_id} sends RPC VoteRequest "
           f"to Phase VOTING of Node {participant_id}")
```

Server side (receiving):

```python
logger.info(f"Node {self.node_id} runs RPC RequestVote called by Node {caller_id}")
```

---

## 🐛 Troubleshooting

### Issue 1: "ModuleNotFoundError: No module named 'two_phase_commit_pb2'"

**Cause:** Proto files not generated

**Solution:**

```bash
python -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. two_phase_commit.proto
ls two_phase_commit_pb2*.py  # Verify files exist
```

### Issue 2: "Error: port is already allocated"

**Cause:** Port already in use by another process

**Solution:**

```bash
# Stop all containers
docker-compose down

# Kill processes using the ports (Linux/Mac)
lsof -ti:50050 | xargs kill -9
lsof -ti:50051 | xargs kill -9
# ... repeat for other ports

# Or restart Docker
docker-compose down
docker system prune -f
docker-compose up -d
```

### Issue 3: Containers not communicating

**Cause:** Network issues

**Solution:**

```bash
# Check network
docker network inspect two-phase-commit_twopc-network

# Restart containers
docker-compose down
docker-compose up -d

# Check logs for connection errors
docker-compose logs | grep -i "error\|failed"
```

### Issue 4: Test client times out

**Cause:** Coordinator or participants not responding

**Solution:**

```bash
# Check if all containers are up
docker-compose ps

# Restart system
docker-compose restart

# Increase timeout in test_client.py if needed
```

### Issue 5: "No such file or directory" when running build script

**Cause:** Script not executable or wrong directory

**Solution:**

```bash
# Make executable
chmod +x build_and_run.sh

# Ensure you're in correct directory
pwd  # Should be in two-phase-commit/

# Run with bash explicitly
bash build_and_run.sh
```

---

## 📸 Screenshots for Submission

### Required Screenshots

#### 1. System Startup

```bash
docker-compose ps
```

#### 2. Voting Phase - Vote Request

```bash
docker-compose logs | grep "GLOBAL_COMMIT\|GLOBAL_ABORT" | head -5
```

#### 3. Voting Phase - Votes Received

```bash
docker-compose logs | grep "VOTE_COMMIT\|VOTE_ABORT" | head -10
```

#### 4. Decision Phase - Global Decision

```bash
docker-compose logs | grep "GLOBAL_COMMIT\|GLOBAL_ABORT" | head -5
```

#### 6. RPC Logging Format

```bash
docker-compose logs | grep "sends RPC\|runs RPC" | head -20
```

#### 7. Successful Transaction

```bash
python test_client.py single
```

#### 8. Failed Transaction & Multiple Transactions Summary

```bash
python test_client.py multiple 10

```

#### 9. Intra-Node Communication

```bash
docker-compose logs | grep "NotifyVote"
```

## 📚 References

- **Two-Phase Commit Protocol**: [Wikipedia]()
- **gRPC Documentation**: [grpc.io](https://grpc.io/docs/)
- **Docker Compose**: [docs.docker.com](https://docs.docker.com/compose/)
- **Protocol Buffers**: [developers.google.com](https://developers.google.com/protocol-buffers)
