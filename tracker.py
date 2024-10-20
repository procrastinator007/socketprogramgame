import socket
import time 
import threading
import random

# Global arrays
player_group = []  # Contains tuples like {player, ip, t-port, p-port}
game_identifier = []  # Stores ongoing game data
server_port = None  # Server's port
server_ip = None  # Server's IP address
client_ip = None  # Client's IP address
client_port = None  # Client's port
lock = threading.Lock()  # Lock object to synchronize threads
card_map = {}  # A dictionary for mapping cards to players
udp_socket = None  # UDP socket for server communication
game_registry = []  # Tracks game_id -> {thread, players, game_state}
player_game_map = []  # Tracks player (IP, port) -> game_id
revealed = False  # Global flag for checking if cards have been revealed

# Creating a UDP socket to receive data
def process_client_request(message, client_ip, client_port):
    # Process client request once and then break out of the loop
    try:
        if 32002 <= client_port <= 32499:  # Ensure client port is within valid range
            print("decoding data")
            
            # Processing the message
            if '<' in message:  # Check if message contains valid command syntax
                command, _, input_string = message.partition('<')  # Split message into command and input string
                command = command.strip()  # Strip whitespace
                input_string = "<" + input_string.strip()  # Strip whitespace and rebuild input string

                # Route commands based on the command keyword
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
                # Handle requests without '<'
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


# Server function to receive incoming UDP requests
def udp_server(udp_socket):
    global player_game_map
    print("Listening for incoming client requests...")

    while True:
        try:
            # Receive data from clients
            data, client_address = udp_socket.recvfrom(1024)
            client_ip, client_port = client_address
            message = data.decode()

            # Convert client_port to string for player_game_map comparison
            client_port_str = str(client_port)

            print(f"Received message from {client_ip}:{client_port} - {message}")
            print("Current player_game_map:", player_game_map)

            # Check if the player is already in a game
            if any((client_ip, client_port_str) == player_info for player_info, _ in player_game_map):
                # Get the player's game ID
                game_id = next(game_id for player_info, game_id in player_game_map if player_info == (client_ip, client_port_str))
                
                # Retrieve game info from game_registry
                game_info = next(info for id, info in game_registry if id == game_id)
                print("game info:", game_info)
                if game_info:
                    # Handle game-related action for the player
                    handle_game_action(game_info, message, client_ip, client_port)
                else:
                    print(f"Game ID {game_id} not found.")

            else:
                # Process new client requests (registrations, start game, etc.)
                client_port = int(client_port)
                process_client_request(message, client_ip, client_port)

        except KeyboardInterrupt:
            print("\nServer shutting down.")
            break

    udp_socket.close()

# Function to handle game actions (reveal, swap, show)
def handle_game_action(game_info, action, client_ip, client_port):
    # Find the player's name by matching their IP and port
    player_name = next((p[0] for p in game_info["players"] if p[1] == client_ip and str(p[2]) == str(client_port)), None)
    print(player_name)
    if player_name:
        # Perform game actions based on the command received
        if "reveal" in action:
            handle_reveal_action(game_info, player_name, action)
        elif "swap" in action:
            handle_swap_action(game_info, player_name, action)
        elif "show" in action:
            handle_show_and_pass_action(game_info, player_name)
    else:
        print(f"Unknown player {client_ip}:{client_port} attempted to take an action.")

# Handle revealing cards during the game
def handle_reveal_action(game_info, player_name, action):
    print("entering reveal action ")
    try:
        # Extract the card positions from the action string
        first_card, second_card = map(int, action.split()[1:3])  # Convert to integers

        # Mark the cards as visible in the game state
        game_info["game_state"]["visible_cards"][player_name][first_card - 1] = True
        game_info["game_state"]["visible_cards"][player_name][second_card - 1] = True

        # Get the current top card of the discard stack
        top_of_discard_stack = game_info["game_state"]["top_of_discard_stack"]

        # Send updated game state to all players
        for player in game_info["players"]:
            player_ip, player_port = player[1], player[2]
            message = format_message(player_name, game_info["game_state"]["player_hands"], 
                                     top_of_discard_stack,
                                     game_info["game_state"]["visible_cards"])
            send_udp_message(player_ip, int(player_port), message)

        # Move to the next player
        process_next_player(game_info)
    except (ValueError, IndexError) as e:
        print(f"Error processing reveal action: {e}")

