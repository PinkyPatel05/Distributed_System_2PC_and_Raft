#!/bin/bash

echo "=========================================="
echo "RAFT IMPLEMENTATION - COMPLETE TEST SUITE"
echo "=========================================="

echo -e "\n Cleaning up previous runs..."
docker-compose -f docker-compose.raft.yml down -v 2>/dev/null
sleep 2

TESTS=(
    "test1_normal_election.sh"
    "test2_leader_failure.sh"
    "test3_log_replication.sh"
    "test4_request_forwarding.sh"
    "test5_network_partition.sh"
)

PASSED=0
FAILED=0

for test in "${TESTS[@]}"; do
    echo -e "\n\n=========================================="
    echo "Running: $test"
    echo "=========================================="
    
    docker-compose -f docker-compose.raft.yml down -v > /dev/null 2>&1
    sleep 2
    
    if bash tests/$test; then
        echo " $test PASSED"
        ((PASSED++))
    else
        echo " $test FAILED"
        ((FAILED++))
    fi
    
    docker-compose -f docker-compose.raft.yml down -v > /dev/null 2>&1
    sleep 2
done

echo -e "\n\n=========================================="
echo "TEST SUITE SUMMARY"
echo "=========================================="
echo "Total Tests: ${#TESTS[@]}"
echo "Passed: $PASSED"
echo "Failed: $FAILED"

if [ $FAILED -eq 0 ]; then
    echo -e "\n All tests passed!"
    exit 0
else
    echo -e "\n  Some tests failed"
    exit 1
fi