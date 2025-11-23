# Testing Guide - Assignment 3, Q2

## Testing Objectives

This guide helps you verify that your Two-Phase Commit implementation meets all Q2 requirements:

1. Complete voting phase (Q1)
2. Complete decision phase (Q2)
3. Intra-node communication via gRPC
4. Proper RPC logging format
5. All 5+ participants working

---

## Quick Start Testing

### 1. Start the System

```bash
./build_and_run.sh
```

Wait for all services to start (about 15 seconds).

### 2. Run Basic Test

```bash
python test_client.py single
```

### 3. Check Logs

```bash
docker-compose logs | grep "sends RPC\|receives RPC" | head -20
```

You should see RPC messages in the exact format:

```
Phase VOTING of Node COORDINATOR sends RPC VoteRequest to Phase VOTING of Node PARTICIPANT_1
Phase DECISION of Node COORDINATOR sends RPC GlobalDecision to Phase DECISION of Node PARTICIPANT_1
```

---

## Detailed Test Scenarios

### Test 1: Verify All Containers Running

**Command:**

```bash
docker-compose ps
```

**Expected Output:**

```
NAME                              STATE    PORTS
2pc_coordinator                   Up       0.0.0.0:50050->50050/tcp
participant_driver_service        Up       0.0.0.0:50051->50051/tcp, 0.0.0.0:60051->60051/tcp
participant_payment_service       Up       0.0.0.0:50052->50052/tcp, 0.0.0.0:60052->60052/tcp
participant_booking_service       Up       0.0.0.0:50053->50053/tcp, 0.0.0.0:60053->60053/tcp
participant_notification_service  Up       0.0.0.0:50054->50054/tcp, 0.0.0.0:60054->60054/tcp
participant_analytics_service     Up       0.0.0.0:50055->50055/tcp, 0.0.0.0:60055->60055/tcp
```

**Verification:**

- 6 containers total
- All showing "Up" status
- Each participant has 2 ports exposed

---

### Test 2: Verify Intra-Node Communication

**Repeat for all participants:**

```bash
for container in participant_driver_service participant_payment_service participant_booking_service participant_notification_service participant_analytics_service; do
    echo "Checking $container..."
    docker exec $container netstat -tuln | grep -E "tcp.*LISTEN" | grep -E "5005|6005"
done
```

---

### Test 3: Single Transaction - Success Scenario

**Command:**

```bash
python test_client.py single
```

**Expected Output:**

```
================================================================================
  TWO-PHASE COMMIT TEST - Ride Booking Transaction
================================================================================

--- Transaction Details ---
Transaction ID: abc-def-123...
Operation: BOOK_RIDE
Parameters:
  • rider_id: rider_456
  • driver_id: driver_789
  • amount: 35.50
  ...

--- Transaction Result ---
Transaction ID: abc-def...
Success: True
Final Decision: GLOBAL_COMMIT
Message: Transaction GLOBAL_COMMIT
Execution Time: 0.234 seconds

Transaction SUCCESSFUL - GLOBAL_COMMIT
```

**Verification:**

- Transaction ID generated
- Success: True
- Final Decision: GLOBAL_COMMIT
- Completed in reasonable time (<1 second)

---

### Test 4: Check Voting Phase Logs

**Command:**

```bash
docker-compose logs | grep "Phase VOTING" | grep "sends RPC\|receives RPC" | head -20
```

**Expected Output:**

```
Phase VOTING of Node COORDINATOR sends RPC VoteRequest to Phase VOTING of Node PARTICIPANT_1
Phase VOTING of Node PARTICIPANT_1 receives RPC VoteRequest from Phase VOTING of Node COORDINATOR
Phase VOTING of Node PARTICIPANT_1 sends RPC NotifyVote to Phase DECISION of Node PARTICIPANT_1
Phase VOTING of Node PARTICIPANT_1 sends VOTE_COMMIT to Phase VOTING of Node COORDINATOR
Phase VOTING of Node COORDINATOR sends RPC VoteRequest to Phase VOTING of Node PARTICIPANT_2
...
```

**Verification:**

- Coordinator sends VoteRequest to all participants
- Participants receive VoteRequest
- Participants notify their decision phase
- Participants respond with vote to coordinator
- Exact log format used

---

### Test 5: Check Decision Phase Logs

**Command:**

```bash
docker-compose logs | grep "Phase DECISION" | grep "sends RPC\|receives RPC" | head -20
```