# Handle the action where a player shows the discard stack and passes
def handle_show_and_pass_action(game_info, player_name):
    # Check if the player has already shown the discard stack in this turn
    if game_info["game_state"].get("has_shown", False):
        send_udp_message(game_info["players"][game_info["game_state"]["current_player"]][1],
                         int(game_info["players"][game_info["game_state"]["current_player"]][2]),
                         "You have already shown the discard stack. You must now either swap or pass.")
        return  # Exit if the player has already shown

    # Perform the show action
    discard_stack = game_info["game_state"]["discard_stack"]

    # Remove the top card from the discard stack
    if discard_stack:
        discarded_card = discard_stack.pop(0)
        print(f"{player_name} removed card {discarded_card} from the discard stack.")

    # Update the new top card of the discard stack
    top_of_discard_stack = game_info["game_state"]["top_of_discard_stack"] = discard_stack[0] if discard_stack else None

    # Send updated game state to all players
    for player in game_info["players"]:
        player_ip, player_port = player[1], player[2]
        message = format_message(player_name, game_info["game_state"]["player_hands"], 
                                 top_of_discard_stack, 
                                 game_info["game_state"]["visible_cards"])
        send_message_to_all(game_info, message)

    # Mark that the player has shown the discard stack in this turn
    game_info["game_state"]["has_shown"] = True

    # Get the previous player's index, wrapping around if necessary
    current_player_index = game_info["game_state"]["current_player"]
    previous_player_index = (current_player_index - 1) % len(game_info["players"])

    # Get the previous player's details
    previous_player = game_info["players"][previous_player_index]
    previous_player_ip, previous_player_port = previous_player[1], previous_player[2]

    # Ask the previous player to swap or pass
    send_udp_message(previous_player_ip, int(previous_player_port), 
                     "Your turn! You must now swap the top of the discard stack with one of your cards or pass.")

    # Allow the player to pass after showing
    game_info["game_state"]["can_pass"] = True

# Handle swapping cards in the game
def handle_swap_action(game_info, player_name, action):
    discard_stack = game_info["game_state"]["discard_stack"]
    player_hands = game_info["game_state"]["player_hands"]

    if "swap" in action:
        # If the action is 'swap top <index>'
        if "top" in action and len(action.split()) == 3:
            card_position = int(action.split()[2]) - 1  # Convert to 0-based index

            # Swap the top of the discard stack with the player's card
            top_of_discard_stack = game_info["game_state"]["top_of_discard_stack"]
            player_hands[player_name][card_position], game_info["game_state"]["top_of_discard_stack"] = top_of_discard_stack, player_hands[player_name][card_position]
            
            # Mark the swapped card as visible
            game_info["game_state"]["visible_cards"][player_name][card_position] = True

        # Send updated game state to all players
        for player in game_info["players"]:
            player_ip, player_port = player[1], player[2]
            message = format_message(player_name, game_info["game_state"]["player_hands"], 
                                     game_info["game_state"]["top_of_discard_stack"],
                                     game_info["game_state"]["visible_cards"])
            send_udp_message(player_ip, int(player_port), message)

        # Move to the next player
        process_next_player(game_info)
    elif "pass" in action and game_info["game_state"].get("can_pass", False):
        handle_pass_action(game_info, player_name)
    else:
        # If passing is not allowed
        send_udp_message(game_info["players"][game_info["game_state"]["current_player"]][1],
                         int(game_info["players"][game_info["game_state"]["current_player"]][2]),
                         "You cannot pass without first showing the discard stack.")



