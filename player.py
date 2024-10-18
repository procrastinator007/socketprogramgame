import socket
import random
import threading
import time
import sys

# Global variables
t_socket = None
p_socket = None
t_port = None
p_port = None
system_ip_address = None
destination_ip_address = None
player_name = None  # To store the player's name globally
in_game = False

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
    global t_socket, p_socket, t_port, p_port, system_ip_address, destination_ip_address
    system_ip_address = input("Enter your IP address: ")
    destination_ip_address = input("Enter server IP address: ")
    t_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    t_port = find_available_port()
    t_socket.bind((system_ip_address, t_port))
    
    p_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    p_port = find_available_port()
    p_socket.bind((system_ip_address, p_port))

# Function to handle server messages in a separate thread
def listen_for_server_commands():
    
    global player_name, in_game
    while True:
        try:
            response, _ = t_socket.recvfrom(1024)
            message = response.decode()
            print(f"\nServer response: {message}")
            
            # Check for different server instructions
            if "Your turn!" in message:
                take_turn()  # Process the turn for swap or show
            elif "reveal two cards by sending the 'reveal <card1> <card2>' command." in message:
                reveal_initial_cards()  # First-round reveal cards
            elif "Please wait for your turn." in message:
                print("Please wait for your turn.")
            elif "Game over!" in message:
                in_game = False
                print("The game has ended. Returning to start page...")
                time.sleep(5)
                startpage()
            elif "You have already shown the discard stack." in message:
                print("Cannot send show again send pass or swap")
                take_turn()
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

    message = f"register <{player_name}> <{system_ip_address}> <{t_port}> <{p_port}>"
    t_socket.sendto(message.encode(), (destination_ip_address, 32001))
    
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
            join_game()
        if choice == '3':
            queryplayers()
        elif choice == '4':
            querygames()
        elif choice == '5':
            dereg()
        else:
            print("Invalid choice. Please select a valid option.")


def start_game():
    global player_name, in_game, system_ip_address, p_port

    # Start the listener thread for server messages
    listener_thread = threading.Thread(target=listen_for_server_commands)
    listener_thread.daemon = True
    listener_thread.start()
    
    # Get the number of players
    while True:
        try:
            n = int(input("Enter number of players (2-4): "))
            if 2 <= n <= 4:
                break
            else:
                print("Invalid number of players. Please enter a number between 2 and 4.")
        except ValueError:
            print("Invalid input. Please enter a valid number.")

    # Get the number of rounds (holes)
    while True:
        try:
            holes_input = input("Enter number of rounds (1-9) or press Enter for default (-1): ")
            if holes_input == '':
                holes = -1  # Default value if no input
                break
            else:
                holes = int(holes_input)
            if 1 <= holes <= 9 or holes == -1:
                break
            else:
                print("Invalid number of rounds.")
        except ValueError:
            print("Invalid input. Please enter a valid number.")

    # Create the input_string in the format <<n>, <holes>>
    input_string = f"<{n}>, <{holes}>"
    
    # Send the start game message to the server in the required format
    message = f"startgame <{input_string}>"
    t_socket.sendto(message.encode(), (destination_ip_address, 32001))
  
    print("Waiting for players to join the game...")

    # Wait for the "Game_started" message from the server
    while True:
        response, _ = t_socket.recvfrom(1024)
        decoded_response = response.decode()

        if "Game_started" in decoded_response:
            print("Game is starting now!")
            listen_for_server_commands()
            break  # Exit the loop when the game starts
        else:
            print(f"Received message from server: {decoded_response}")

    # Set the in_game flag to True
    in_game = True


def join_game():
    message = f"query games"
    t_socket.sendto(message.encode(), (destination_ip_address, 32001))
    print(f"Sent 'query games' request to the server")
    
    # Wait indefinitely for a reply from the server
    while True:
        try:
            # Receive the response from the server
            data, server = t_socket.recvfrom(1024)  # Buffer size is 1024 bytes
            response = data.decode()
            
            # Print the server response (list of active players)
            print(f"{response}")
            break
        except Exception as e:
            print(f"Error receiving data: {e}")
            break


    game_index = input("Enter the game index to join: ")
    message = f"join game <{player_name}> <{game_index}>"
    t_socket.sendto(message.encode(), (destination_ip_address, 32001))
    print(f"Requested to join game {game_index}.")

    # Wait for the "Game_started" message
    while True:
        response, _ = t_socket.recvfrom(1024)
        decoded_response = response.decode()
        if "Game_started" in decoded_response:
            print("Game is starting now!")
            listen_for_server_commands()
            break
        else:
            print(f"Waiting for the game to start. Received message: {decoded_response}")




