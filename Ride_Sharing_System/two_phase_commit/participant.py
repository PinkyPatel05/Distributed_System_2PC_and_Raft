import grpc
from concurrent import futures
import time
import logging
import random
import os
from typing import Dict
import two_phase_commit_pb2 as pb2
import two_phase_commit_pb2_grpc as pb2_grpc

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)


class VotingPhase(pb2_grpc.ParticipantVotingPhaseServicer):
    # Handles the voting phase of 2PC for a participant & Communicates with coordinator and with local decision phase
    
    def __init__(self, participant_id: str, service_name: str, decision_phase_port: int):
        self.participant_id = participant_id
        self.service_name = service_name
        self.decision_phase_port = decision_phase_port
        self.node_id = participant_id
        
        logger.info(f"[{self.node_id}] Voting Phase initialized for {service_name}")
    
    def VoteRequest(self, request, context):
        # Handle vote-request from coordinator & return VOTE_COMMIT or VOTE_ABORT
        transaction_id = request.transaction_id
        operation_type = request.operation_type
        
        # Log RPC received
        logger.info(f"Phase VOTING of Node {self.node_id} receives RPC VoteRequest "
                   f"from Phase VOTING of Node COORDINATOR")
        
        logger.info(f"\n[{self.node_id} - VOTING] Processing transaction {transaction_id[:8]}...")
        logger.info(f"[{self.node_id} - VOTING] Operation: {operation_type}")
        
        # Validate if this participant can perform the operation
        can_commit, reason = self._can_commit(operation_type, dict(request.parameters))
        
        if can_commit:
            vote_decision = pb2.VOTE_COMMIT
            decision_str = "VOTE_COMMIT"
            logger.info(f"[{self.node_id} - VOTING] Decision: VOTE_COMMIT - {reason}")
        else:
            vote_decision = pb2.VOTE_ABORT
            decision_str = "VOTE_ABORT"
            logger.info(f"[{self.node_id} - VOTING] Decision: VOTE_ABORT - {reason}")
        
        # Notify local decision phase about the vote via gRPC
        self._notify_decision_phase(transaction_id, vote_decision, operation_type, 
                                    dict(request.parameters))
        
        # Return vote to coordinator
        response = pb2.VoteResponseMessage(
            transaction_id=transaction_id,
            participant_id=self.participant_id,
            decision=vote_decision,
            reason=reason
        )
        
        logger.info(f"Phase VOTING of Node {self.node_id} sends {decision_str} "
                   f"to Phase VOTING of Node COORDINATOR")
        
        return response
    
    def _notify_decision_phase(self, transaction_id: str, vote: int, 
                               operation_type: str, parameters: Dict[str, str]):
        # Notify the local decision phase about this node's vote via gRPC
        try:
            # Connect to local decision phase
            channel = grpc.insecure_channel(f'localhost:{self.decision_phase_port}')
            stub = pb2_grpc.IntraNodeDecisionPhaseStub(channel)
            
            vote_str = "VOTE_COMMIT" if vote == pb2.VOTE_COMMIT else "VOTE_ABORT"
            
            # Log intra-node RPC
            logger.info(f"Phase VOTING of Node {self.node_id} sends RPC NotifyVote "
                       f"to Phase DECISION of Node {self.node_id}")
            
            notification = pb2.VoteNotification(
                transaction_id=transaction_id,
                vote=vote,
                operation_type=operation_type,
                parameters=parameters
            )
            
            ack = stub.NotifyVote(notification, timeout=2.0)
            
            logger.info(f"Phase DECISION of Node {self.node_id} acknowledges NotifyVote "
                       f"from Phase VOTING of Node {self.node_id}")
            
            channel.close()
            
        except Exception as e:
            logger.error(f"[{self.node_id} - VOTING] Failed to notify decision phase: {e}")
    
    def _can_commit(self, operation_type: str, parameters: Dict[str, str]) -> tuple:
        # Business logic to determine if participant can commit & Simulate different validation logic for different services
        
        if self.service_name == "DriverService":
            driver_id = parameters.get('driver_id', '')
            if not driver_id:
                return False, "No driver ID provided"
            
            # Simulate driver availability (85% available)
            if random.random() < 0.85:
                return True, "Driver available"
            return False, "Driver not available"
        
        elif self.service_name == "PaymentService":
            amount = parameters.get('amount', '0')
            try:
                if float(amount) <= 0:
                    return False, "Invalid amount"
                # Simulate payment validation (90% success)
                if random.random() < 0.90:
                    return True, "Payment authorized"
                return False, "Insufficient funds"
            except ValueError:
                return False, "Invalid amount format"
        
        elif self.service_name == "BookingService":
            rider_id = parameters.get('rider_id', '')
            if not rider_id:
                return False, "No rider ID provided"
            
            # Simulate booking validation (95% success)
            if random.random() < 0.95:
                return True, "Booking slot available"
            return False, "Booking conflict"
        
        elif self.service_name == "NotificationService":
            if random.random() < 0.98:
                return True, "Notification ready"
            return False, "Notification service unavailable"
        
        elif self.service_name == "AnalyticsService":
            if random.random() < 0.99:
                return True, "Analytics ready"
            return False, "Analytics database unavailable"
        
        else:
            return True, "Ready to commit"


