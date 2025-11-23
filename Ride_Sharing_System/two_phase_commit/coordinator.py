import grpc
from concurrent import futures
import time
import uuid
import logging
from typing import List, Dict, Tuple
import two_phase_commit_pb2 as pb2
import two_phase_commit_pb2_grpc as pb2_grpc

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)


class TwoPhaseCommitCoordinator(pb2_grpc.TwoPhaseCommitCoordinatorServicer):
    def __init__(self, participant_addresses: List[str]):
        # Initialize coordinator with list of participant addresses(gRPC addresses)
        self.participant_addresses = participant_addresses
        self.transaction_log = {}
        self.node_id = "COORDINATOR"
        
    def InitiateTransaction(self, request, context):
        # Main entry point for starting a complete 2PC transaction

        transaction_id = request.transaction_id or str(uuid.uuid4())
        logger.info(f"\n{'='*70}")
        logger.info(f"[{self.node_id}] Starting 2PC Transaction: {transaction_id}")
        logger.info(f"[{self.node_id}] Operation: {request.operation_type}")
        logger.info(f"{'='*70}")
        
        # Log transaction start
        self.transaction_log[transaction_id] = {
            'status': 'INITIATED',
            'operation': request.operation_type,
            'timestamp': int(time.time())
        }
        
        # PHASE 1: VOTING PHASE
        logger.info(f"\n[{self.node_id}] ==== PHASE 1: VOTING ====")
        vote_result = self._voting_phase(transaction_id, request.operation_type, 
                                          dict(request.parameters))
        
        # PHASE 2: DECISION PHASE
        logger.info(f"\n[{self.node_id}] ==== PHASE 2: DECISION ====")
        if vote_result['success']:
            # All participants voted COMMIT
            final_decision = pb2.GLOBAL_COMMIT
            decision_str = "GLOBAL_COMMIT"
            logger.info(f"[{self.node_id}] Decision: GLOBAL_COMMIT (all participants ready)")
        else:
            # At least one participant voted ABORT
            final_decision = pb2.GLOBAL_ABORT
            decision_str = "GLOBAL_ABORT"
            logger.info(f"[{self.node_id}] Decision: GLOBAL_ABORT")
            logger.info(f"[{self.node_id}] Reason: {vote_result['reason']}")
        
        # Send decision to all participants
        decision_result = self._decision_phase(transaction_id, final_decision)
        
        # Update transaction log
        self.transaction_log[transaction_id]['status'] = decision_str
        self.transaction_log[transaction_id]['decision_time'] = int(time.time())
        
        logger.info(f"\n{'='*70}")
        logger.info(f"[{self.node_id}] Transaction {transaction_id[:8]}... COMPLETED")
        logger.info(f"[{self.node_id}] Final Status: {decision_str}")
        logger.info(f"{'='*70}\n")
        
        return pb2.TransactionResponse(
            transaction_id=transaction_id,
            success=(final_decision == pb2.GLOBAL_COMMIT),
            message=f"Transaction {decision_str}",
            timestamp=int(time.time()),
            final_decision=decision_str
        )
    
    def _voting_phase(self, transaction_id: str, operation_type: str, 
                     parameters: Dict[str, str]) -> Dict:
        # Phase 1: Send vote-request to all participants and collect responses
        vote_responses = []
        failed_participants = []
        
        # Send vote-request to all participants
        for i, participant_addr in enumerate(self.participant_addresses, 1):
            participant_id = f"PARTICIPANT_{i}"
            
            try:
                # Create gRPC channel to participant's voting phase
                channel = grpc.insecure_channel(participant_addr)
                stub = pb2_grpc.ParticipantVotingPhaseStub(channel)
                
                # Log RPC call
                logger.info(f"Phase VOTING of Node {self.node_id} sends RPC VoteRequest "
                          f"to Phase VOTING of Node {participant_id}")
                
                # Create vote request message
                vote_request = pb2.VoteRequestMessage(
                    transaction_id=transaction_id,
                    operation_type=operation_type,
                    parameters=parameters,
                    timestamp=int(time.time())
                )
                
                # Send request and wait for response
                response = stub.VoteRequest(vote_request, timeout=5.0)
                
                # Log response received
                decision_str = "VOTE_COMMIT" if response.decision == pb2.VOTE_COMMIT else "VOTE_ABORT"
                logger.info(f"Phase VOTING of Node {participant_id} responds with {decision_str} "
                          f"to Node {self.node_id}")
                
                vote_responses.append(response)
                
                # Check if participant voted to abort
                if response.decision == pb2.VOTE_ABORT:
                    failed_participants.append({
                        'participant': response.participant_id,
                        'reason': response.reason
                    })
                
                channel.close()
                
            except grpc.RpcError as e:
                logger.error(f"[{self.node_id}] Failed to contact {participant_id}: {e.code()}")
                failed_participants.append({
                    'participant': participant_id,
                    'reason': f"Network error: {e.code()}"
                })
            except Exception as e:
                logger.error(f"[{self.node_id}] Error with {participant_id}: {str(e)}")
                failed_participants.append({
                    'participant': participant_id,
                    'reason': f"Error: {str(e)}"
                })
        
        # Determine voting result
        logger.info(f"\n[{self.node_id}] Voting Summary:")
        logger.info(f"  Total Participants: {len(self.participant_addresses)}")
        logger.info(f"  Votes Received: {len(vote_responses)}")
        logger.info(f"  COMMIT Votes: {len(vote_responses) - len(failed_participants)}")
        logger.info(f"  ABORT Votes: {len(failed_participants)}")
        
        if len(failed_participants) > 0:
            reason = f"Failed participants: {[p['participant'] for p in failed_participants]}"
            return {'success': False, 'reason': reason, 'failed': failed_participants}
        
        return {'success': True, 'votes': vote_responses}
    
    def _decision_phase(self, transaction_id: str, decision: int) -> Dict:
        
        # Phase 2: Send global decision (COMMIT or ABORT) to all participants
        
        decision_str = "GLOBAL_COMMIT" if decision == pb2.GLOBAL_COMMIT else "GLOBAL_ABORT"
        logger.info(f"[{self.node_id}] Broadcasting {decision_str} to all participants")
        
        decision_message = pb2.GlobalDecisionMessage(
            transaction_id=transaction_id,
            decision=decision,
            timestamp=int(time.time())
        )
        
        acknowledgments = []
        
        # Send decision to all participants
        for i, participant_addr in enumerate(self.participant_addresses, 1):
            participant_id = f"PARTICIPANT_{i}"
            
            try:
                # Create gRPC channel to participant's decision phase
                channel = grpc.insecure_channel(participant_addr)
                stub = pb2_grpc.ParticipantDecisionPhaseStub(channel)
                
                # Log RPC call
                logger.info(f"Phase DECISION of Node {self.node_id} sends RPC GlobalDecision "
                          f"to Phase DECISION of Node {participant_id}")
                
                # Send decision
                ack = stub.GlobalDecision(decision_message, timeout=5.0)
                
                # Log acknowledgment
                logger.info(f"Phase DECISION of Node {participant_id} acknowledges {ack.status} "
                          f"to Node {self.node_id}")
                
                acknowledgments.append(ack)
                channel.close()
                
            except grpc.RpcError as e:
                logger.error(f"[{self.node_id}] Failed to send decision to {participant_id}: {e.code()}")
            except Exception as e:
                logger.error(f"[{self.node_id}] Error sending decision to {participant_id}: {str(e)}")
        
        logger.info(f"\n[{self.node_id}] Decision Phase Summary:")
        logger.info(f"  Acknowledgments Received: {len(acknowledgments)}/{len(self.participant_addresses)}")
        
        return {'acknowledgments': acknowledgments}


