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
game_registry = []  # Tracks game_id -> {thread, players, game_state}
player_game_map = []  # Tracks player (IP, port) -> game_id
revealed =False

#creating a UDP socket to recieve data

def process_client_request(message, client_ip, client_port):
    # Process client request once and then break out of the loop
    try:
        if 32002 <= client_port <= 32499:
            print("decoding data")
                # Processing the message
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
    # The function will automatically return after processing the request


def udp_server(udp_socket):
    global player_game_map
    print("Listening for incoming client requests...")

    while True:
        try:
            # Receive data from clients
            data, client_address = udp_socket.recvfrom(1024)
            client_ip, client_port = client_address
            message = data.decode()

            # Cast client_port to string for comparison with player_game_map
            client_port_str = str(client_port)

            print(f"Received message from {client_ip}:{client_port} - {message}")
            print("Current player_game_map:", player_game_map)

            # Check if the player is already registered in a game
            if any((client_ip, client_port_str) == player_info for player_info, _ in player_game_map):
                # Find the correct game_id for the player
                game_id = next(game_id for player_info, game_id in player_game_map if player_info == (client_ip, client_port_str))
                
                # Retrieve game_info from game_registry
                game_info = next(info for id, info in game_registry if id == game_id)  # Extract game_info from the tuple
                print("game info:", game_info)
                if game_info:
                    # Route the message to the correct game thread
                    handle_game_action(game_info, message, client_ip, client_port)
                else:
                    print(f"Game ID {game_id} not found.")

            else:
                # Cast client_port back to int for process_client_request
                client_port = int(client_port)
                # Handle new registrations, starting new games, etc.
                process_client_request(message, client_ip, client_port)

        except KeyboardInterrupt:
            print("\nServer shutting down.")
            break

    udp_socket.close()


def handle_game_action(game_info, action, client_ip, client_port):
    player_name = next((p[0] for p in game_info["players"] if p[1] == client_ip and str(p[2]) == str(client_port)), None)
    print(player_name)
    if player_name:
        if "reveal" in action:
            handle_reveal_action(game_info, player_name, action)
        elif "swap" in action:
            handle_swap_action(game_info, player_name, action)
        elif "show" in action:
            handle_show_and_pass_action(game_info, player_name)
    else:
        print(f"Unknown player {client_ip}:{client_port} attempted to take an action.")


# Handles the reveal action in the game
def handle_reveal_action(game_info, player_name, action):
    print("entering reveal action ")
    try:
        # Extract the card positions from the action string
        first_card, second_card = map(int, action.split()[1:3])  # Convert to integers

        # Update the visible cards in the game state for the player
        game_info["game_state"]["visible_cards"][player_name][first_card - 1] = True
        game_info["game_state"]["visible_cards"][player_name][second_card - 1] = True

        # Get the top card of the discard stack (not the entire discard stack)
        top_of_discard_stack = game_info["game_state"]["top_of_discard_stack"]

        # Prepare the message showing the updated game state for all players
        for player in game_info["players"]:
            player_ip, player_port = player[1], player[2]
            message = format_message(player_name, game_info["game_state"]["player_hands"], 
                                     top_of_discard_stack,  # Use top card instead of discard stack
                                     game_info["game_state"]["visible_cards"])
            send_udp_message(player_ip, int(player_port), message)

        # Proceed to the next player
        process_next_player(game_info)
    except (ValueError, IndexError) as e:
        print(f"Error processing reveal action: {e}")


# Handles the swap action in the game
def handle_show_and_pass_action(game_info, player_name):
    discard_stack = game_info["game_state"]["discard_stack"]

    # Show: Remove the top card from the discard stack permanently
    if discard_stack:
        discarded_card = discard_stack.pop(0)  # Remove the top card from the discard stack
        print(f"{player_name} removed card {discarded_card} from the discard stack.")

    # Now, the next card becomes the new top of the discard stack, visible to all players
    top_of_discard_stack = game_info["game_state"]["top_of_discard_stack"] = discard_stack[0] if discard_stack else None

    # Prepare the message showing the updated game state for all players
    for player in game_info["players"]:
        player_ip, player_port = player[1], player[2]
        message = format_message(player_name, game_info["game_state"]["player_hands"], 
                                 top_of_discard_stack, 
                                 game_info["game_state"]["visible_cards"])
        send_udp_message(player_ip, int(player_port), message)

    # After showing, the current player must either swap the new top of the discard stack or pass
    previous_player_index = game_info["game_state"]["current_player"] - 1
    if previous_player_index < 0:
        previous_player_index = len(game_info["players"]) - 1  # Wrap around to the last player

    previous_player = game_info["players"][previous_player_index]
    previous_player_ip, previous_player_port = previous_player[1], previous_player[2]

    # Prompt the previous player for a swap or pass action
    send_udp_message(previous_player_ip, int(previous_player_port),"Your turn! You must now swap the top of the discard stack with one of your cards or pass.")

    # Allow the player to pass after showing
    game_info["game_state"]["can_pass"] = True


