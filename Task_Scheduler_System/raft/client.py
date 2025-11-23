import grpc
import sys
import time
import raft_pb2
import raft_pb2_grpc


def submit_operation(node_address, operation, client_id="client1"):
    """Submit an operation to a Raft node"""
    try:
        with grpc.insecure_channel(node_address) as channel:
            stub = raft_pb2_grpc.RaftClientStub(channel)
            
            request = raft_pb2.ClientRequest(
                operation=operation,
                client_id=client_id
            )
            
            print(f"\n Submitting operation to {node_address}")
            print(f"   Operation: {operation}")
            
            response = stub.SubmitOperation(request, timeout=10)
            
            print(f" Response:")
            print(f"   Success: {response.success}")
            print(f"   Message: {response.message}")
            print(f"   Leader: {response.leader_id}")
            
            return response
    
    except grpc.RpcError as e:
        print(f" Error: {e}")
        return None


def main():
    # Default node addresses (client ports)
    nodes = [
        "localhost:50151",  # node1 (index 0)
        "localhost:50152",  # node2 (index 1)
        "localhost:50153",  # node3 (index 2)
        "localhost:50154",  # node4 (index 3)
        "localhost:50155",  # node5 (index 4)
    ]
    
    if len(sys.argv) > 1:
        # Use command line arguments
        operation = sys.argv[1]
        node_index = int(sys.argv[2]) if len(sys.argv) > 2 else 0
        
        # Validate node index
        if node_index < 0 or node_index >= len(nodes):
            print(f" Error: Node index must be between 0 and {len(nodes)-1}")
            print(f"   You provided: {node_index}")
            sys.exit(1)
        
        target_node = nodes[node_index]
    else:
        # Interactive mode
        print("\n" + "="*60)
        print("Raft Client - Operation Submission Tool")
        print("="*60)
        print("\nAvailable nodes:")
        for i, node in enumerate(nodes):
            print(f"  {i}: {node} (node{i+1})")
        
        # Get valid node selection
        while True:
            try:
                node_index = int(input(f"\nSelect node (0-{len(nodes)-1}): "))
                
                if node_index < 0 or node_index >= len(nodes):
                    print(f" Invalid selection. Please choose a number between 0 and {len(nodes)-1}")
                    continue
                
                target_node = nodes[node_index]
                break
            
            except ValueError:
                print(" Invalid input. Please enter a number.")
                continue
            except KeyboardInterrupt:
                print("\n\n Goodbye!")
                sys.exit(0)
        
        # Get operation
        try:
            operation = input("\nEnter operation (e.g., 'SET x=10'): ")
            if not operation.strip():
                print(" Operation cannot be empty")
                sys.exit(1)
        except KeyboardInterrupt:
            print("\n\n Goodbye!")
            sys.exit(0)
    
    # Submit operation
    print(f"\n Targeting: Node {node_index + 1} at {target_node}")
    submit_operation(target_node, operation)


if __name__ == "__main__":
    main()