def handle_pass_action(game_info, player_name):
    # When a player passes, they do not swap any cards.
    # We still need to show the updated game state to all players.
    
    discard_stack = game_info["game_state"]["discard_stack"]  # Get the current discard stack
    
    # Send the updated game state to all players
    for player in game_info["players"]:
        player_ip, player_port = player[1], player[2]
        message = format_message(player_name, game_info["game_state"]["player_hands"], 
                                 discard_stack[0],  # Keep the top card of the discard stack visible
                                 game_info["game_state"]["visible_cards"])
        send_udp_message(player_ip, int(player_port), message)

    # After passing, move to the next player's turn
    process_next_player(game_info)


def process_next_player(game_info):
    global game_registry
    players = game_info["players"]  # Get the list of players
    round_count = game_info["game_state"]["round"]  # Get the current round count

    game_id = next((gid for gid, info in game_registry if info == game_info), None)  # Get the current game ID

    # Get the previous player's index by subtracting 1 from the current player, wrapping around if necessary
    previous_player_index = (game_info["game_state"]["current_player"] - 1) % len(players)
    previous_player = players[previous_player_index]  # Get the previous player's details
    previous_player_name = previous_player[0]  # Get the previous player's name

    # Check if all the previous player's cards are visible. If true, end the game after this round.
    if all(game_info["game_state"]["visible_cards"][previous_player_name]):
        print(f"All cards of {previous_player_name} are visible. Ending the game after this round.")
        game_info["game_state"]["round"] = game_info["rounds"]  # Set the current round as the final round

    # Check if all players have had their turn in this round
    if game_info["game_state"]["current_player"] >= len(players):
        game_info["game_state"]["current_player"] = 0  # Reset to the first player
        game_info["game_state"]["round"] += 1  # Increment the round count
        round_count = game_info["game_state"]["round"]  # Update the round count

    # If the round count exceeds the allowed number of rounds, end the game
    if round_count > game_info["rounds"]:
        end_game_logic(game_info, game_id)  # Call the end game logic function
    else:
        # If the game continues, proceed to the next player
        current_player_index = game_info["game_state"]["current_player"]
        current_player = players[current_player_index]
        player_name, ipaddr, t_port, _ = current_player  # Get current player's details
        game_info["game_state"]["current_player"] += 1  # Move to the next player's turn

        # Reset the 'can_pass' and 'has_shown' flags for the new player
        game_info["game_state"]["can_pass"] = False
        game_info["game_state"]["has_shown"] = False

        # Notify all other players to wait for their turn
        for player in players:
            other_ip, other_port = player[1], player[2]
            if player != current_player:
                print(f"Sending 'Please wait' to {other_ip}:{other_port}")
                send_udp_message(other_ip, int(other_port), "Please wait for your turn.")

        # If it's the first round, prompt the player to reveal two cards
        if round_count == 0:
            print(f"Sending 'Please reveal two cards' to {ipaddr}:{t_port}")
            send_udp_message(ipaddr, int(t_port), "Please reveal two cards by sending the 'reveal <card1> <card2>' command.")
        else:
            # For subsequent rounds, ask the player to swap or pass
            print(f"Sending 'Your turn' to {ipaddr}:{t_port}")
            send_udp_message(ipaddr, int(t_port), "Your turn! You can 'swap top <index>' or 'pass' or 'show'.")


# Function that registers players in the game
def register(input_string, client_ip):
    print("in register function")
    global player_group
    elements = []  # List to store parsed data
    current_value = ""  # Variable to store current value being parsed
    inside_tag = False  # Flag to track whether we are inside a tag

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

    # Ensure the input contains a valid multiple of 4 sets of data
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

        # Validate the player's IPv4 address
        if not is_valid_ipv4(ip_addr):
            message = f"Invalid IPv4 address: {ip_addr}."
            send_message(client_ip, t_port, message)
            print(f"Message sent via t-port: {message}")
            continue  # Skip adding this player

        # If all checks pass, add the player to the global player_group
        player_group.append((player, ip_addr, t_port, p_port))
        print(f"Player '{player}' with IP {ip_addr}, t-port {t_port}, and p-port {p_port} has been registered.")
        message = "player registered"
        send_message(client_ip, int(t_port), message)