def handle_swap_action(game_info, player_name, action):
    discard_stack = game_info["game_state"]["discard_stack"]
    player_hands = game_info["game_state"]["player_hands"]

    if "swap" in action and len(action.split()) == 3:
        card_position = int(action.split()[2]) - 1  # swap top <index>
        
        # Swap the player's card with the top of the discard stack
        player_hands[player_name][card_position], discard_stack[0] = discard_stack[0], player_hands[player_name][card_position]
        game_info["game_state"]["visible_cards"][player_name][card_position] = True

        # Prepare the message showing the updated game state for all players
        for player in game_info["players"]:
            player_ip, player_port = player[1], player[2]
            message = format_message(player_name, game_info["game_state"]["player_hands"], 
                                     discard_stack[0],  # Now, top card only
                                     game_info["game_state"]["visible_cards"])
            send_udp_message(player_ip, int(player_port), message)

        # Proceed to the next player after the swap
        process_next_player(game_info)
    
    elif "pass" in action and game_info["game_state"].get("can_pass", False):
        handle_pass_action(game_info, player_name)

    else:
        # If pass is not allowed, send a message to the player
        send_udp_message(game_info["players"][game_info["game_state"]["current_player"]][1],
                         int(game_info["players"][game_info["game_state"]["current_player"]][2]),
                         "You cannot pass without first showing the discard stack.")


def handle_pass_action(game_info, player_name):
    # Since the player chooses to pass, no cards are swapped
    # Prepare the message showing the updated game state for all players
    discard_stack = game_info["game_state"]["discard_stack"]
    
    for player in game_info["players"]:
        player_ip, player_port = player[1], player[2]
        message = format_message(player_name, game_info["game_state"]["player_hands"], 
                                 discard_stack[0],  # Pass will still keep the top card visible
                                 game_info["game_state"]["visible_cards"])
        send_udp_message(player_ip, int(player_port), message)

    # Proceed to the next player after the pass
    process_next_player(game_info)


def process_next_player(game_info):
    players = game_info["players"]
    round_count = game_info["game_state"]["round"]

    # Check if all the cards of the previous player (current_player - 1) are visible
    previous_player_index = (game_info["game_state"]["current_player"] - 1) % len(players)
    previous_player = players[previous_player_index]
    previous_player_name = previous_player[0]

    # If all cards of the previous player are visible, make the current round the final round
    if all(game_info["game_state"]["visible_cards"][previous_player_name]):
        print(f"All cards of {previous_player_name} are visible. Ending the game after this round.")
        game_info["game_state"]["round"] = game_info["rounds"]  # Set the current round as the final round

    # Check if the game has exceeded the allowed number of rounds
    if round_count >= game_info["rounds"]:
        end_game_logic(players, game_info["game_state"]["player_hands"], game_info["game_state"]["visible_cards"], game_info["game_id"])
    else:
        # Move to the next player
        current_player = players[game_info["game_state"]["current_player"]]
        player_name, ipaddr, t_port, _ = current_player
        game_info["game_state"]["current_player"] += 1

        # Notify all other players to wait while the current player takes their turn
        for player in players:
            other_ip, other_port = player[1], player[2]
            if player != current_player:
                print(f"Sending 'Please wait' to {other_ip}:{other_port}")
                send_udp_message(other_ip, int(other_port), "Please wait for your turn.")

        # If it's the first round, ask the player to reveal two cards
        if round_count == 0:
            print(f"Sending 'Please reveal two cards' to {ipaddr}:{t_port}")
            send_udp_message(ipaddr, int(t_port), "Please reveal two cards by sending the 'reveal <card1> <card2>' command.")
        else:
            # Subsequent rounds: Ask the player to swap or pass
            print(f"Sending 'Your turn' to {ipaddr}:{t_port}")
            send_udp_message(ipaddr, int(t_port), "Your turn! You can 'swap top <index>' or 'pass' or 'show'.")



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
    
    # Add player tuple to the temp_players_array with all four values 
    temp_players_array = [(registered_player[0], registered_player[1], registered_player[2], registered_player[3])]

    
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
def join_game(input_string):
    global game_identifier, player_group
    
    # Debugging: Print the raw input string to see its contents
    print(f"Raw input_string: {input_string}")
    
    try:
        # Split the input message to get player and game_index, ensuring proper parsing
        stripped_message = input_string.replace('<', '').replace('>', '').strip()
        print(f"Stripped message: {stripped_message}")  # Debugging
        
        player_name, game_index_str = stripped_message.split()
        game_index = int(game_index_str)  # Convert game_index to an integer
        
        print(f"Player Name: {player_name}, Game Index: {game_index}")
        
    except ValueError as e:
        print(f"Error converting game_index_str to int: {e}")
        return  # Handle error accordingly

    # Retrieve the game entry using the game_index
    game_entry = next((game for game in game_identifier if game["index"] == game_index), None)

    if game_entry is None:
        print(f"Game with index {game_index} not found.")
        return  # Game not found, exit function
    
    # Find the player details in player_group
    player_details = next((player for player in player_group if player[0] == player_name), None)
    
    if player_details is None:
        print(f"Player {player_name} is not registered.")
        return  # Player not registered, exit function
    
    # Add the player to the game entry in the correct tuple format (name, ip, t-port, p-port)
    temp_player = (player_details[0], player_details[1], player_details[2], player_details[3])
    game_entry["players"].append(temp_player)
    game_entry["players_needed"] -= 1  # Decrement players needed
    
    # Update the game_identifier array (not strictly necessary unless you want to maintain a reference)
    for i in range(len(game_identifier)):
        if game_identifier[i]["index"] == game_index:
            game_identifier[i] = game_entry  # Update the game entry in the identifier array

    print(f"Player {player_name} has joined game {game_index}.")
    waiting_room(game_entry)



