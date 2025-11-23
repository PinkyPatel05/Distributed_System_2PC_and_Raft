import grpc
import threading
import time
import random
import raft_pb2
import raft_pb2_grpc


def safe_grpc_call(stub_function, request, node_id, target_id, rpc_name, retries=3, delay=1):
    """Safely call gRPC with retries and proper logging"""
    for i in range(retries):
        try:
            # Client-side logging 
            print(f"Node {node_id} sends RPC {rpc_name} to Node {target_id}")
            return stub_function(request, timeout=2)
        except grpc.RpcError as e:
            if i < retries - 1:
                time.sleep(delay)
            else:
                pass  # Silent failure after retries
    return None


class ElectionManager:
    def __init__(self, node_id, all_nodes, port):
        self.node_id = node_id
        self.all_nodes = all_nodes
        self.port = port
        self.current_term = 0
        self.voted_for = None
        self.votes_received = 0
        self.running = True
        self.role = "follower"
        self.vote_lock = threading.Lock()
        self.election_timer = None
        self.last_heartbeat = time.time()
    
    def start_election_loop(self):
        """Main loop to keep node alive and trigger elections."""
        print(f" Node {self.node_id}: Election loop started (role: {self.role})")
        self.reset_election_timer()
        
        while self.running:
            time.sleep(0.1)
    
    def reset_election_timer(self):
        """Resets randomized election timeout (1.5-3 seconds as required)"""
        if hasattr(self, "election_timer") and self.election_timer:
            self.election_timer.cancel()
        
        # Q3 Requirement: Election timeout = [1.5, 3] seconds
        timeout = random.uniform(1.5, 3)
        self.election_timer = threading.Timer(timeout, self.start_election)
        self.election_timer.start()
    
    def handle_vote_request(self, request):
        """Handles RequestVote RPC calls."""
        # Server-side logging (as required)
        print(f"Node {self.node_id} runs RPC RequestVote called by Node {request.candidate_id}")
        
        with self.vote_lock:
            response = raft_pb2.VoteResponse(term=self.current_term, vote_granted=False)
            
            if request.term > self.current_term:
                self.current_term = request.term
                self.voted_for = None
                self.role = "follower"
            
            if request.term >= self.current_term and (self.voted_for is None or self.voted_for == request.candidate_id):
                self.voted_for = request.candidate_id
                response.vote_granted = True
                response.term = self.current_term
                print(f" Node {self.node_id}: Voted for {request.candidate_id} in term {self.current_term}")
                self.reset_election_timer()
            
            return response
    
    def handle_heartbeat(self, request):
        """Handles leader heartbeat RPCs."""
        # Server-side logging
        print(f"Node {self.node_id} runs RPC AppendEntries called by Node {request.leader_id}")
        
        if request.term >= self.current_term:
            self.current_term = request.term
            self.role = "follower"
            self.voted_for = None
            self.last_heartbeat = time.time()
            self.reset_election_timer()
            print(f"Node {self.node_id}: Heartbeat received from leader {request.leader_id}")
            return raft_pb2.AppendEntriesResponse(term=self.current_term, success=True, match_index=0)
        
        return raft_pb2.AppendEntriesResponse(term=self.current_term, success=False, match_index=0)
    
    def start_election(self):
        """Starts a new election round."""
        if self.role == "leader":
            return

        with self.vote_lock:
            self.current_term += 1
            self.voted_for = self.node_id
            self.role = "candidate"
            self.votes_received = 1

        print(f"\nNode {self.node_id}: Starting election for term {self.current_term}")

        for peer in self.all_nodes:
            if peer == f"raft_{self.node_id}:{self.port}":
                continue

            host, port = peer.split(":")
            target_id = host.replace("raft_", "")

            try:
                with grpc.insecure_channel(f"{host}:{port}") as channel:
                    stub = raft_pb2_grpc.RaftStub(channel)
                    request = raft_pb2.VoteRequest(
                        term=self.current_term,
                        candidate_id=self.node_id
                    )

                    response = safe_grpc_call(
                        stub.RequestVote,
                        request,
                        self.node_id,
                        target_id,
                        "RequestVote"
                    )

                    if response and response.vote_granted:
                        self.votes_received += 1
            except:
                pass

        majority = (len(self.all_nodes) // 2) + 1
        if self.votes_received >= majority:
            self.role = "leader"
            print(f"Node {self.node_id}: Became LEADER in term {self.current_term} with {self.votes_received}/{len(self.all_nodes)} votes")
            self.send_heartbeats()
        else:
            self.role = "follower"
            self.reset_election_timer()
    
    def send_heartbeats(self):
        """Continuously sends heartbeats when leader."""
        def heartbeat_loop():
            while self.role == "leader" and self.running:
                for peer in self.all_nodes:
                    if peer == f"raft_{self.node_id}:{self.port}":
                        continue
                    
                    host, port = peer.split(":")
                    target_id = host.replace("raft_", "")
                    
                    try:
                        with grpc.insecure_channel(f"{host}:{port}") as channel:
                            stub = raft_pb2_grpc.RaftStub(channel)
                            request = raft_pb2.AppendEntriesRequest(
                                term=self.current_term,
                                leader_id=self.node_id,
                                entries=[],
                                prev_log_index=0,
                                prev_log_term=0,
                                leader_commit=0
                            )
                            
                            safe_grpc_call(
                                stub.AppendEntries,
                                request,
                                self.node_id,
                                target_id,
                                "AppendEntries"
                            )
                    except:
                        pass
                
                # Q3 Requirement: Heartbeat timeout = 1 second
                time.sleep(1)
        
        threading.Thread(target=heartbeat_loop, daemon=True).start()
    
    def stop(self):
        """Stop election loop."""
        self.running = False
        if hasattr(self, "election_timer") and self.election_timer:
            self.election_timer.cancel()