# Function to start a game with a specified number of players and rounds
def start_game(client_ip, client_port, input_string):
    global player_group, game_identifier
    
    print(f"Received input_string: {input_string}")
    
    try:
        # Extract the number of players and rounds from game_details
        n_str, holes_str = input_string.strip('<>').split('>, <')
        n = int(n_str.strip())  # Parse number of players
        holes = int(holes_str.strip())  # Parse number of rounds
        print(f"Parsed players: {n}, rounds: {holes}")
    except ValueError:
        print("Error: Invalid input string.")
        send_message(client_ip, client_port, "Invalid input string.")
        return

    print("Checking if the player is registered...")

    # Use the client IP to find the player name from the player_group
    registered_player = next((entry for entry in player_group if entry[1] == client_ip), None)

    if not registered_player:
        print("Player not found.")
        send_message(client_ip, client_port, "You are not registered with that IP and port.")
        return

    print(f"Creating game entry for {registered_player[0]}...")
    game_index = len(game_identifier)  # Generate a new game index
    game_name = f"{registered_player[0]}'s Game"  # Name the game based on the player
    
    # Add the registered player to the temporary player array
    temp_players_array = [(registered_player[0], registered_player[1], registered_player[2], registered_player[3])]

    # Create a game entry with game details
    game_entry = {
        "index": game_index,
        "name": game_name,
        "players": temp_players_array,
        "players_needed": n - 1,  # Track how many more players are needed
        "rounds": holes,
        "ongoing": False  # Game has not started yet
    }

    game_identifier.append(game_entry)  # Add the game to the game_identifier list
    print(f"Game '{game_name}' created with {n} players.")

    # Call the waiting room function to wait for more players to join
    waiting_room(game_entry)




# join game has a formatted input of join game <player> <game_index>
def join_game(input_string):
    global game_identifier, player_group
    
    # Debugging: Print the raw input string to see its contents
    print(f"Raw input_string: {input_string}")
    
    try:
        # Strip '<' and '>' and split the input message to get player name and game index
        stripped_message = input_string.replace('<', '').replace('>', '').strip()
        print(f"Stripped message: {stripped_message}")  # Debugging output
        
        # Split the stripped message into player name and game index
        player_name, game_index_str = stripped_message.split()
        game_index = int(game_index_str)  # Convert game_index from string to integer
        
        print(f"Player Name: {player_name}, Game Index: {game_index}")
        
    except ValueError as e:
        # Handle any value errors, such as invalid splitting or conversion to integer
        print(f"Error converting game_index_str to int: {e}")
        return  # Exit function in case of error

    # Retrieve the game entry using the game_index
    game_entry = next((game for game in game_identifier if game["index"] == game_index), None)

    if game_entry is None:
        # If no game matches the provided game index, print an error and exit
        print(f"Game with index {game_index} not found.")
        return  # Exit function if game not found
    
    # Find the player's details in player_group (registered players)
    player_details = next((player for player in player_group if player[0] == player_name), None)
    
    if player_details is None:
        # If player is not found in the player group, print an error and exit
        print(f"Player {player_name} is not registered.")
        return  # Exit function if player is not registered
    
    # Create a player tuple with player details (name, IP, t-port, p-port)
    temp_player = (player_details[0], player_details[1], player_details[2], player_details[3])
    
    # Add the player to the list of players in the game entry
    game_entry["players"].append(temp_player)
    
    # Decrement the number of players needed to start the game
    game_entry["players_needed"] -= 1  
    
    # Update the game_identifier array (if needed, to keep the reference updated)
    for i in range(len(game_identifier)):
        if game_identifier[i]["index"] == game_index:
            # Update the game entry at the corresponding index in the array
            game_identifier[i] = game_entry

    # Print that the player successfully joined the game
    print(f"Player {player_name} has joined game {game_index}.")
    
    # Call waiting_room to handle player waiting or start the game
    waiting_room(game_entry)


