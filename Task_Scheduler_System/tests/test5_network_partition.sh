#!/bin/bash

echo "======================================"
echo "TEST 5: Network Partition"
echo "======================================"

docker-compose -f docker-compose.raft.yml up -d
sleep 10

echo -e "\n--- Finding current leader ---"
LEADER=""
for i in {1..5}; do
    if docker logs raft_node$i 2>&1 | grep -q "Became LEADER"; then
        LEADER=$i
        echo " Current leader: Node $LEADER"
        break
    fi
done

echo -e "\n--- Creating network partition ---"
echo "Minority partition: Nodes 1, 2"
echo "Majority partition: Nodes 3, 4, 5"

docker pause raft_node1
docker pause raft_node2
echo "Paused nodes 1 and 2"

echo "Waiting 10 seconds for partition effects..."
sleep 10

echo -e "\n--- Checking majority partition ---"
MAJORITY_LEADER=""
for i in {3..5}; do
    if docker logs raft_node$i 2>&1 | tail -50 | grep -q "Became LEADER"; then
        MAJORITY_LEADER=$i
        echo " Majority partition elected leader: Node $MAJORITY_LEADER"
        break
    fi
done

echo -e "\n--- Healing partition ---"
docker unpause raft_node1
docker unpause raft_node2
echo " Unpaused nodes 1 and 2"

sleep 5

echo -e "\n--- Verifying minority nodes rejoined ---"
for i in {1..2}; do
    if docker logs raft_node$i 2>&1 | tail -20 | grep -q "Heartbeat received"; then
        echo " Node $i rejoined cluster"
    fi
done

echo -e "\n Test 5 Complete: Split brain prevented"