def waiting_room(game_entry):
    global udp_socket
    print(f"Entering waiting room for {game_entry['name']}...")
    
    # Check if the game is still waiting for players
    if game_entry["players_needed"] > 0:
        # Notify all players that the game is still waiting for more players
        for player_tuple in game_entry["players"]:
            if len(player_tuple) < 3:
                print(f"Error: Player tuple does not have enough elements: {player_tuple}")
                continue

            player_ip, player_port = player_tuple[1], player_tuple[2]
            send_message(player_ip, player_port, "Still waiting for more players...")
        
        print(f"Still waiting for players to join {game_entry['name']}. Players needed: {game_entry['players_needed']}")
        udp_server(udp_socket)  # Return back to udp_server() to keep listening for more players

    else:
        # Start the game if enough players have joined
        game_entry["ongoing"] = True
        print(f"Starting game: {game_entry['name']}")
        
        # Notify all players that the game is starting
        for player_tuple in game_entry["players"]:
            if len(player_tuple) < 3:
                print(f"Error: Player tuple does not have enough elements: {player_tuple}")
                continue

            player_ip, player_port = player_tuple[1], player_tuple[2]
            send_message(player_ip, player_port, "Game_started")
        
        # Extract player IPs for the game and start the game
        temp_player_group = [player_tuple for player_tuple in game_entry["players"] if len(player_tuple) >= 3]
        start_game_thread(temp_player_group, game_entry["rounds"])

    # After the game starts or while waiting, return to listening for new clients
    udp_server(udp_socket)

        
def play_game(players, rounds, game_id):
    global game_registry  # Access the global game_registry

    # Create a deck of cards and shuffle
    deck = list(range(1, 53))
    random.shuffle(deck)

    # Assign 6 cards to each player directly from the deck and remove them as we go
    player_hands = {}
    for player in players:
        hand = [deck.pop(0) for _ in range(6)]  # Take 6 cards from the deck
        player_hands[player[0]] = hand

    # The top card is the first card from the remaining deck
    top_of_discard_stack = deck.pop(0)

    # The remaining cards form the discard stack
    discard_stack = deck

    visible_cards = {player[0]: [False] * 6 for player in players}

    game_state = {
        "player_hands": player_hands,
        "top_of_discard_stack": top_of_discard_stack,
        "discard_stack": discard_stack,
        "visible_cards": visible_cards,
        "round": 0,
        "current_player": 0
    }

    # Send initial hands and wait for reveals
    for player in players:
        player_name, ipaddr, t_port, _ = player
        message = format_message(player_name, player_hands, top_of_discard_stack, visible_cards)
        send_udp_message(ipaddr, int(t_port), message)

    # Update the game_state in the game_registry
    for i, (gid, info) in enumerate(game_registry):
        if gid == game_id:
            game_registry[i][1]["game_state"] = game_state  # Update game_state in registry

    print(f"Game info after initialization: {game_registry}")

    # Sequentially ask players to reveal their cards
    process_next_player(game_registry[i][1])  # Use the updated game_info with game_state



