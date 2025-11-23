import grpc
import time
import threading
import raft_pb2
import raft_pb2_grpc


class LogReplicationManager:
    def __init__(self, node_id, peers, election_mgr):
        self.node_id = node_id
        self.peers = peers
        self.election_mgr = election_mgr
        
        self.log = [{"term": 0, "command": "INIT", "index": 0}]
        self.commit_index = 0
        self.last_applied = 0
        
        self.next_index = {}
        self.match_index = {}
        
        self.log_lock = threading.Lock()
        
        print(f" Node {self.node_id}: Log Replication Manager initialized")
    
    def append_entry(self, command, client_id):
        """Leader receives client request and appends to log."""
        if self.election_mgr.role != "leader":
            return False, "Not the leader", self.election_mgr.voted_for
        
        with self.log_lock:
            new_index = len(self.log)
            new_entry = {
                "term": self.election_mgr.current_term,
                "command": command,
                "index": new_index
            }
            self.log.append(new_entry)
            
            print(f"Node {self.node_id} (LEADER): Appended entry at index {new_index}: {command}")
        
        success = self._wait_for_majority_ack(new_index)
        
        if success:
            with self.log_lock:
                self.commit_index = new_index
            print(f"Node {self.node_id} (LEADER): Committed entry at index {new_index}")
            self._apply_committed_entries()
            return True, "Operation committed successfully", self.node_id
        else:
            return False, "Failed to replicate to majority", self.node_id
    
    def _wait_for_majority_ack(self, index, timeout=5):
        """Wait for majority of followers to acknowledge replication"""
        start_time = time.time()
        majority = (len(self.peers) // 2) + 1
        
        while time.time() - start_time < timeout:
            ack_count = 1
            
            for peer in self.peers:
                peer_id = peer.split(":")[0].replace("raft_", "")
                if peer_id == self.node_id:
                    continue
                
                if self.match_index.get(peer_id, 0) >= index:
                    ack_count += 1
            
            if ack_count >= majority:
                return True
            
            time.sleep(0.1)
        
        return False
    
    def _apply_committed_entries(self):
        """Apply committed entries to state machine"""
        with self.log_lock:
            while self.last_applied < self.commit_index:
                self.last_applied += 1
                entry = self.log[self.last_applied]
                print(f" Node {self.node_id}: Applying entry {self.last_applied}: {entry['command']}")
    
    def replicate_to_followers(self):
        """Leader continuously replicates log to followers"""
        def replication_loop():
            while True:
                if self.election_mgr.role == "leader":
                    for peer in self.peers:
                        peer_id = peer.split(":")[0].replace("raft_", "")
                        if peer_id == self.node_id:
                            continue
                        
                        self._send_append_entries(peer, peer_id)
                
                time.sleep(0.5)
        
        threading.Thread(target=replication_loop, daemon=True).start()
    
    def _send_append_entries(self, peer_address, peer_id):
        """Send AppendEntries RPC to a specific follower"""
        try:
            if peer_id not in self.next_index:
                self.next_index[peer_id] = len(self.log)
                self.match_index[peer_id] = 0
            
            next_idx = self.next_index[peer_id]
            
            with self.log_lock:
                entries_to_send = self.log[next_idx:]
                prev_log_index = next_idx - 1
                prev_log_term = self.log[prev_log_index]["term"] if prev_log_index >= 0 else 0
                
                log_entries = [
                    raft_pb2.LogEntry(
                        term=entry["term"],
                        command=entry["command"],
                        index=entry["index"]
                    )
                    for entry in entries_to_send
                ]
            
            host, port = peer_address.split(":")
            
            with grpc.insecure_channel(f"{host}:{port}") as channel:
                stub = raft_pb2_grpc.RaftStub(channel)
                
                request = raft_pb2.AppendEntriesRequest(
                    term=self.election_mgr.current_term,
                    leader_id=self.node_id,
                    entries=log_entries,
                    prev_log_index=prev_log_index,
                    prev_log_term=prev_log_term,
                    leader_commit=self.commit_index
                )
                
                if len(log_entries) > 0:
                    print(f"Node {self.node_id} sends RPC AppendEntries to Node {peer_id} (entries: {len(log_entries)})")
                
                response = stub.AppendEntries(request, timeout=2)
                
                if response.success:
                    self.match_index[peer_id] = prev_log_index + len(log_entries)
                    self.next_index[peer_id] = self.match_index[peer_id] + 1
                else:
                    self.next_index[peer_id] = max(1, self.next_index[peer_id] - 1)
        
        except:
            pass
    
    def handle_append_entries(self, request):
        """Follower handles AppendEntries RPC from leader"""
        if len(request.entries) > 0:
            print(f"Node {self.node_id} runs RPC AppendEntries called by Node {request.leader_id} (entries: {len(request.entries)})")
        
        with self.log_lock:
            if request.term < self.election_mgr.current_term:
                return raft_pb2.AppendEntriesResponse(
                    term=self.election_mgr.current_term,
                    success=False,
                    match_index=0
                )
            
            if request.prev_log_index > 0:
                if request.prev_log_index >= len(self.log):
                    return raft_pb2.AppendEntriesResponse(
                        term=self.election_mgr.current_term,
                        success=False,
                        match_index=len(self.log) - 1
                    )
                
                if self.log[request.prev_log_index]["term"] != request.prev_log_term:
                    return raft_pb2.AppendEntriesResponse(
                        term=self.election_mgr.current_term,
                        success=False,
                        match_index=request.prev_log_index - 1
                    )
            
            if len(request.entries) > 0:
                insert_index = request.prev_log_index + 1
                
                for i, entry in enumerate(request.entries):
                    log_index = insert_index + i
                    
                    entry_dict = {
                        "term": entry.term,
                        "command": entry.command,
                        "index": entry.index
                    }
                    
                    if log_index < len(self.log):
                        if self.log[log_index]["term"] != entry.term:
                            self.log[log_index] = entry_dict
                    else:
                        self.log.append(entry_dict)
                
                print(f" Node {self.node_id} (FOLLOWER): Replicated {len(request.entries)} entries from leader")
            
            if request.leader_commit > self.commit_index:
                old_commit = self.commit_index
                self.commit_index = min(request.leader_commit, len(self.log) - 1)
                
                if self.commit_index > old_commit:
                    print(f" Node {self.node_id} (FOLLOWER): Updated commit_index to {self.commit_index}")
            
            self._apply_committed_entries()
            
            return raft_pb2.AppendEntriesResponse(
                term=self.election_mgr.current_term,
                success=True,
                match_index=len(self.log) - 1
            )