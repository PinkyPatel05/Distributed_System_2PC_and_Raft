#!/bin/bash

echo "======================================"
echo "TEST 4: Request Forwarding"
echo "======================================"

docker-compose -f docker-compose.raft.yml up -d
sleep 10

echo -e "\n--- Identifying leader and follower ---"
LEADER=""
FOLLOWER=""
for i in {1..5}; do
    if docker logs raft_node$i 2>&1 | grep -q "Became LEADER"; then
        LEADER=$i
        echo " Leader: Node $LEADER"
    elif [ -z "$FOLLOWER" ]; then
        FOLLOWER=$i
        echo " Follower selected: Node $FOLLOWER"
    fi
done

if [ -z "$LEADER" ] || [ -z "$FOLLOWER" ]; then
    echo " Could not identify leader and follower!"
    exit 1
fi

FOLLOWER_PORT=$((50150 + $FOLLOWER))
echo -e "\n--- Submitting operation to FOLLOWER (Node $FOLLOWER, port $FOLLOWER_PORT) ---"

python3 raft/client.py "SET forwarded=true" $((FOLLOWER - 1)) 2>/dev/null

sleep 3

echo -e "\n--- Checking follower logs ---"
if docker logs raft_node$FOLLOWER 2>&1 | grep -q "forwarding to"; then
    echo " Follower correctly forwarded request to leader"
else
    echo "  Request may have been handled directly"
fi

echo -e "\n Test 4 Complete"