import socket
import random
import threading
import time
import sys

# Global variables
t_socket = None  # The transaction socket (for communication with the server)
p_socket = None  # The player socket (for in-game communication)
t_port = None  # Port for transaction socket
p_port = None  # Port for player socket
system_ip_address = None  # The system's IP address
destination_ip_address = None  # The server's IP address
player_name = None  # To store the player's name globally
in_game = False  # Flag to indicate if the player is currently in a game

# Function to find an available port in the specified range
def find_available_port(start_port=32002, end_port=32499):
    while True:
        port = random.randint(start_port, end_port)  # Randomly select a port within the range
        try:
            # Try to bind to the selected port to check if it's available
            test_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            test_socket.bind(('', port))
            test_socket.close()
            return port  # Return the available port
        except OSError:
            continue  # If the port is in use, continue the loop to find another port

# Function to create t-socket and p-socket
def create_sockets():
    global t_socket, p_socket, t_port, p_port, system_ip_address, destination_ip_address
    system_ip_address = input("Enter your IP address: ")  # Get the system's IP address
    destination_ip_address = input("Enter server IP address: ")  # Get the server's IP address
    t_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  # Create a transaction socket
    t_port = find_available_port()  # Find an available port for t_socket
    t_socket.bind((system_ip_address, t_port))  # Bind the socket to the found port
    
    p_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  # Create a player socket
    p_port = find_available_port()  # Find an available port for p_socket
    p_socket.bind((system_ip_address, p_port))  # Bind the socket to the found port

# Function to handle server messages in a separate thread
def listen_for_server_commands():
    global player_name, in_game
    while True:
        try:
            response, _ = t_socket.recvfrom(1024)  # Receive server response (buffer size = 1024 bytes)
            message = response.decode()  # Decode the response
            print(f"\nServer response: {message}")  # Print the server's response
            
            # Check for different server instructions
            if "Your turn!" in message:
                take_turn()  # Process the turn for swap or show
            elif "reveal two cards by sending the 'reveal <card1> <card2>' command." in message:
                reveal_initial_cards()  # Handle the first-round card reveal
            elif "Please wait for your turn." in message:
                print("Please wait for your turn.")  # Inform the player to wait
            elif "Game over!" in message:
                in_game = False  # Set the in_game flag to False when the game is over
                handle_game_over()  # Handle game over logic
            elif "You have already shown the discard stack." in message:
                print("Cannot send show again. Send pass or swap.")  # Show can't be repeated
                take_turn()  # Prompt the player for swap or pass action
        except Exception as e:
            print("Error receiving message:", e)  # Handle exceptions in receiving server messages

# Function to handle registration
def register():
    global player_name

    while True:
        player_name = input("Please enter your name (max 15 characters): ")  # Get the player's name
        if len(player_name) <= 15:
            break  # Ensure the name doesn't exceed 15 characters
        else:
            print("Error: Name is too long. Please try again.")  # Error message for long names

    message = f"register <{player_name}> <{system_ip_address}> <{t_port}> <{p_port}>"  # Registration message format
    t_socket.sendto(message.encode(), (destination_ip_address, 32001))  # Send the registration request to the server
    
    print("Waiting for a response from the server...")
    while True:
        response, _ = t_socket.recvfrom(1024)  # Wait for the server's response
        print("Server response:", response.decode())  # Print the server's response
        break

    startpage()  # Go to the start page

# Function for the start page
def startpage():
    global in_game
    while in_game == False:  # Loop as long as the player is not in a game
        print("\nWhat would you like to do today? Enter 1-5")
        print("1. Start a game of 6 card golf.")
        print("2. Join a game of 6 card golf.")
        print("3. See active players.")
        print("4. See active Games.")
        print("5. Exit")

        choice = input("Enter your choice: ")

        if choice == '1':
            start_game()  # Start a new game
        elif choice == '2':
            join_game()  # Join an existing game
        elif choice == '3':
            queryplayers()  # Query active players
        elif choice == '4':
            querygames()  # Query active games
        elif choice == '5':
            dereg()  # Deregister and exit
        else:
            print("Invalid choice. Please select a valid option.")  # Handle invalid choices

