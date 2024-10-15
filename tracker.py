import socket
import time 
import threading
import random

# Global arrays
player_group = []  # Contains tuples like {player, ip, t-port, p-port}
game_identifier = []  # Stores ongoing game data
server_port = None
server_ip =None
client_ip =None
client_port =None
lock = threading.Lock()
card_map = {}
udp_socket = None
#creating a UDP socket to recieve data
def udp_server(udp_socket):
    global server_port, client_ip, client_port
    
    print("listening")


    while True:
        try:
            # Receive data from clients
            data, client_address = udp_socket.recvfrom(1024)
            client_ip, client_port = client_address
            print("checking port")
            
            
            # Check if the client port is within the specified range (32002 - 32499)
            if 32002 <= client_port <= 32499:
                message = data.decode()
                print("decoding data")
                #processing the message 
                if '<' in message:
                    command, _, input_string = message.partition('<')
                    command = command.strip()  # Strip whitespace
                    input_string = "<" + input_string
                    input_string = input_string.strip()  # Strip whitespace
                    
                    if command == "register":
                        print("going to register function")
                        register(input_string, client_ip)
                    elif command == "startgame":
                        start_game(client_ip, client_port, input_string)
                    elif command == "end":
                        end_game(input_string)
                    elif command == "de-register":
                        de_register(client_ip, client_port, input_string)
                    elif command == "join game":
                        join_game(input_string)
                    else:
                        print("Invalid command.")
                else:
                    # No '<' in the message
                    if message == 'query players':
                        query_players(client_ip, client_port)
                    elif message == 'query games':
                        print("querying games")
                        query_games(client_ip, client_port)
                    else:
                        print("Invalid input.")
            else:
                print(f"Connection from invalid port {client_port}. Ignoring.")
        except KeyboardInterrupt:
            print("\nServer shutting down.")
            break

    udp_socket.close()


#creating a function that registers players in the game
def register(input_string, client_ip):
    print("in register function")
    global player_group
    elements = []
    current_value = ""
    inside_tag = False

    # Iterate through each character in the input string
    for char in input_string:
        if char == '<':
            if inside_tag:
                print("double <")
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

    # Process the input in chunks of 4 (player, IP, t-port, p-port)
    for i in range(0, len(elements), 4):
        player = elements[i]
        ip_addr = elements[i+1]
        t_port = elements[i+2]
        p_port = elements[i+3]

        # Check if the player name is unique
        if any(existing_player[0] == player for existing_player in player_group):
            print(f"Player '{player}' already exists.")
            continue  # Skip adding this player

        # Check if player name is too long
        if len(player) > 15:
            message = f"Too long of a name: {player}. Limit is 15 characters."
            send_message(client_ip, t_port, message)
            print(f"Message sent via t-port: {message}")
            continue  # Skip adding this player

        # Validate IPv4 address
        if not is_valid_ipv4(ip_addr):
            message = f"Invalid IPv4 address: {ip_addr}."
            send_message(client_ip, t_port, message)
            print(f"Message sent via t-port: {message}")
            continue  # Skip adding this player

        # If all checks pass, add the player to the global player_group
        player_group.append((player, ip_addr, t_port, p_port))
        print(f"Player '{player}' with IP {ip_addr}, t-port {t_port}, and p-port {p_port} has been registered.")
        message = "player registered"
        send_message(client_ip,int(t_port),message)

def start_game(client_ip, client_port, input_string):
    global player_group, game_identifier
    
    print(f"Received input_string: {input_string}")
    
    try:
        # Extract the number of players and rounds from game_details
        n_str, holes_str = input_string.strip('<>').split('>, <')
        n = int(n_str.strip())
        holes = int(holes_str.strip())
        print(f"Parsed players: {n}, rounds: {holes}")
    except ValueError:
        print("Error: Invalid input string.")
        send_message(client_ip, client_port, "Invalid input string.")
        return

    print("Checking if the player is registered...")

    # Use the client IP to find the player name from the player_group
    # Find the correct player tuple from player_group using the player_name from client_ip
    registered_player = next((entry for entry in player_group if entry[1] == client_ip), None)

    if not registered_player:
        print("Player not found.")
        send_message(client_ip, client_port, "You are not registered with that IP and port.")
        return

    print(f"Creating game entry for {registered_player[0]}...")
    game_index = len(game_identifier)
    game_name = f"{registered_player[0]}'s Game"
    
    # Add player tuple to the temp_players_array
    temp_players_array = [(1, registered_player[1], registered_player[2])]
    
    game_entry = {
        "index": game_index,
        "name": game_name,
        "players": temp_players_array,
        "players_needed": n - 1,
        "rounds": holes,
        "ongoing": False
    }

    game_identifier.append(game_entry)
    print(f"Game '{game_name}' created with {n} players.")

    # Call the waiting room logic to handle player waiting
    waiting_room(game_entry)