def take_turn():
    print("It's your turn! You can either swap a card, show the discard stack, or pass.")
    while True:
        action = input("Enter 'swap top <index>', 'show' to reveal the discard stack top, or 'pass' to skip: ").strip().lower()

        if action.startswith("swap"):
            try:
                card_position = int(action.split()[2])  # Expecting input format 'swap top <index>'
                if 1 <= card_position <= 6:
                    message = f"swap top {card_position}"
                    t_socket.sendto(message.encode(), (destination_ip_address, 32001))
                    break
                else:
                    print("Invalid card position. Please enter a number between 1 and 6.")
            except (IndexError, ValueError):
                print("Invalid format. Use 'swap top <index>' where <index> is a number between 1 and 6.")
        elif action == "show":
            message = "show"  # The player chooses to show the top of the discard stack
            t_socket.sendto(message.encode(), (destination_ip_address, 32001))
            break
        elif action == "pass":
            message = "swap pass"  # Player chooses to pass (discard the top card)
            t_socket.sendto(message.encode(), (destination_ip_address, 32001))
            break
        else:
            print("Invalid action. Please enter 'swap top <index>', 'show', or 'pass'.")


def reveal_initial_cards():
    print("You need to reveal two cards.")
    while True:
        try:
            first_card = int(input("Enter the first card position (1-6): "))
            second_card = int(input("Enter the second card position (1-6): "))
            if 1 <= first_card <= 6 and 1 <= second_card <= 6:
                message = f"reveal {first_card} {second_card}"  # Send the 'reveal' command
                t_socket.sendto(message.encode(), (destination_ip_address, 32001))
                break
            else:
                print("Invalid card positions. Please enter numbers between 1 and 6.")
        except ValueError:
            print("Invalid input. Please enter a number.")


# Welcome function to start the program
def welcome():
    message= input("Welcome! do you want to play? (y/n) ")
    if message.lower() == "n":
        print("terminating")
    else:
        print("BEFORE PLAYING PLEASE ESTABLISH CONNECTION.")
        print("-X-")
        register()

def queryplayers():
    message = f"query players"
    t_socket.sendto(message.encode(), (destination_ip_address, 32001))
    print(f"Sent 'query players' request to the server")
    
    # Wait indefinitely for a reply from the server
    while True:
        try:
            # Receive the response from the server
            data, server = t_socket.recvfrom(1024)  # Buffer size is 1024 bytes
            response = data.decode()
            
            # Print the server response (list of active players)
            print(f"{response}")
            
            # After receiving the response, return to the startpage() function
            startpage()
        
        except Exception as e:
            print(f"Error receiving data: {e}")
            break

def querygames():
    message = f"query games"
    t_socket.sendto(message.encode(), (destination_ip_address, 32001))
    print(f"Sent 'query games' request to the server")
    
    # Wait indefinitely for a reply from the server
    while True:
        try:
            # Receive the response from the server
            data, server = t_socket.recvfrom(1024)  # Buffer size is 1024 bytes
            response = data.decode()
            
            # Print the server response (list of active players)
            print(f"{response}")
            
            # After receiving the response, return to the startpage() function
            startpage()
        
        except Exception as e:
            print(f"Error receiving data: {e}")
            break

def dereg():
    message = f"de-register <{player_name}>"
    t_socket.sendto(message.encode(), (destination_ip_address, 32001))
    print(f"Sent 'de-register and exit' request to the server")
    
    # Wait indefinitely for a reply from the server
    while True:
        try:
            # Receive the response from the server
            data, server = t_socket.recvfrom(1024)  # Buffer size is 1024 bytes
            response = data.decode()
            
            # Print the server response (list of active players)
            print(f"{response}")
            time.sleep(3)
            print("Exiting the program...")
            sys.exit(0)  # Terminate the program gracefully
        
        except Exception as e:
            print(f"Error receiving data: {e}")
            break

# Main function to start player.py
if __name__ == "__main__":
    create_sockets()
    welcome()