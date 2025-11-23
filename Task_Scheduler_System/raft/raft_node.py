import grpc
import os
import time
import socket
import threading
from concurrent import futures

import raft_pb2
import raft_pb2_grpc
from election import ElectionManager
from log_replication import LogReplicationManager


class RaftService(raft_pb2_grpc.RaftServicer):
    #gRPC Service Implementation for Raft RPCs

    def __init__(self, election_mgr, log_replicator):
        self.election_mgr = election_mgr
        self.log_replicator = log_replicator

    def RequestVote(self, request, context):
        return self.election_mgr.handle_vote_request(request)

    def AppendEntries(self, request, context):
        if len(request.entries) == 0:
            return self.election_mgr.handle_heartbeat(request) # Heartbeat
        else:
            return self.log_replicator.handle_append_entries(request) # Log replication


class RaftClientService(raft_pb2_grpc.RaftClientServicer):
    #gRPC Service for client operations
    
    def __init__(self, node_id, election_mgr, log_replicator, all_nodes):
        self.node_id = node_id
        self.election_mgr = election_mgr
        self.log_replicator = log_replicator
        self.all_nodes = all_nodes
    
    def SubmitOperation(self, request, context):
        #Handle client operation submission
        print(f"\n Node {self.node_id}: Received client request")
        print(f"   Operation: {request.operation}")
        print(f"   Client ID: {request.client_id}")
        
        #if not leader, forward to leader
        if self.election_mgr.role != "leader":
            leader_id = self._find_leader()
            
            if leader_id and leader_id != self.node_id:
                print(f" Node {self.node_id}: Not leader, forwarding to {leader_id}")
                return self._forward_to_leader(request, leader_id)
            else:
                return raft_pb2.ClientResponse(
                    success=False,
                    message="No leader currently available",
                    leader_id=""
                )
        
        # Process as leader
        print(f" Node {self.node_id}: Processing as leader")
        success, message, leader = self.log_replicator.append_entry(
            request.operation,
            request.client_id
        )
        
        return raft_pb2.ClientResponse(
            success=success,
            message=message,
            leader_id=leader
        )
    
    def _find_leader(self):
        """Try to find current leader"""
        if self.election_mgr.voted_for and self.election_mgr.voted_for != self.node_id:
            return self.election_mgr.voted_for
        
        for peer in self.all_nodes:
            peer_id = peer.split(":")[0].replace("raft_", "")
            if peer_id == self.node_id:
                continue
            
            try:
                host, port = peer.split(":")
                client_port = str(int(port) + 90)  # Client port offset
                with grpc.insecure_channel(f"{host}:{client_port}") as channel:
                    stub = raft_pb2_grpc.RaftClientStub(channel)
                    response = stub.SubmitOperation(
                        raft_pb2.ClientRequest(operation="ping", client_id="test"),
                        timeout=1
                    )
                    if response.leader_id:
                        return response.leader_id
            except:
                continue
        
        return None
    
    def _forward_to_leader(self, request, leader_id):
        """Forward client request to leader"""
        for peer in self.all_nodes:
            if leader_id in peer:
                try:
                    host, port = peer.split(":")
                    client_port = str(int(port) + 90)
                    with grpc.insecure_channel(f"{host}:{client_port}") as channel:
                        stub = raft_pb2_grpc.RaftClientStub(channel)
                        return stub.SubmitOperation(request, timeout=5)
                except Exception as e:
                    print(f" Failed to forward to leader: {e}")
        
        return raft_pb2.ClientResponse(
            success=False,
            message=f"Failed to contact leader {leader_id}",
            leader_id=leader_id
        )


def serve():
    """Start a single Raft node instance."""
    node_id = os.environ.get("NODE_ID", socket.gethostname())
    port = os.environ.get("PORT", "50051")
    client_port = os.environ.get("CLIENT_PORT", "50151")
    
    all_nodes_str = os.environ.get("ALL_NODE_IDS", "")
    all_nodes = [n.strip() for n in all_nodes_str.split(",") if n.strip()]

    print(f" Node {node_id}: Initializing...")
    print(f"   Raft Port: {port}")
    print(f"   Client Port: {client_port}")
    print(f"   Peers: {all_nodes}")

    # Initialize managers
    election_mgr = ElectionManager(node_id=node_id, all_nodes=all_nodes, port=port)
    log_replicator = LogReplicationManager(node_id, all_nodes, election_mgr)

    # Start gRPC servers
    raft_server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    raft_pb2_grpc.add_RaftServicer_to_server(
        RaftService(election_mgr, log_replicator),
        raft_server
    )
    raft_server.add_insecure_port(f"[::]:{port}")
    raft_server.start()
    
    client_server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    raft_pb2_grpc.add_RaftClientServicer_to_server(
        RaftClientService(node_id, election_mgr, log_replicator, all_nodes),
        client_server
    )
    client_server.add_insecure_port(f"[::]:{client_port}")
    client_server.start()

    print(f" Node {node_id}: Raft node started")

    # Background threads
    election_thread = threading.Thread(target=election_mgr.start_election_loop, daemon=True)
    election_thread.start()

    replication_thread = threading.Thread(target=log_replicator.replicate_to_followers, daemon=True)
    replication_thread.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print(f" Node {node_id}: Shutting down...")
        election_mgr.stop()
        raft_server.stop(0)
        client_server.stop(0)


if __name__ == "__main__":
    serve()