def waiting_room(game_entry):
    global udp_socket
    print(f"Entering waiting room for {game_entry['name']}...")
    
    # Check if the game is still waiting for more players
    if game_entry["players_needed"] > 0:
        # Notify all registered players that the game is still waiting for more players
        for player_tuple in game_entry["players"]:
            if len(player_tuple) < 3:
                # Error handling: Check if the player tuple has the correct number of elements
                print(f"Error: Player tuple does not have enough elements: {player_tuple}")
                continue  # Skip players with incomplete details

            player_ip, player_port = player_tuple[1], player_tuple[2]
            # Send a message to the player indicating that more players are needed
            send_message(player_ip, player_port, "Still waiting for more players...")
        
        # Print how many more players are needed to start the game
        print(f"Still waiting for players to join {game_entry['name']}. Players needed: {game_entry['players_needed']}")
        
        # Return to the UDP server to keep listening for incoming player connections
        udp_server(udp_socket)  

    else:
        # If enough players have joined, mark the game as ongoing and start the game
        game_entry["ongoing"] = True
        print(f"Starting game: {game_entry['name']}")
        
        # Notify all players in the game that it is starting
        for player_tuple in game_entry["players"]:
            if len(player_tuple) < 3:
                # Error handling: Check if the player tuple has the correct number of elements
                print(f"Error: Player tuple does not have enough elements: {player_tuple}")
                continue  # Skip players with incomplete details

            player_ip, player_port = player_tuple[1], player_tuple[2]
            # Send a message to each player that the game has started
            send_message(player_ip, player_port, "Game_started")
        
        # Start the game by extracting all player tuples and initiating the game thread
        temp_player_group = [player_tuple for player_tuple in game_entry["players"] if len(player_tuple) >= 3]
        start_game_thread(temp_player_group, game_entry["rounds"])

    # After the game starts or while waiting for more players, keep listening for new clients
    udp_server(udp_socket)

        
def play_game(players, rounds, game_id):
    global game_registry  # Access the global game_registry to store the game state

    # Create a deck of cards with 52 cards and shuffle them
    deck = list(range(1, 53))
    random.shuffle(deck)

    # Assign 6 cards to each player and remove them from the deck
    player_hands = {}
    for player in players:
        hand = [deck.pop(0) for _ in range(6)]  # Deal 6 cards to each player
        player_hands[player[0]] = hand  # Store the player's hand using their name as the key

    # The first card from the remaining deck becomes the top of the discard stack
    top_of_discard_stack = deck.pop(0)

    # The remaining cards form the discard stack
    discard_stack = deck

    # Initialize the visible_cards dictionary with 6 False values for each player (all cards hidden)
    visible_cards = {player[0]: [False] * 6 for player in players}

    # Store the initial game state including player hands, discard stack, and round number
    game_state = {
        "player_hands": player_hands,
        "top_of_discard_stack": top_of_discard_stack,
        "discard_stack": discard_stack,
        "visible_cards": visible_cards,
        "round": 0,  # The game starts at round 0
        "current_player": 0  # The first player (index 0) will take the first turn
    }

    # Send the initial hand and game state to each player
    for player in players:
        player_name, ipaddr, t_port, _ = player
        # Format and send the player's hand, top of discard stack, and visibility of cards
        message = format_message(player_name, player_hands, top_of_discard_stack, visible_cards)
        send_udp_message(ipaddr, int(t_port), message)

    # Update the game_state in the game_registry for the corresponding game_id
    for i, (gid, info) in enumerate(game_registry):
        if gid == game_id:
            game_registry[i][1]["game_state"] = game_state  # Update the game state in the registry

    print(f"Game info after initialization: {game_registry}")

    # Start the game by asking players to reveal their cards sequentially
    process_next_player(game_registry[i][1])  # Pass the updated game_info with game_state


def start_game_thread(players, rounds):
    global player_game_map
    global game_registry
    # Generate a random unique game ID for this game instance
    game_id = random.randint(1000, 9999)

    # Map each player (IP and port) to the game_id to track which game they're part of
    for player in players:
        player_ip = player[1]
        player_port = str(player[2])  # Convert port to string for easier comparison
        player_game_map.append(((player_ip, player_port), game_id))  # Add player to player_game_map

    print(f"player_game_map after update: {player_game_map}")

    # Create a new game entry with players, rounds, and initialize game_state to None for now
    game_info = {
        "players": players,
        "rounds": rounds,
        "game_state": None  # game_state will be fully initialized in play_game
    }
    # Add the game entry to game_registry with the game_id and game_info
    game_registry.append((game_id, game_info))

    print(f"Started a new game thread for {len(players)} players. Game ID: {game_id}")

    # Start a new thread to run the game, passing the players, rounds, and game_id
    game_thread = threading.Thread(target=play_game, args=(players, rounds, game_id))
    game_thread.daemon = True  # Make the thread exit when the main program exits
    game_thread.start()  # Start the game thread