def start_game_thread(players, rounds):
    global player_game_map
    global game_registry
    game_id = random.randint(1000, 9999)  # Generate a unique game ID

    # Update the player_game_map to associate each player with the game
    for player in players:
        player_ip = player[1]
        player_port = str(player[2])  # Store port as a string for easier comparison
        player_game_map.append(((player_ip, player_port), game_id))

    print(f"player_game_map after update: {player_game_map}")

    # Append the new game info to game_registry as a tuple (game_id, game_info)
    game_info = {
        "players": players,
        "rounds": rounds,
        "game_state": None  # game_state will be fully initialized in play_game
    }
    game_registry.append((game_id, game_info))

    print(f"Started a new game thread for {len(players)} players. Game ID: {game_id}")

    # Create and start the game thread, passing in the game_id to update the correct game
    game_thread = threading.Thread(target=play_game, args=(players, rounds, game_id))
    game_thread.daemon = True  # Allow the thread to exit when the main program exits
    game_thread.start()



def format_message(player_name, player_hands, top_of_discard_stack, visible_cards):
    message = "\nYour cards:\n"
    player_hand = player_hands[player_name]
    message += format_hand(player_hand, visible_cards[player_name]) + "\n"
    
    for other_player, hand in player_hands.items():
        if other_player != player_name:
            message += f"{other_player}'s cards:\n"
            message += format_hand(hand, visible_cards[other_player]) + "\n"
    
    message += "Discard Stack:\n"
    message += get_card(top_of_discard_stack) + "\n"  # Show only the top card
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


def end_game_logic(players, player_hands, visible_cards, game_id):
    global udp_socket
    # Make all cards visible
    for player in players:
        visible_cards[player[0]] = [True] * 6

    # Send final game state to all players
    for player in players:
        player_name, ipaddr, t_port, _ = player
        message = format_message(player_name, player_hands, None, visible_cards)  # No discard stack after game ends
        send_udp_message(ipaddr, int(t_port), message)

    # Calculate scores
    scores = {}
    for player_name, hand in player_hands.items():
        score = 0
        for i, card in enumerate(hand):
            card_value = get_card_value(card)
            if i < 3 and hand[i] == hand[i + 3]:  # Check for pairs in positions (1 and 4), (2 and 5), (3 and 6)
                score += 0  # Pair rule: both cards become zero
            else:
                score += card_value
        scores[player_name] = score

    # Find the player with the lowest score
    winner = min(scores, key=scores.get)

    # Send the game result to all players
    for player in players:
        player_name, ipaddr, t_port, _ = player
        final_message = f"Game over! The winner is {winner}. Final scores:\n"
        for p, score in scores.items():
            final_message += f"{p}: {score} points\n"
        send_udp_message(ipaddr, int(t_port), final_message)

    # Remove game data from all tracking lists
    remove_game_data(game_id)

    # Return to UDP server listening state
    print(f"Game {game_id} ended. Returning to UDP server listening state.")
    udp_server(udp_socket)

def remove_game_data(game_id):
    global game_registry, player_game_map, game_identifier

    # Remove game from game_registry
    game_registry = [game for game in game_registry if game[0] != game_id]

    # Remove game from player_game_map
    player_game_map = [entry for entry in player_game_map if entry[1] != game_id]

    # Remove game from game_identifier if it exists
    game_identifier = [game for game in game_identifier if game["index"] != game_id]

    print(f"Game ID {game_id} has been removed from all data structures.")

def send_udp_message(ipaddr, port, message):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.sendto(message.encode(), (ipaddr, int(port)))  # Ensure port is int here
    sock.close()


def send_message_to_all(game_info, message):
    for player in game_info["players"]:
        player_ip, player_port = player[1], player[2]
        send_udp_message(player_ip, int(player_port), message)

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


def get_card_value(card_number):
    # Calculate the card value based on the given card number
    card_rank = (card_number - 1) % 13 + 1  # Card rank from 1 to 13 (A, 2, 3, ..., K)
    
    if card_rank == 1:  # Ace
        return -1
    elif card_rank == 2:  # 2
        return -2
    elif card_rank == 3:  # 3
        return 3
    elif card_rank == 4:  # 4
        return 4
    elif card_rank == 5:  # 5
        return 5
    elif card_rank == 6:  # 6
        return 6
    elif card_rank == 7:  # 7
        return 7
    elif card_rank == 8:  # 8
        return 8
    elif card_rank == 9:  # 9
        return 9
    elif card_rank == 10:  # 10, J, Q
        return 10
    elif card_rank == 11:  # J
        return 10
    elif card_rank == 12:  # Q
        return 10
    elif card_rank == 13:  # K
        return 0
    return 0


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
