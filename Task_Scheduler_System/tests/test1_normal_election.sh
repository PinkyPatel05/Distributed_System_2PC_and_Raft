#!/bin/bash

echo "======================================"
echo "TEST 1: Normal Leader Election"
echo "======================================"

docker-compose -f docker-compose.raft.yml up -d

echo "Waiting 10 seconds for election..."
sleep 10

echo -e "\n--- Checking for leader ---"
for i in {1..5}; do
    if docker logs raft_node$i 2>&1 | grep -q "Became LEADER"; then
        echo " Node $i is the LEADER"
    else
        echo "   Node $i is a follower"
    fi
done

echo -e "\n Test 1 Complete"