def format_message(player_name, player_hands, top_of_discard_stack, visible_cards):
    # Begin formatting the message with the player's cards
    message = "\nYour cards:\n"
    player_hand = player_hands[player_name]
    # Format the player's own hand, showing which cards are visible
    message += format_hand(player_hand, visible_cards[player_name]) + "\n"
    
    # Format the hands of other players, showing only the visible cards
    for other_player, hand in player_hands.items():
        if other_player != player_name:
            message += f"{other_player}'s cards:\n"
            message += format_hand(hand, visible_cards[other_player]) + "\n"
    
    # Add the top card of the discard stack to the message
    message += "Discard Stack:\n"
    message += get_card(top_of_discard_stack) + "\n"  # Show only the top card
    return message  # Return the formatted message for the player


def format_hand(hand, visible):
    # Function to format the player's hand by showing visible cards and hiding non-visible ones
    hand_str = ""
    for i, card in enumerate(hand):
        if visible[i]:
            # If the card is visible, display it
            hand_str += f"{get_card(card)}  "
        else:
            # If the card is not visible, hide it with '***'
            hand_str += "***  "
        # Add a newline after every third card for formatting
        if (i + 1) % 3 == 0:
            hand_str += "\n"
    return hand_str  # Return the formatted hand


def end_game_logic(game_info, game_id):
    global udp_socket
    players = game_info["players"]
    player_hands = game_info["game_state"]["player_hands"]
    visible_cards = game_info["game_state"]["visible_cards"]
    player_name = players[0][0]  # The player who started the game

    # Make all cards visible at the end of the game
    for player in players:
        visible_cards[player[0]] = [True] * 6

    # Send the final game state to all players
    for player in players:
        player_name, ipaddr, t_port, _ = player
        # Format the message with all cards visible and send it to the player
        message = format_message(player_name, player_hands, game_info["game_state"]["top_of_discard_stack"], visible_cards)
        send_message_to_all(game_info, message)

    # Calculate scores for each player, applying the pair rule for matching cards
    scores = {}
    for player_name, hand in player_hands.items():
        score = 0
        # Calculate score based on pairs: (1 & 4), (2 & 5), (3 & 6)
        pairs = [(0, 3), (1, 4), (2, 5)]
        for i, j in pairs:
            if get_card_number(hand[i]) == get_card_number(hand[j]):
                # If the pair matches, both cards contribute 0 to the score
                score += 0
            else:
                # Otherwise, add the values of the two cards
                score += get_card_value(hand[i]) + get_card_value(hand[j])
        scores[player_name] = score  # Store the player's score

    # Determine the player with the lowest score as the winner
    winner = min(scores, key=scores.get)

    # Send the final game results to all players, including the winner and scores
    for player in players:
        player_name, ipaddr, t_port, _ = player
        final_message = f"The winner is {winner}. Final scores:\n"
        for p, score in scores.items():
            final_message += f"{p}: {score} points\n"
        send_udp_message(ipaddr, t_port, final_message)

    # Notify all players that the game is over
    message = "Game over!"
    send_message_to_all(game_info, message)

    # Remove all game data and players from the tracking lists
    remove_game_data(players[0][0])  # Use the player who started the game to remove data

    # Return to the UDP server listening state after the game ends
    print(f"Game started by '{players[0][0]}' ended. Returning to UDP server listening state.")
    udp_server(udp_socket)