class DecisionPhase(pb2_grpc.ParticipantDecisionPhaseServicer, 
                   pb2_grpc.IntraNodeDecisionPhaseServicer):
    # Handles the decision phase of 2PC for a participant & Receives final decision from coordinator and executes commit/abort
    
    def __init__(self, participant_id: str, service_name: str):
        self.participant_id = participant_id
        self.service_name = service_name
        self.node_id = participant_id
        self.prepared_transactions = {}  # Transactions waiting for decision
        
        logger.info(f"[{self.node_id}] Decision Phase initialized for {service_name}")
    
    def NotifyVote(self, request, context):
        # Receive vote notification from local voting phase (intra-node communication)

        transaction_id = request.transaction_id
        vote = request.vote
        
        vote_str = "VOTE_COMMIT" if vote == pb2.VOTE_COMMIT else "VOTE_ABORT"
        
        logger.info(f"Phase DECISION of Node {self.node_id} receives RPC NotifyVote "
                   f"from Phase VOTING of Node {self.node_id}")
        
        if vote == pb2.VOTE_COMMIT:
            # Store transaction in PREPARED state
            self.prepared_transactions[transaction_id] = {
                'operation': request.operation_type,
                'parameters': dict(request.parameters),
                'timestamp': int(time.time()),
                'status': 'PREPARED',
                'vote': vote_str
            }
            logger.info(f"[{self.node_id} - DECISION] Transaction {transaction_id[:8]}... "
                       f"in PREPARED state, waiting for coordinator decision")
        else:
            # Vote was ABORT, no need to prepare
            logger.info(f"[{self.node_id} - DECISION] Transaction {transaction_id[:8]}... "
                       f"voted ABORT, no preparation needed")
        
        return pb2.VoteAck(
            transaction_id=transaction_id,
            acknowledged=True
        )
    
    def GlobalDecision(self, request, context):
        # Receive final decision from coordinator & Execute commit or abort based on coordinator's decision
        transaction_id = request.transaction_id
        decision = request.decision
        
        decision_str = "GLOBAL_COMMIT" if decision == pb2.GLOBAL_COMMIT else "GLOBAL_ABORT"
        
        # Log RPC received
        logger.info(f"Phase DECISION of Node {self.node_id} receives RPC GlobalDecision "
                   f"from Phase DECISION of Node COORDINATOR")
        
        logger.info(f"\n[{self.node_id} - DECISION] Received {decision_str} for transaction "
                   f"{transaction_id[:8]}...")
        
        if decision == pb2.GLOBAL_COMMIT:
            # Execute commit
            status = self._do_commit(transaction_id)
            logger.info(f"[{self.node_id} - DECISION] ✅ Transaction COMMITTED locally")
        else:
            # Execute abort
            status = self._do_abort(transaction_id)
            logger.info(f"[{self.node_id} - DECISION] ❌ Transaction ABORTED locally")
        
        # Clean up prepared state
        if transaction_id in self.prepared_transactions:
            del self.prepared_transactions[transaction_id]
        
        # Send acknowledgment back to coordinator
        ack = pb2.DecisionAck(
            transaction_id=transaction_id,
            participant_id=self.participant_id,
            acknowledged=True,
            status=status
        )
        
        logger.info(f"Phase DECISION of Node {self.node_id} sends acknowledgment "
                   f"to Phase DECISION of Node COORDINATOR")
        
        return ack
    
    def _do_commit(self, transaction_id: str) -> str:
        # Actually perform the commit operation
        if transaction_id in self.prepared_transactions:
            txn = self.prepared_transactions[transaction_id]
            operation = txn['operation']
            
            logger.info(f"[{self.node_id} - DECISION] Executing commit for {operation}")
            
            # Simulate actual database/state changes
            if self.service_name == "DriverService":
                driver_id = txn['parameters'].get('driver_id', 'unknown')
                logger.info(f"[{self.node_id} - DECISION] Assigning driver {driver_id} to ride")
                # Update driver status in database
                
            elif self.service_name == "PaymentService":
                amount = txn['parameters'].get('amount', '0')
                rider_id = txn['parameters'].get('rider_id', 'unknown')
                logger.info(f"[{self.node_id} - DECISION] Charging ${amount} to rider {rider_id}")
                # Process payment transaction
                
            elif self.service_name == "BookingService":
                logger.info(f"[{self.node_id} - DECISION] Creating booking record")
                # Insert booking into database
                
            elif self.service_name == "NotificationService":
                logger.info(f"[{self.node_id} - DECISION] Sending ride confirmation notification")
                # Send notification to rider and driver
                
            elif self.service_name == "AnalyticsService":
                logger.info(f"[{self.node_id} - DECISION] Recording ride metrics")
                # Update analytics data
            
            return "COMMITTED"
        
        return "COMMITTED"
    
    def _do_abort(self, transaction_id: str) -> str:
        # Rollback any prepared changes
        if transaction_id in self.prepared_transactions:
            txn = self.prepared_transactions[transaction_id]
            logger.info(f"[{self.node_id} - DECISION] Rolling back {txn['operation']}")
            
            # Release any reserved resources
            if self.service_name == "DriverService":
                logger.info(f"[{self.node_id} - DECISION] Releasing driver reservation")
            elif self.service_name == "PaymentService":
                logger.info(f"[{self.node_id} - DECISION] Canceling payment authorization")
            # etc.
        
        return "ABORTED"