**Expected Output:**

```
Phase DECISION of Node PARTICIPANT_1 receives RPC NotifyVote from Phase VOTING of Node PARTICIPANT_1
Phase DECISION of Node COORDINATOR sends RPC GlobalDecision to Phase DECISION of Node PARTICIPANT_1
Phase DECISION of Node PARTICIPANT_1 receives RPC GlobalDecision from Phase DECISION of Node COORDINATOR
Phase DECISION of Node PARTICIPANT_1 sends acknowledgment to Phase DECISION of Node COORDINATOR
...
```

**Verification:**

- Decision phase receives vote notification from voting phase (intra-node)
- Coordinator sends GlobalDecision to all participants
- Participants receive GlobalDecision
- Participants acknowledge decision
- Exact log format used

---

### Test 6: Intra-Node Communication Logs

**Command:**

```bash
docker-compose logs | grep "NotifyVote"
```

**Expected Output:**

```
Phase VOTING of Node PARTICIPANT_1 sends RPC NotifyVote to Phase DECISION of Node PARTICIPANT_1
Phase DECISION of Node PARTICIPANT_1 receives RPC NotifyVote from Phase VOTING of Node PARTICIPANT_1
Phase VOTING of Node PARTICIPANT_2 sends RPC NotifyVote to Phase DECISION of Node PARTICIPANT_2
Phase DECISION of Node PARTICIPANT_2 receives RPC NotifyVote from Phase VOTING of Node PARTICIPANT_2
...
```

**Verification:**

- Each participant's voting phase notifies its decision phase
- Communication happens within same node (same PARTICIPANT_X ID)
- All 5 participants show intra-node communication

---

### Test 7: Failed Transaction - Abort Scenario

**Command:**

```bash
# Run multiple times until you see a failure
python test_client.py multiple 5
```

**Expected Output (for failed transaction):**

```
--- Transaction Details ---
...

Transaction SUCCESSFUL - GLOBAL_COMMIT  (some will succeed)

Transaction FAILED - GLOBAL_ABORT        (some will fail)
   Reason: Transaction aborted: Failed participants: [...]
```

**Check abort logs:**

```bash
docker-compose logs | grep "VOTE_ABORT\|GLOBAL_ABORT" | tail -30
```

**Expected:**

```
[PARTICIPANT_2 - VOTING] Decision: VOTE_ABORT - Insufficient funds
Phase VOTING of Node PARTICIPANT_2 sends VOTE_ABORT to Phase VOTING of Node COORDINATOR
[COORDINATOR] Decision: GLOBAL_ABORT
Phase DECISION of Node COORDINATOR sends RPC GlobalDecision to Phase DECISION of Node PARTICIPANT_1
[PARTICIPANT_1 - DECISION] Received GLOBAL_ABORT for transaction...
[PARTICIPANT_1 - DECISION] Transaction ABORTED locally
```

**Verification:**

- At least one participant votes ABORT
- Coordinator decides GLOBAL_ABORT
- All participants execute local abort
- Even participants who voted COMMIT abort when coordinator says so

---

### Test 8: Multiple Transactions Statistics

**Command:**

```bash
python test_client.py multiple 10
```

**Expected Output:**

```
================================================================================
  TEST SUMMARY
================================================================================
Total Transactions: 10
  Successful (GLOBAL_COMMIT): 7
  Failed (GLOBAL_ABORT): 3
  Errors: 0

Success Rate: 70.0%
================================================================================
```

**Verification:**

- All transactions complete (no errors)
- Mix of successful and failed transactions
- Success rate reasonable (typically 60-85%)
- No network errors or timeouts

---

### Test 9: Verify Transaction States

**Command:**

```bash
# Look for transaction state progression
docker-compose logs participant1 | grep "PREPARED\|COMMITTED\|ABORTED" | head -20
```

**Expected Output:**

```
[PARTICIPANT_1 - DECISION] Transaction abc-123... in PREPARED state, waiting for coordinator decision
[PARTICIPANT_1 - DECISION] Executing commit for BOOK_RIDE
[PARTICIPANT_1 - DECISION] Transaction COMMITTED locally

[PARTICIPANT_1 - DECISION] Transaction xyz-789... in PREPARED state, waiting for coordinator decision
[PARTICIPANT_1 - DECISION] Rolling back BOOK_RIDE
[PARTICIPANT_1 - DECISION] Transaction ABORTED locally
```