# join game has a formatted input of join game <player> <game_index>
def join_game(message):
    global game_identifier, player_group
    
    # Split the input message to get player and game_index
    stripped_message = message.strip('<>').strip()
    player_name, game_index_str = stripped_message.split()
    
    game_index = int(game_index_str)  # Convert game_index to an integer

    # Retrieve the game entry using the game_index
    game_entry = next((game for game in game_identifier if game["index"] == game_index), None)

    if game_entry is None:
        print(f"Game with index {game_index} not found.")
        return  # Game not found, exit function
    
    #Find the player details in player_group
    player_details = next((player for player in player_group if player[0] == player_name), None)
    
    if player_details is None:
        print(f"Player {player_name} is not registered.")
        return  # Player not registered, exit function
    
    # Copy the player details into a temp variable
    temp_player = player_details  # This is a tuple (player, ip, t-port, p-port)
    
    # Append the player to the players_array of the game_entry
    game_entry["players"].append((len(game_entry["players"]) + 1, temp_player))  # Using the next index for player
    game_entry["players_needed"] -= 1  # Decrement players needed
    
    
    # Update the game_identifier array (not strictly necessary unless you want to maintain a reference)
    for i in range(len(game_identifier)):
        if game_identifier[i]["index"] == game_index:
            game_identifier[i] = game_entry  # Update the game entry in the identifier array

    else:
        waiting_room()
####
##
#
#
#


def waiting_room(game_entry):
    global udp_socket
    print(f"Entering waiting room for {game_entry['name']}...")

    # Check for players_needed in the game
    if game_entry["players_needed"] > 0:
        # Notify all players that the game is still waiting for more players
        for player_tuple in game_entry["players"]:
            player_ip, player_port = player_tuple[1], player_tuple[2]
            send_message(player_ip, player_port, "Still waiting for more players...")
        print(f"Still waiting for players to join {game_entry['name']}. Players needed: {game_entry['players_needed']}")
        udp_server(udp_socket) # Go back to udp_server() to keep listening for more players
    else:
        # If players_needed == 0, start the game
        game_entry["ongoing"] = True
        print(f"Starting game: {game_entry['name']}")

        # Notify all players that the game is starting
        for player_tuple in game_entry["players"]:
            player_ip, player_port = player_tuple[1], player_tuple[2]
            send_message(player_ip, player_port, "Game_started")
        
        # Proceed with the game logic
        temp_player_group = [player_tuple[1] for player_tuple in game_entry["players"]]
        play_game(temp_player_group, game_entry["rounds"])




        
def play_game(players, rounds):
    # Initialize the deck, shuffle, and deal 6 cards to each player
    deck = list(range(1, 53))  # Full deck
    random.shuffle(deck)
    
    player_hands = {}
    visible_cards = {player[0]: [False] * 6 for player in players}  # Initially no cards are visible
    for player in players:
        hand = random.sample(deck, 6)
        player_hands[player[0]] = hand
        for card in hand:
            deck.remove(card)

    discard_stack = [deck.pop(0)]  # Initialize discard stack

    # Send the initial hidden hand and discard stack to players
    for player in players:
        player_name, ipaddr, t_port, _ = player
        message = format_message(player_name, player_hands, discard_stack, visible_cards)
        send_udp_message(ipaddr, t_port, message)
    
    # Step 1: Ask for the first two cards to reveal
    for player in players:
        player_name, ipaddr, t_port, _ = player
        send_udp_message(ipaddr, t_port, "Select two cards to reveal (enter two integers):")
        selected = listen_for_player_action(ipaddr, t_port)
        # Reveal the selected cards
        visible_cards[player_name][selected[0] - 1] = True
        visible_cards[player_name][selected[1] - 1] = True

    # Step 2: Play rounds
    for _ in range(rounds):
        for i, player in enumerate(players):
            player_name, ipaddr, t_port, _ = player
            # Announce it's this player's turn and others should wait
            for p in players:
                if p[0] == player_name:
                    send_udp_message(p[1], p[2], "Your turn!")
                else:
                    send_udp_message(p[1], p[2], "Wait for your turn...")
            
            # Get player's action (swap or show next)
            player_action = listen_for_player_action(ipaddr, t_port)

            # Handle player's action: either swap or reveal
            handle_player_action(player_name, player_hands, player_action, discard_stack, visible_cards)

            # Send the updated hand and discard stack to all players
            for p in players:
                message = format_message(p[0], player_hands, discard_stack, visible_cards)
                send_udp_message(p[1], p[2], message)

        # End the game if any player reveals all their cards
        if any(all(visible for visible in v_cards) for v_cards in visible_cards.values()):
            break

    # After rounds or if a player reveals all cards, end game
    end_game_logic(players, player_hands, visible_cards)