# Function to start a new game
def start_game():
    global player_name, in_game, system_ip_address, p_port

    # Start the listener thread for server messages
    listener_thread = threading.Thread(target=listen_for_server_commands)
    listener_thread.daemon = True
    listener_thread.start()  # Start the thread to listen for server commands
    
    # Get the number of players
    while True:
        try:
            n = int(input("Enter number of players (2-4): "))  # Get the number of players (2-4)
            if 2 <= n <= 4:
                break
            else:
                print("Invalid number of players. Please enter a number between 2 and 4.")
        except ValueError:
            print("Invalid input. Please enter a valid number.")  # Handle invalid inputs

    # Get the number of rounds (holes)
    while True:
        try:
            holes_input = input("Enter number of rounds (1-9) or press Enter for default (-1): ")  # Get the number of rounds
            if holes_input == '':
                holes = -1  # Default value if no input
                break
            else:
                holes = int(holes_input)  # Parse the input as an integer
            if 1 <= holes <= 9 or holes == -1:
                break  # Accept only values between 1-9 or default (-1)
            else:
                print("Invalid number of rounds.")
        except ValueError:
            print("Invalid input. Please enter a valid number.")  # Handle invalid inputs

    # Create the input_string in the format <<n>, <holes>>
    input_string = f"<{n}>, <{holes}>"
    
    # Send the start game message to the server in the required format
    message = f"startgame <{input_string}>"
    t_socket.sendto(message.encode(), (destination_ip_address, 32001))  # Send the start game request
  
    print("Waiting for players to join the game...")

    # Wait for the "Game_started" message from the server
    while True:
        response, _ = t_socket.recvfrom(1024)  # Wait for the server's response
        decoded_response = response.decode()

        if "Game_started" in decoded_response:
            print("Game is starting now!")
            listen_for_server_commands()  # Listen for game-related commands
            break  # Exit the loop when the game starts
        else:
            print(f"Received message from server: {decoded_response}")

    # Set the in_game flag to True
    in_game = True  # Set the player as in the game

# Function to join an existing game
def join_game():
    message = f"query games"
    t_socket.sendto(message.encode(), (destination_ip_address, 32001))  # Query active games from the server
    print(f"Sent 'query games' request to the server")
    
    # Wait indefinitely for a reply from the server
    while True:
        try:
            data, server = t_socket.recvfrom(1024)  # Receive the response from the server
            response = data.decode()  # Decode the response
            print(f"{response}")  # Print the list of active games
            break
        except Exception as e:
            print(f"Error receiving data: {e}")
            break

    game_index = input("Enter the game index to join: ")  # Get the game index from the user
    message = f"join game <{player_name}> <{game_index}>"
    t_socket.sendto(message.encode(), (destination_ip_address, 32001))  # Send the join game request
    print(f"Requested to join game {game_index}.")

    # Wait for the "Game_started" message
    while True:
        response, _ = t_socket.recvfrom(1024)  # Wait for the server's response
        decoded_response = response.decode()
        if "Game_started" in decoded_response:
            print("Game is starting now!")
            listen_for_server_commands()  # Listen for game-related commands
            break
        else:
            print(f"Waiting for the game to start. Received message: {decoded_response}")

# Function to handle game over logic
def handle_game_over():
    global in_game
    print("Game over!")
    in_game = False  # Reset in_game flag to indicate the game has ended.
    print("The game has ended. Returning to start page...")
    time.sleep(2)  # Allow some time for the message to display before resetting.
    startpage()  # Return to the start page after the game ends.