def remove_game_data(player_name):
    global player_game_map, game_registry, game_identifier

    # Construct the game name based on the player who started it (e.g., "player_name's Game")
    game_name = f"{player_name}'s Game"

    # Find the game in game_registry using the player who started it
    game_to_remove = next((game for game in game_registry if game[1]["players"][0][0] == player_name), None)

    if not game_to_remove:
        print(f"No game found for player '{player_name}'.")
        return

    game_id = game_to_remove[0]  # Extract the game ID for the game to be removed

    print(f"Removing game with ID {game_id} started by '{player_name}'.")

    # Remove all players associated with the game from player_game_map
    player_game_map_before = list(player_game_map)
    player_game_map = [entry for entry in player_game_map if entry[1] != game_id]
    print(f"Player game map before: {player_game_map_before}")
    print(f"Player game map after: {player_game_map}")

    # Remove the game from game_registry using the game ID
    game_registry_before = list(game_registry)
    game_registry = [game for game in game_registry if game[0] != game_id]
    print(f"Game registry before: {game_registry_before}")
    print(f"Game registry after: {game_registry}")

    # Remove the game from game_identifier using the game name
    game_identifier_before = list(game_identifier)
    game_identifier = [entry for entry in game_identifier if entry["name"] != game_name]
    print(f"Game identifier before: {game_identifier_before}")
    print(f"Game identifier after: {game_identifier}")

    print(f"Game '{game_name}' and all associated player data have been removed.")


def get_card_number(card):
    # Extracts the card number based on its rank in the deck (Ace=1, ..., King=13)
    number = (card - 1) % 13 + 1  # Card numbers: 1 (Ace), 2, 3, ..., 11 (Jack), 12 (Queen), 13 (King)
    return number  # Return the card number based on its rank


def send_udp_message(ipaddr, port, message):
    # Function to send a UDP message to a specific IP address and port
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  # Create a UDP socket
    sock.sendto(message.encode(), (ipaddr, int(port)))  # Send the message after encoding it
    sock.close()  # Close the socket after sending

# Corrected function to send a message to all players in the game
def send_message_to_all(game_info, message):
    # Loop through all players in the game and send the message
    for player in game_info["players"]:
        player_ip, player_port = player[1], player[2]
        send_udp_message(player_ip, int(player_port), message)  # Use send_udp_message to send to each player

def de_register(client_ip, client_port, input_string):
    global player_group
    
    # Remove the '<' and '>' from input_string to extract the player's name
    player_name = input_string.strip('<>').strip()
    
    # Find the player by their name in the player_group
    player_found = None
    for player_tuple in player_group:
        if player_tuple[0] == player_name:  # Compare the player's name with input
            player_found = player_tuple
            break
    
    # If the player is found, remove them from the player_group
    if player_found:
        player_group.remove(player_found)  # Remove the player from the list
        print(f"Player {player_name} has been de-registered.")
        
        # Send a termination message to the client who requested the de-registration
        return_message = 'terminate'
        send_message(client_ip, client_port, return_message)  # Send the termination message
        print(f"Sent termination message to {client_ip}:{client_port}")
    else:
        # If the player is not found in the group, print an error message
        print(f"Player {player_name} not found. No action taken.")

# Function to query the currently registered players
def query_players(client_ip, client_port):
    global player_group
    
    # If there are no players registered, send a message indicating that
    if not player_group:
        send_message(client_ip, client_port, "No players currently registered.")
        return

    # Construct a message that lists all the players and their connection details
    player_info_message = ""
    for index, player in enumerate(player_group):
        player_name, ip, t_port, p_port = player  # Unpack player information
        player_info_message += f"{player_name} {ip} {p_port}\n"  # Add each player's info to the message

    # Send the complete list of players back to the client
    send_message(client_ip, client_port, player_info_message.strip())

# Function to query the current game statuses and return the details to the client
def query_games(client_ip, client_port):
    global game_identifier
    
    # If there are no games available, send a message indicating that
    if not game_identifier:
        message = "No games currently available."
        send_message(client_ip, client_port, message)
        return

    # Construct a message that lists all available games and their statuses
    game_info_message = ""
    for game in game_identifier:
        game_index = game["index"]
        game_name = game["name"]
        players_needed = game["players_needed"]
        rounds = game["rounds"]
        ongoing = game["ongoing"]

        # If the game is still in the waiting room, provide the details
        if not ongoing:
            game_info_message += (f"{game_index}. {game_name} is in the waiting room, {rounds} "
                                  f"round(s) will be played and {players_needed} more "
                                  "player(s) are needed.\n")
        else:
            # If the game has started, indicate that it is ongoing
            game_info_message += f"{game_index}. {game_name} is being played.\n"
    
    # Send the list of games back to the client
    send_message(client_ip, client_port, game_info_message.strip())