def serve_voting_phase(port: int, participant_id: str, service_name: str, 
                      decision_phase_port: int):
    # Start the voting phase gRPC server
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=5))
    voting_phase = VotingPhase(participant_id, service_name, decision_phase_port)
    
    pb2_grpc.add_ParticipantVotingPhaseServicer_to_server(voting_phase, server)
    
    server.add_insecure_port(f'[::]:{port}')
    server.start()
    
    logger.info(f"[{participant_id}] Voting Phase server started on port {port}")
    return server


def serve_decision_phase(port: int, participant_id: str, service_name: str):
    
    # Start the decision phase gRPC server
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=5))
    decision_phase = DecisionPhase(participant_id, service_name)
    
    pb2_grpc.add_ParticipantDecisionPhaseServicer_to_server(decision_phase, server)
    pb2_grpc.add_IntraNodeDecisionPhaseServicer_to_server(decision_phase, server)
    
    server.add_insecure_port(f'[::]:{port}')
    server.start()
    
    logger.info(f"[{participant_id}] Decision Phase server started on port {port}")
    return server


if __name__ == '__main__':
    # Get configuration from environment variables
    voting_port = int(os.getenv('VOTING_PORT', '50051'))
    decision_port = int(os.getenv('DECISION_PORT', '60051'))
    participant_id = os.getenv('PARTICIPANT_ID', 'PARTICIPANT_1')
    service_name = os.getenv('SERVICE_NAME', 'GenericService')
    
    logger.info(f"\n{'='*70}")
    logger.info(f"[{participant_id}] Starting Two-Phase Commit Participant")
    logger.info(f"[{participant_id}] Service: {service_name}")
    logger.info(f"[{participant_id}] Voting Phase Port: {voting_port}")
    logger.info(f"[{participant_id}] Decision Phase Port: {decision_port}")
    logger.info(f"{'='*70}\n")
    
    # Start both phases
    voting_server = serve_voting_phase(voting_port, participant_id, service_name, decision_port)
    decision_server = serve_decision_phase(decision_port, participant_id, service_name)
    
    try:
        voting_server.wait_for_termination()
        decision_server.wait_for_termination()
    except KeyboardInterrupt:
        logger.info(f"[{participant_id}] Shutting down...")
        voting_server.stop(0)
        decision_server.stop(0)