# Function to process a player's turn
def take_turn():
    print("It's your turn! You can either swap a card, show the discard stack, or pass.")
    while True:
        action = input("Enter 'swap top <index>', 'show' to reveal the discard stack top, or 'pass' to skip: ").strip().lower()

        if action.startswith("swap"):
            try:
                card_position = int(action.split()[2])  # Expecting input format 'swap top <index>'
                if 1 <= card_position <= 6:
                    message = f"swap top {card_position}"
                    t_socket.sendto(message.encode(), (destination_ip_address, 32001))  # Send the swap request
                    break
                else:
                    print("Invalid card position. Please enter a number between 1 and 6.")
            except (IndexError, ValueError):
                print("Invalid format. Use 'swap top <index>' where <index> is a number between 1 and 6.")
        elif action == "show":
            message = "show"  # The player chooses to show the top of the discard stack
            t_socket.sendto(message.encode(), (destination_ip_address, 32001))  # Send the show request
            break
        elif action == "pass":
            message = "swap pass"  # Player chooses to pass (discard the top card)
            t_socket.sendto(message.encode(), (destination_ip_address, 32001))  # Send the pass request
            break
        else:
            print("Invalid action. Please enter 'swap top <index>', 'show', or 'pass'.")

# Function to reveal initial two cards at the start of the game
def reveal_initial_cards():
    print("You need to reveal two cards.")
    while True:
        try:
            first_card = int(input("Enter the first card position (1-6): "))  # Get the first card position
            second_card = int(input("Enter the second card position (1-6): "))  # Get the second card position
            if 1 <= first_card <= 6 and 1 <= second_card <= 6:
                message = f"reveal {first_card} {second_card}"  # Send the 'reveal' command
                t_socket.sendto(message.encode(), (destination_ip_address, 32001))  # Send the reveal request
                break
            else:
                print("Invalid card positions. Please enter numbers between 1 and 6.")
        except ValueError:
            print("Invalid input. Please enter a number.")  # Handle invalid input

# Welcome function to start the program
def welcome():
    message = input("Welcome! Do you want to play? (y/n) ")  # Ask the user if they want to play
    if message.lower() == "n":
        print("terminating")  # If no, terminate the program
    else:
        print("BEFORE PLAYING PLEASE ESTABLISH CONNECTION.")  # Prompt to establish connection
        print("-X-")
        register()  # Proceed to registration

# Function to query active players
def queryplayers():
    message = f"query players"
    t_socket.sendto(message.encode(), (destination_ip_address, 32001))  # Send query players request
    print(f"Sent 'query players' request to the server")
    
    # Wait indefinitely for a reply from the server
    while True:
        try:
            data, server = t_socket.recvfrom(1024)  # Receive the response from the server
            response = data.decode()  # Decode the response
            print(f"{response}")  # Print the list of active players
            startpage()  # Return to the start page after receiving the response
        except Exception as e:
            print(f"Error receiving data: {e}")
            break

# Function to query active games
def querygames():
    message = f"query games"
    t_socket.sendto(message.encode(), (destination_ip_address, 32001))  # Send query games request
    print(f"Sent 'query games' request to the server")
    
    # Wait indefinitely for a reply from the server
    while True:
        try:
            data, server = t_socket.recvfrom(1024)  # Receive the response from the server
            response = data.decode()  # Decode the response
            print(f"{response}")  # Print the list of active games
            startpage()  # Return to the start page after receiving the response
        except Exception as e:
            print(f"Error receiving data: {e}")
            break

# Function to deregister and exit the program
def dereg():
    message = f"de-register <{player_name}>"  # Create the deregistration message
    t_socket.sendto(message.encode(), (destination_ip_address, 32001))  # Send deregister request
    print(f"Sent 'de-register and exit' request to the server")
    
    # Wait indefinitely for a reply from the server
    while True:
        try:
            data, server = t_socket.recvfrom(1024)  # Receive the response from the server
            response = data.decode()  # Decode the response
            print(f"{response}")  # Print the server response
            time.sleep(3)  # Wait for 3 seconds
            print("Exiting the program...")
            sys.exit(0)  # Terminate the program gracefully
        except Exception as e:
            print(f"Error receiving data: {e}")
            break

# Main function to start player.py
if __name__ == "__main__":
    create_sockets()  # Create the necessary sockets for communication
    welcome()  # Start the welcome process
