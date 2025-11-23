import grpc
import time
import uuid
import two_phase_commit_pb2 as pb2
import two_phase_commit_pb2_grpc as pb2_grpc


def print_header(title):
    """Print a formatted header"""
    print("\n" + "="*52)
    print(f"  {title}")
    print("="*52)


def print_section(title):
    """Print a section divider"""
    print(f"\n--- {title} ---")


def test_ride_booking_transaction(show_details=True):
    # Test a complete 2PC transaction (voting + decision phases)
    # Connect to coordinator
    channel = grpc.insecure_channel('localhost:50050')
    stub = pb2_grpc.TwoPhaseCommitCoordinatorStub(channel)
    
    if show_details:
        print_header("TWO-PHASE COMMIT TEST - Ride Booking Transaction")
    
    # Create transaction request
    transaction_id = str(uuid.uuid4())
    
    transaction_request = pb2.TransactionRequest(
        transaction_id=transaction_id,
        operation_type="BOOK_RIDE",
        parameters={
            'rider_id': f'rider_{int(time.time()) % 1000}',
            'driver_id': f'driver_{int(time.time()) % 500}',
            'amount': f'{20 + (int(time.time()) % 50):.2f}',
            'pickup': 'Downtown Dallas',
            'destination': 'DFW Airport'
        }
    )
    
    if show_details:
        print_section("Transaction Details")
        print(f"Transaction ID: {transaction_id}")
        print(f"Operation: {transaction_request.operation_type}")
        print(f"Parameters:")
        for key, value in transaction_request.parameters.items():
            print(f"  • {key}: {value}")
    
    try:
        if show_details:
            print_section("Sending Transaction to Coordinator")
            print("Initiating 2PC protocol...")
        
        # Send transaction to coordinator (this triggers both phases)
        start_time = time.time()
        response = stub.InitiateTransaction(transaction_request, timeout=15.0)
        end_time = time.time()
        
        if show_details:
            print_section("Transaction Result")
            print(f"Transaction ID: {response.transaction_id[:8]}...")
            print(f"Success: {response.success}")
            print(f"Final Decision: {response.final_decision}")
            print(f"Message: {response.message}")
            print(f"Execution Time: {(end_time - start_time):.3f} seconds")
        
        if response.success:
            print(f"\n Transaction SUCCESSFUL - {response.final_decision}")
            result = "SUCCESS"
        else:
            print(f"\nTransaction FAILED - {response.final_decision}")
            print(f"  Reason: {response.message}")
            result = "FAILED"
            
    except grpc.RpcError as e:
        print(f"\nRPC Error: {e.code()} - {e.details()}")
        result = "ERROR"
    except Exception as e:
        print(f"\nError: {e}")
        result = "ERROR"
    finally:
        channel.close()
    
    if show_details:
        print("="*52 + "\n")
    
    return result


def test_multiple_transactions(count=5):

    # Test multiple transactions to observe both success and failure scenarios

    print_header(f"TESTING {count} TRANSACTIONS")
    
    results = {"SUCCESS": 0, "FAILED": 0, "ERROR": 0}
    
    for i in range(count):
        print(f"\nTransaction {i+1}/{count}")
        print('─'*50)
        
        result = test_ride_booking_transaction(show_details=False)
        results[result] += 1
        
        if i < count - 1:
            time.sleep(1)  # Brief pause between transactions
    
    # Summary
    print_header("TEST SUMMARY")
    print(f"Total Transactions: {count}")
    print(f" Successful (GLOBAL_COMMIT): {results['SUCCESS']}")
    print(f" Failed (GLOBAL_ABORT): {results['FAILED']}")
    print(f" Errors: {results['ERROR']}")
    print(f"\nSuccess Rate: {(results['SUCCESS']/count)*100:.1f}%")
    print("="*50 + "\n")


def test_participant_failure_scenario():
    # Test what happens when we simulate a participant failure
    print_header("TESTING PARTICIPANT FAILURE SCENARIO")
    print("Note: Some participants are configured to randomly fail votes")
    print("This simulates real-world scenarios like insufficient funds,")
    print("unavailable drivers, booking conflicts, etc.\n")
    
    # Run several transactions to see failures
    for i in range(3):
        print(f"\nAttempt {i+1}/3:")
        test_ride_booking_transaction(show_details=False)
        time.sleep(1)


def interactive_menu():
    """
    Interactive menu for testing
    """
    while True:
        print("\n" + "="*50)
        print("  TWO-PHASE COMMIT TEST MENU")
        print("="*50)
        print("1. Run single transaction (detailed)")
        print("2. Run multiple transactions (5)")
        print("3. Run multiple transactions (10)")
        print("4. Test failure scenarios")
        print("5. Stress test (20 transactions)")
        print("6. Exit")
        print("="*50)
        
        choice = input("\nEnter your choice (1-6): ").strip()
        
        if choice == '1':
            test_ride_booking_transaction(show_details=True)
        elif choice == '2':
            test_multiple_transactions(5)
        elif choice == '3':
            test_multiple_transactions(10)
        elif choice == '4':
            test_participant_failure_scenario()
        elif choice == '5':
            test_multiple_transactions(20)
        elif choice == '6':
            print("\nExiting... Goodbye!\n")
            break
        else:
            print("\nInvalid choice. Please enter 1-6.")
        
        input("\nPress Enter to continue...")


if __name__ == '__main__':
    import sys
    
    print("\nWaiting for services to be ready...")
    time.sleep(2)
    
    if len(sys.argv) > 1:
        # Command line arguments
        if sys.argv[1] == 'single':
            test_ride_booking_transaction(show_details=True)
        elif sys.argv[1] == 'multiple':
            count = int(sys.argv[2]) if len(sys.argv) > 2 else 5
            test_multiple_transactions(count)
        elif sys.argv[1] == 'menu':
            interactive_menu()
        else:
            print("Usage: python test_client.py [single|multiple|menu]")
    else:
        # Default: run interactive menu
        interactive_menu()