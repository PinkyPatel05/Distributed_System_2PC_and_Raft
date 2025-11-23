#!/bin/bash

echo "======================================"
echo "TEST 2: Leader Failure & Re-election"
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

if [ -z "$LEADER" ]; then
    echo " No leader found!"
    exit 1
fi

echo -e "\n--- Stopping leader (Node $LEADER) ---"
docker stop raft_node$LEADER

echo "Waiting 10 seconds for re-election..."
sleep 10

echo -e "\n--- Checking for new leader ---"
NEW_LEADER=""
for i in {1..5}; do
    if [ $i -eq $LEADER ]; then
        continue
    fi
    
    if docker logs raft_node$i 2>&1 | tail -50 | grep -q "Became LEADER"; then
        NEW_LEADER=$i
        echo " New leader elected: Node $NEW_LEADER"
        break
    fi
done

if [ -z "$NEW_LEADER" ]; then
    echo " No new leader elected!"
else
    echo " Test 2 Complete: Leader failover successful"
fi