def serve(port: int = 50050, participant_addresses: List[str] = None):
    """
    Start the coordinator gRPC server
    """
    if participant_addresses is None:
        # Default participant addresses
        participant_addresses = [
            'participant1:50051',
            'participant2:50052',
            'participant3:50053',
            'participant4:50054',
            'participant5:50055'
        ]
    
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    coordinator = TwoPhaseCommitCoordinator(participant_addresses)
    
    pb2_grpc.add_TwoPhaseCommitCoordinatorServicer_to_server(coordinator, server)
    
    server.add_insecure_port(f'[::]:{port}')
    server.start()
    
    logger.info(f"\n{'='*70}")
    logger.info(f"[COORDINATOR] Two-Phase Commit Coordinator Started")
    logger.info(f"[COORDINATOR] Listening on port {port}")
    logger.info(f"[COORDINATOR] Managing {len(participant_addresses)} participants")
    logger.info(f"{'='*70}\n")
    
    try:
        server.wait_for_termination()
    except KeyboardInterrupt:
        logger.info("[COORDINATOR] Shutting down...")
        server.stop(0)


if __name__ == '__main__':
    import os
    port = int(os.getenv('COORDINATOR_PORT', '50050'))
    addresses_str = os.getenv('PARTICIPANT_ADDRESSES', 
                             'participant1:50051,participant2:50052,participant3:50053,'
                             'participant4:50054,participant5:50055')
    participant_addresses = addresses_str.split(',')
    serve(port, participant_addresses)