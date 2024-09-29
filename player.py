import socket
import random
import threading
import time

# Global variables
t_socket = None
p_socket = None
t_port = None
p_port = None
ip_address = None
player_name = None  # To store the player's name globally

# Function to find an available port in the specified range
def find_available_port(start_port=32002, end_port=32499):
    while True:
        port = random.randint(start_port, end_port)
        try:
            test_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            test_socket.bind(('', port))
            test_socket.close()
            return port
        except OSError:
            continue

# Function to create t-socket and p-socket
def create_sockets():
    global t_socket, p_socket, t_port, p_port, ip_address
    hostname = socket.gethostname()
    ip_address = socket.gethostbyname(hostname)
    
    t_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    t_port = find_available_port()
    t_socket.bind((ip_address, t_port))
    
    p_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    p_port = find_available_port()
    p_socket.bind((ip_address, p_port))

# Function to handle server messages in a separate thread
def listen_for_server_commands():
    global player_name
    while True:
        try:
            response, _ = t_socket.recvfrom(1024)
            print("Server response:", response.decode())
            # You can add additional handling based on specific commands from the server
        except Exception as e:
            print("Error receiving message:", e)

# Function to handle registration
def register():
    global player_name

    while True:
        player_name = input("Please enter your name (max 15 characters): ")
        if len(player_name) <= 15:
            break
        else:
            print("Error: Name is too long. Please try again.")

    message = f"register <{player_name}> <{ip_address}> <{t_port}> <{p_port}>"
    t_socket.sendto(message.encode(), (ip_address, 32001))
    
    print("Waiting for a response from the server...")
    while True:
        response, _ = t_socket.recvfrom(1024)
        print("Server response:", response.decode())
        break

    startpage()

# Function for the start page
def startpage():
    while True:
        print("\nWhat would you like to do today? Enter 1-5")
        print("1. Start a game of 6 card golf.")
        print("2. Join a game of 6 card golf.")
        print("3. See active players.")
        print("4. See active Games.")
        print("5. Exit")

        choice = input("Enter your choice: ")

        if choice == '1':
            start_game()
        elif choice == '2':
            print("Joining a game of 6 card golf...")
            # To be implemented
            break
        elif choice == '3':
            print("Querying active players...")
            # To be implemented
            break
        elif choice == '4':
            print("Querying active games...")
            # To be implemented
            break
        elif choice == '5':
            print("Exiting the game. Goodbye!")
            break
        else:
            print("Invalid choice. Please select a valid option.")

# Function to start a game
def start_game():
    global player_name

    # Start the listener thread for server messages
    listener_thread = threading.Thread(target=listen_for_server_commands)
    listener_thread.daemon = True  # This will ensure the thread exits when the main program does
    listener_thread.start()

    while True:
        try:
            # Input for the number of players
            n = int(input("Enter number of players (2-4): "))
            if 2 <= n <= 4:
                break
            else:
                print("Invalid number of players. Please enter a number between 2 and 4.")
        except ValueError:
            print("Invalid input. Please enter a valid number.")

    while True:
        try:
            # Input for the number of rounds
            holes_input = input("Enter number of rounds (1-9) or press Enter for default (-1): ")
            if holes_input == '':
                holes = -1  # Default value if no input
                break
            holes = int(holes_input)
            if 1 <= holes <= 9:
                break
            elif holes == -1:
                break
            else:
                print("Invalid number of holes. Please enter a number between 1 and 9 or leave blank for -1.")
        except ValueError:
            print("Invalid input. Please enter a valid number.")

    # Send the start game message to the server
    message = f"start game <{player_name}> <{n}> <{holes}>"
    t_socket.sendto(message.encode(), (ip_address, 32001))
    print("Waiting for players to join the game...")

    # Infinite listening loop for server commands
    while True:
        time.sleep(1)  # Prevents busy waiting
        # You can add logic to break this loop based on server responses or commands

# Welcome function to start the program
def welcome():
    print("Welcome!")
    print("BEFORE PLAYING PLEASE ESTABLISH CONNECTION.")
    print("-X-")
    register()

# Main function to start player.py
if __name__ == "__main__":
    create_sockets()
    welcome()
