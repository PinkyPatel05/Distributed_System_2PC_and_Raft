#!/bin/bash

echo "======================================"
echo "TEST 3: Log Replication"
echo "======================================"

docker-compose -f docker-compose.raft.yml up -d
sleep 10

echo -e "\n--- Finding leader ---"
LEADER_NUM=""
for i in {1..5}; do
    if docker logs raft_node$i 2>&1 | grep -q "Became LEADER"; then
        LEADER_NUM=$i
        LEADER_PORT=$((50150 + $i))
        echo " Leader found on port $LEADER_PORT (Node $i)"
        break
    fi
done

if [ -z "$LEADER_NUM" ]; then
    echo " No leader found!"
    exit 1
fi

echo -e "\n--- Submitting operations ---"
python3 raft/client.py "SET x=10" $((LEADER_NUM - 1)) 2>/dev/null &
sleep 2
python3 raft/client.py "SET y=20" $((LEADER_NUM - 1)) 2>/dev/null &
sleep 2
python3 raft/client.py "SET z=30" $((LEADER_NUM - 1)) 2>/dev/null &

wait

echo -e "\n--- Waiting for replication ---"
sleep 5

echo -e "\n--- Replication Summary ---"
for i in {1..5}; do
    COUNT=$(docker logs raft_node$i 2>&1 | grep -c "Applying entry")
    echo "Node $i: $COUNT entries applied"
done

echo -e "\n Test 3 Complete"