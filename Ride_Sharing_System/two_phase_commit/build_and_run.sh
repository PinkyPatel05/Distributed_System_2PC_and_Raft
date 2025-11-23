
# echo "=========================================="
# echo "Two-Phase Commit - Complete Implementation"
# echo "Assignment 3 - Q2: Voting + Decision Phases"
# echo "=========================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Step 1: Generate Python code from proto file
echo ""
echo "[1/6] Generating gRPC code from proto file..."
python -m grpc_tools.protoc \
    -I. \
    --python_out=. \
    --grpc_python_out=. \
    two_phase_commit.proto

if [ $? -eq 0 ]; then
    echo -e "${GREEN} Proto code generated successfully${NC}"
else
    echo -e "${RED} Failed to generate proto code${NC}"
    exit 1
fi

# Verify generated files exist
if [ ! -f "two_phase_commit_pb2.py" ] || [ ! -f "two_phase_commit_pb2_grpc.py" ]; then
    echo -e "${RED} Generated proto files not found${NC}"
    exit 1
fi

# Step 2: Stop and remove existing containers
echo ""
echo "[2/6] Cleaning up existing containers..."
docker-compose down -v 2>/dev/null
docker system prune -f >/dev/null 2>&1

# Step 3: Build Docker images
echo ""
echo "[3/6] Building Docker images..."
echo "This may take a few minutes..."
docker-compose build --no-cache

if [ $? -eq 0 ]; then
    echo -e "${GREEN} Docker images built successfully${NC}"
else
    echo -e "${RED} Failed to build Docker images${NC}"
    exit 1
fi

# Step 4: Start containers
echo ""
echo "[4/6] Starting Docker containers..."
docker-compose up -d

if [ $? -eq 0 ]; then
    echo -e "${GREEN} Containers started successfully${NC}"
else
    echo -e "${RED} Failed to start containers${NC}"
    exit 1
fi

# Step 5: Wait for services to be ready
echo ""
echo "[5/6] Waiting for services to be ready..."
echo "Coordinator and 5 participants starting up..."

for i in {1..15}; do
    echo -n "."
    sleep 1
done
echo ""

# Step 6: Verify all containers are running
echo ""
echo "[6/6] Verifying container status..."

# Count running containers
RUNNING=$(docker-compose ps | grep "Up" | wc -l)

if [ $RUNNING -eq 6 ]; then
    echo -e "${GREEN} All 6 containers are running${NC}"
else
    echo -e "${YELLOW}  Expected 6 containers, found $RUNNING running${NC}"
fi

# Show running containers
echo ""
echo "Running Containers:"
docker-compose ps

# Check if coordinator is accessible
echo ""
echo "Checking coordinator accessibility..."
timeout 2 bash -c "echo > /dev/tcp/localhost/50050" 2>/dev/null
if [ $? -eq 0 ]; then
    echo -e "${GREEN} Coordinator is accessible on port 50050${NC}"
else
    echo -e "${YELLOW} Coordinator may not be ready yet${NC}"
fi

# Check participant voting phases
echo ""
echo "Checking participant voting phases..."
for port in 50051 50052 50053 50054 50055; do
    timeout 1 bash -c "echo > /dev/tcp/localhost/$port" 2>/dev/null
    if [ $? -eq 0 ]; then
        echo -e "${GREEN} Participant voting phase accessible on port $port${NC}"
    else
        echo -e "${YELLOW}  Port $port may not be ready yet${NC}"
    fi
done

echo ""
echo "====================="
echo "System is ready!"
echo "====================="
echo ""
echo "System Overview:"
echo "  • 1 Coordinator (port 50050)"
echo "  • 5 Participants with dual phases:"
echo "    - Voting phases (ports 50051-50055)"
echo "    - Decision phases (ports 60051-60055)"
echo ""
echo " Useful Commands:"
echo ""
echo "View all logs:"
echo "  docker-compose logs -f"
echo ""
echo "View coordinator logs:"
echo "  docker-compose logs -f coordinator"
echo ""
echo "View specific participant:"
echo "  docker-compose logs -f participant1"
echo ""
echo "Filter for RPC messages:"
echo "  docker-compose logs | grep 'sends RPC\\|receives RPC'"
echo ""
echo "View only voting phase logs:"
echo "  docker-compose logs | grep 'VOTING'"
echo ""
echo "View only decision phase logs:"
echo "  docker-compose logs | grep 'DECISION'"
echo ""
echo " Run Tests:"
echo ""
echo "Interactive menu:"
echo "  python test_client.py menu"
echo ""
echo "Single transaction:"
echo "  python test_client.py single"
echo ""
echo "Multiple transactions:"
echo "  python test_client.py multiple 10"
echo ""
echo "To stop all services:"
echo "  docker-compose down"
echo ""
echo "To rebuild after code changes:"
echo "  ./build_and_run.sh"
echo ""