# Function to send a message to a specific IP and port using UDP
def send_message(ip, port, message):
    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  # Create a UDP socket
    udp_socket.sendto(message.encode(), (ip, int(port)))  # Send the message after encoding it

# Function to validate if the given string is a valid IPv4 address
def is_valid_ipv4(ip):
    """Validate if the given string is a valid IPv4 address in the format x.x.x.x where x < 256."""
    parts = ip.split('.')  # Split the string by periods (.)
    if len(parts) != 4:  # IPv4 addresses should have 4 parts
        return False
    for part in parts:
        try:
            # Check if each part is an integer between 0 and 255
            if not 0 <= int(part) < 256:
                return False
        except ValueError:
            return False  # If it's not a valid number, return False
    return True  # If all parts are valid, return True

# Function to calculate the value of a card based on its number
def get_card_value(card_number):
    # Determine the card's rank (1 to 13, where 1 is Ace, 13 is King)
    card_rank = (card_number - 1) % 13 + 1  # Mod 13 gives us ranks for cards

    # Return the corresponding card value
    if card_rank == 1:  # Ace has a value of -1
        return -1
    elif card_rank == 2:  # 2 has a value of -2
        return -2
    elif card_rank == 3:  # 3 has a value of 3
        return 3
    elif card_rank == 4:  # 4 has a value of 4
        return 4
    elif card_rank == 5:  # 5 has a value of 5
        return 5
    elif card_rank == 6:  # 6 has a value of 6
        return 6
    elif card_rank == 7:  # 7 has a value of 7
        return 7
    elif card_rank == 8:  # 8 has a value of 8
        return 8
    elif card_rank == 9:  # 9 has a value of 9
        return 9
    elif card_rank == 10:  # 10, J, Q have a value of 10
        return 10
    elif card_rank == 11:  # Jack has a value of 10
        return 10
    elif card_rank == 12:  # Queen has a value of 10
        return 10
    elif card_rank == 13:  # King has a value of 0
        return 0
    return 0  # Default return 0 for any other invalid values

# Function to generate a mapping of card numbers to card strings
def generate_card_mapping():
    # Define the possible ranks and suits for cards
    ranks = ['A','2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K']
    suits = ['S', 'H', 'D', 'C']  # Suits: Spades, Hearts, Diamonds, Clubs
    
    # Initialize the dictionary to map card numbers to card strings
    card_map = {}
    
    # Start the card index from 1 (Ace of Spades is card 1)
    index = 1
    
    # Loop through suits and ranks to assign each card a string representation
    for suit in suits:
        for rank in ranks:
            card_string = rank + suit  # Create the card string (e.g., "AS" for Ace of Spades)
            card_map[index] = card_string  # Map the card index to its string representation
            index += 1  # Increment the index for the next card
    
    return card_map  # Return the complete mapping

# Function to get a card string (e.g., "AS") based on its number (1 to 52)
def get_card(number):
    # Check if the card number is valid (between 1 and 52)
    if number < 1 or number > 52:
        return "Invalid card number. Please enter a number between 1 and 52."
    
    # Generate the card mapping
    card_map = generate_card_mapping()
    
    # Return the corresponding card string for the given number
    return card_map[number]


if __name__ == "__main__":
    card_map = generate_card_mapping()  # Generate card map on startup
    server_ip = input("Enter ip_address here: ")  # Ask for the server IP address
    server_port = 32001  # Set the server port
    
    # Create a UDP socket for the server
    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    # Bind the socket to the server IP and port
    udp_socket.bind((server_ip, server_port))
    
    # Start the UDP server to listen for incoming messages
    udp_server(udp_socket)