def format_message(player_name, player_hands, discard_stack, visible_cards):
    message = "\nYour cards:\n"
    player_hand = player_hands[player_name]
    message += format_hand(player_hand, visible_cards[player_name]) + "\n"
    
    for other_player, hand in player_hands.items():
        if other_player != player_name:
            message += f"{other_player}'s cards:\n"
            message += format_hand(hand, visible_cards[other_player]) + "\n"
    
    message += "Discard Stack:\n"
    message += get_card(discard_stack[-1]) + "\n"
    return message

def format_hand(hand, visible):
    hand_str = ""
    for i, card in enumerate(hand):
        if visible[i]:
            hand_str += f"{get_card(card)}  "
        else:
            hand_str += "***  "
        if (i + 1) % 3 == 0:
            hand_str += "\n"
    return hand_str

def handle_player_action(player_name, player_hands, action, discard_stack, visible_cards):
    if action[0] == "swap":
        card_index = int(action[1]) - 1
        visible_cards[player_name][card_index] = True
        discard_stack.insert(0, player_hands[player_name][card_index])
        player_hands[player_name][card_index] = discard_stack.pop(1)
    elif action[0] == "show":
        discard_stack.pop(0)  # Discard top
        new_top = discard_stack[0]
        send_udp_message(player_name, "New top of the discard stack: " + get_card(new_top))

def listen_for_player_action(ipaddr, t_port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((ipaddr, t_port))
    while True:
        data, _ = sock.recvfrom(1024)
        action = data.decode().strip().split()
        if action[0] in {"swap", "show"} and len(action) >= 2:
            return action

def end_game_logic(players, player_hands, visible_cards):
    scores = {p[0]: sum(visible_cards[p[0]]) for p in players}
    winner = max(scores, key=scores.get)
    for p in players:
        send_udp_message(p[1], p[2], f"Game over! The winner is {winner}.")

def send_udp_message(ipaddr, port, message):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.sendto(message.encode(), (ipaddr, port))
    sock.close()

def de_register(client_ip, client_port, input_string):
    global player_group
    
    # Strip off the '<' and '>' from the input_string to extract the player name
    player_name = input_string.strip('<>').strip()
    
    # Find the player in the player_group by comparing the player name
    player_found = None
    for player_tuple in player_group:
        if player_tuple[0] == player_name:  # Compare player name
            player_found = player_tuple
            break
    
    # If player is found, remove them from player_group
    if player_found:
        player_group.remove(player_found)
        print(f"Player {player_name} has been de-registered.")
        
        # Send a return message to the client
        return_message = 'terminate'
        send_message(client_ip,client_port,return_message)
        print(f"Sent termination message to {client_ip}:{client_port}")
    else:
        print(f"Player {player_name} not found. No action taken.")

#checks listed players
def query_players(client_ip, client_port):
    global player_group
    
    # If no players are registered, return an empty list message
    if not player_group:
        send_message(client_ip, client_port, "No players currently registered.")
        return

    # Construct the message with all players' information
    player_info_message = ""
    for index, player in enumerate(player_group):
        player_name, ip, t_port, p_port = player
        player_info_message += f"{player_name} {ip} {p_port}\n"

    # Send the complete message back to the client
    send_message(client_ip, client_port, player_info_message.strip())

# Function to query all games and return the game status to the client
def query_games(client_ip, client_port):
    global game_identifier
    
    # If no games are in the identifier, return a message
    if not game_identifier:
        message = "No games currently available."
        send_message(client_ip, client_port, message)
        return

    # Construct the message with all games' information
    game_info_message = ""
    for game in game_identifier:
        game_index = game["index"]
        game_name = game["name"]
        players_needed = game["players_needed"]
        rounds = game["rounds"]
        ongoing = game["ongoing"]

        # Construct message based on the game's state (waiting room or ongoing)
        if not ongoing:
            game_info_message += (f"{game_index}. {game_name} is in the waiting room, {rounds} "
                                  f"round(s) will be played and {players_needed} more "
                                  "player(s) are needed.\n")
        else:
            game_info_message += f"{game_index}. {game_name} is being played.\n"
    
    # Send the complete message back to the client
    send_message(client_ip, client_port, game_info_message.strip())


# functions for register: 
def send_message(ip, port, message):
    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_socket.sendto(message.encode(), (ip, int(port)))

# checks ip address format
def is_valid_ipv4(ip):
    """Validate if the given string is a valid IPv4 address in the format x.x.x.x where x < 256."""
    parts = ip.split('.')
    if len(parts) != 4:
        return False
    for part in parts:
        try:
            if not 0 <= int(part) < 256:
                return False
        except ValueError:
            return False
    return True


# functions for start game
# A function to generate a mapping of cards to numbers
#
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
    
    #Return the corresponding card string
    return card_map[number]

# Example Usage:
if __name__ == "__main__":
    card_map = generate_card_mapping()
    server_ip = input("Enter ip_address here: ")
    server_port = 32001
    
    # Create UDP socket
    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    # Bind the socket to the server address and port
    udp_socket.bind((server_ip, server_port))
    udp_server(udp_socket)