**Verification:**

- Transactions enter PREPARED state after voting COMMIT
- Transactions wait for coordinator decision
- Local commit executed on GLOBAL_COMMIT
- Local abort executed on GLOBAL_ABORT

---

### Test 10: Check All RPC Types

**Command:**

```bash
docker-compose logs | grep "sends RPC" | awk '{print $NF}' | sort | uniq
```

**Expected Output:**

```
GlobalDecision
NotifyVote
VoteRequest
```

**Verification:**

- VoteRequest RPC present (voting phase)
- NotifyVote RPC present (intra-node)
- GlobalDecision RPC present (decision phase)

---

## Complete Test Sequence

Run this complete test sequence to verify everything:

```bash
# 1. Clean start
docker-compose down -v
./build_and_run.sh

# 2. Wait for startup
sleep 15

# 3. Verify containers
docker-compose ps | grep -c "Up"  # Should show 6

# 4. Check ports
for port in 50050 50051 50052 50053 50054 50055; do
    echo "Port $port:" && timeout 1 bash -c "echo > /dev/tcp/localhost/$port" 2>/dev/null && echo "✅ Open" || echo "❌ Closed"
done

# 5. Run single test
python test_client.py single

# 6. Verify RPC logging
docker-compose logs | grep "sends RPC\|receives RPC" | wc -l
# Should show many lines (30+)

# 7. Check voting phase
docker-compose logs | grep "Phase VOTING" | grep "sends RPC" | wc -l
# Should show multiple lines

# 8. Check decision phase
docker-compose logs | grep "Phase DECISION" | grep "sends RPC" | wc -l
# Should show multiple lines

# 9. Check intra-node communication
docker-compose logs | grep "NotifyVote" | wc -l
# Should show 10+ lines (5 participants × 2 log messages each per transaction)

# 10. Run multiple transactions
python test_client.py multiple 5

# 11. Verify both success and failure scenarios
docker-compose logs | grep -E "GLOBAL_COMMIT|GLOBAL_ABORT" | grep "Decision:" | tail -10

# 12. Check for errors
docker-compose logs | grep -i "error\|exception" | wc -l
# Should be 0 or very few

# 13. Final status
docker-compose ps
```

---

## 📸 Screenshots to Capture

For your submission, capture these screenshots:

### Screenshot 1: Container Status

```bash
docker-compose ps
```

### Screenshot 2: Successful Transaction

```bash
python test_client.py single
```

(Make sure it shows GLOBAL_COMMIT)

### Screenshot 3: Failed Transaction Logs

```bash
docker-compose logs | grep "VOTE_ABORT\|GLOBAL_ABORT" | tail -20
```

### Screenshot 4: RPC Logging Format

```bash
docker-compose logs | grep "sends RPC\|receives RPC" | head -30
```

### Screenshot 5: Intra-Node Communication

```bash
docker-compose logs | grep "NotifyVote"
```

### Screenshot 6: Multiple Transactions Summary

```bash
python test_client.py multiple 10
```

(Show the final summary with success/fail counts)

---

## 🐛 Troubleshooting Failed Tests

### Test fails: "Connection refused"

```bash
# Check if containers are running
docker-compose ps

# Check logs for startup errors
docker-compose logs | grep -i "error\|exception"

# Restart
docker-compose restart
```

### Test fails: "Missing RPC logs"

```bash
# Ensure you're checking logs AFTER running test
python test_client.py single
docker-compose logs | grep "sends RPC"

# If no logs, check Python logging configuration
docker-compose logs coordinator | grep "logging"
```

### Test fails: "Intra-node communication not working"

```bash
# Verify decision phase is running
docker exec participant_driver_service netstat -tuln | grep 60051

# Check for localhost connectivity issues
docker exec participant_driver_service ping -c 1 localhost

# Check logs for connection errors
docker-compose logs participant1 | grep "Failed to notify"
```

---

## 📊 Expected Success Metrics

Based on the randomized failure simulation:

- **Success Rate**: 60-85%
- **Typical Results** (10 transactions):
  - Successful: 6-8
  - Failed: 2-4
  - Errors: 0

If your success rate is:

- **<50%**: Check if services are failing to start or network issues
- **100%**: Check if failure simulation is working (should have some fails)
- **Variable**: Normal! This is expected with randomized logic
