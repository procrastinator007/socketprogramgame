import socket

#creating a UDP socket to recieve data
def udp_server():
    # Server-side setup: bind to port 32001
    server_ip = "0.0.0.0"  # Listen on all interfaces
    server_port = 32001
    buffer_size = 1024  # Buffer size for receiving data in Bytes

    # Create UDP socket
    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    # Bind the socket to the server address and port
    udp_socket.bind((server_ip, server_port))
    
    while True:
        try:
            # Receive data from clients
            data, client_address = udp_socket.recvfrom(buffer_size)
            client_ip, client_port = client_address
            
            # Check if the client port is within the specified range (32002 - 32499)
            if 32002 <= client_port <= 32499:
                message = data.decode()
                #processing the message 
                if '<' in message:
                    command, _, input_string = message.partition('<')
                    command = command.strip()  # Strip whitespace
                    input_string = input_string.strip()  # Strip whitespace
                    
                    if command == "register":
                        register(input_string)
                    elif command == "start game":
                        start_game(input_string)
                    elif command == "end":
                        end_game(input_string)
                    elif command == "de-register":
                        de_register(input_string)
                    else:
                        print("Invalid command.")
                else:
                    # No '<' in the message
                    if message == 'query players':
                        query_players()
                    elif message == 'query games':
                        query_games()
                    else:
                        print("Invalid input.")
            else:
                print(f"Connection from invalid port {client_port}. Ignoring.")
        except KeyboardInterrupt:
            print("\nServer shutting down.")
            break

    udp_socket.close()


#creating a function that registers players in the game
def register(input_string):
    elements = []
    current_value = ""
    inside_tag = False

    # Iterate through each character in the input string
    for char in input_string:
        if char == '<':
            if inside_tag:
                raise ValueError("Unexpected '<' detected inside an open tag.")
            inside_tag = True  # Start capturing a new value
            current_value = ""  # Reset the current value

        elif char == '>':
            if not inside_tag:
                raise ValueError("Unexpected '>' detected without an open tag.")
            inside_tag = False  # Stop capturing this value
            elements.append(current_value.strip())  # Append the captured value
            current_value = ""  # Reset for the next value

        elif inside_tag:
            if char != ' ':  # Ignore spaces inside tags
                current_value += char

        elif char != ' ':  # Ignore spaces outside tags
            raise ValueError(f"Unexpected character '{char}' outside of tags.")

    # Check if we have exactly 4 sets of player data
    if len(elements) % 4 != 0:
        raise ValueError("Input must contain a multiple of 4 values for: <player>, <IPv4>, <t-port>, <p-port>")

    # Initialize a list for the players and corresponding details
    players = []

    # Process the input in chunks of 4 (player, IP, t-port, p-port)
    for i in range(0, len(elements), 4):
        player = elements[i]
        ip_addr = elements[i+1]
        t_port = elements[i+2]
        p_port = elements[i+3]
        
        players.append((player, ip_addr, t_port, p_port))

    # Print the result in the desired format
    #for item in players:
    #   print(f"{item[0]} {item[1]} {item[2]} {item[3]}")

def start_game(input_string):
    print(f"Starting game with: {input_string}")

def end_game(input_string):
    print(f"Ending game with: {input_string}")

def de_register(input_string):
    print(f"Deregistering: {input_string}")

def query_players():
    print("Querying players...")

def query_games():
    print("Querying games...")


# A function to generate a mapping of cards to numbers
def generate_card_mapping():
    # Define the card ranks and suits
    ranks = ['A','2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K']
    suits = ['S', 'H', 'D', 'C']  # Spades, Hearts, Diamonds, Clubs
    
    # Initialize the card map
    card_map = {}
    
    # Card index starts at 1 (Ace of Spades is 1)
    index = 1
    
    # Loop through each suit and rank to assign the card strings to the numbers
    for suit in suits:
        for rank in ranks:
            card_string = rank + suit
            card_map[index] = card_string
            index += 1
    
    return card_map

# Function to get a card string based on the number (1 to 52)
def get_card(number):
    # Validate if the input number is within range
    if number < 1 or number > 52:
        return "Invalid card number. Please enter a number between 1 and 52."
    
    # Generate the card mapping
    card_map = generate_card_mapping()
    
    # Return the corresponding card string
    return card_map[number]

# Example Usage:
if __name__ == "__main__":
    udp_server()
