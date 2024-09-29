import socket

# Global arrays
player_group = []  # Contains tuples like {player, ip, t-port, p-port}
game_identifier = []  # Stores ongoing game data


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
                    input_string = "<" + input_string
                    input_string = input_string.strip()  # Strip whitespace
                    
                    if command == "register":
                        register(input_string, client_ip)
                   # elif command == "start game" or command == "startgame":
                   #     start_game(client_ip, client_port, input_string,)
                   # elif command == "end":
                   #     end_game(input_string)
                    elif command == "de-register":
                        de_register(client_ip, client_port, input_string)
                    #elif command == "join game":
                     #   join_game(input_string)
                    else:
                        print("Invalid command.")
                else:
                    # No '<' in the message
                    if message == 'query players':
                        query_players(client_ip, client_port)
                    elif message == 'query games':
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
    global player_group
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

#def start_game(client_ip, client_port, input_string):
   # global player_group, game_identifier
    
    # Split the input_string into <player>, <n>, <#holes>
    #try:
    #    player, n_str, holes_str = input_string.split(',')
     #   player = player.strip().replace('<', '').replace('>', '')
      #  n = int(n_str.strip().replace('<', '').replace('>', ''))
       # holes = int(holes_str.strip().replace('<', '').replace('>', ''))
    #except ValueError:
     #   send_message(client_ip, client_port, "Invalid input format. Expected <player>,<n>,<#holes>.")
      #  return

    # Check if player is registered in the player_group
    #registered_player = None
    #for entry in player_group:
     #   if entry[0] == player:  # entry[0] is the player's name
      #      registered_player = entry
      #      break
    
    #if not registered_player:
     #   send_message(client_ip, client_port, "You are not registered with that name. Try again.")
     #   return

    # Check if the number of players is within the valid range (2 <= n <= 4)
    #if n < 2 or n > 4:
      #  send_message(registered_player[1], registered_player[2], "Invalid number of players. Must be between 2 and 4.")
     #   return

    # Check if the number of holes is in the range 1 <= holes <= 9, or set to 9 if -1
    #if holes == -1:
     #   holes = 9
    #elif holes < 1 or holes > 9:
      #  send_message(registered_player[1], registered_player[2], "Invalid number of holes. Must be between 1 and 9.")
     #   return

    # Append a new game entry to the game_identifier array
    #game_index = len(game_identifier)
    #game_name = f"{player}'s Game"
    
    # Create the player array {<index>, <player>}
    #players_array = [(1, registered_player)]  # Initially one player with index 1

    # Game tuple: {<index>, <name>, <number of players in game>, <players needed>, <rounds>, <ongoing>}
    #game_entry = {
        #"index": game_index,
        #"name": game_name,
        #"players": players_array,
       # "players_needed": n - 1,  # Players still needed to start
      #  "rounds": holes,
     #   "ongoing": False  # Initially set to False
    #}

    #game_identifier.append(game_entry)
    
    #print(f"Game '{game_name}' created with {n} players and {holes} rounds.")

    # Go to waiting room, then play game, then end game
    #waiting_room()
    #    if play_game():
     #       end_game()

# join game has a formatted input of join game <player> <game_index>
#def join_game(message):
 #   global game_identifier, player_group
    
    # Split the input message to get player and game_index
  #  stripped_message = message.strip('<>').strip()
   # player_name, game_index_str = stripped_message.split()
    
    #game_index = int(game_index_str)  # Convert game_index to an integer

    # Retrieve the game entry using the game_index
    #game_entry = next((game for game in game_identifier if game["index"] == game_index), None)

    #if game_entry is None:
     #   print(f"Game with index {game_index} not found.")
      #  return  # Game not found, exit function
    
    # Find the player details in player_group
    #player_details = next((player for player in player_group if player[0] == player_name), None)
    
    #if player_details is None:
     #   print(f"Player {player_name} is not registered.")
     #   return  # Player not registered, exit function
    
    # Copy the player details into a temp variable
    #temp_player = player_details  # This is a tuple (player, ip, t-port, p-port)
    
    # Append the player to the players_array of the game_entry
    #game_entry["players"].append((len(game_entry["players"]) + 1, temp_player))  # Using the next index for player
    #game_entry["players_needed"] -= 1  # Decrement players needed
    
    # Check if players_needed is now 0
    #if game_entry["players_needed"] == 0:
     #   game_entry["ongoing"] = True  # Set ongoing to true
    
    # Update the game_identifier array (not strictly necessary unless you want to maintain a reference)
    #for i in range(len(game_identifier)):
     #   if game_identifier[i]["index"] == game_index:
      #      game_identifier[i] = game_entry  # Update the game entry in the identifier array

    # If the game is now ongoing, proceed to play game; otherwise, wait in the waiting room
    #if game_entry["ongoing"]:
     #   play_game(game_entry)
    #else:
      #  waiting_room()
####
##
#
#
#
#def waiting_room():    
   # print("teri maa ki chut")

#def end_game(input_string):
    #print(f"Ending game with: {input_string}")

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
        send_message(client_ip, client_port, "No games currently available.")
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
    udp_socket.sendto(message.encode(), (ip, port))

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
#def generate_card_mapping():
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
    
    #return card_map

# Function to get a card string based on the number (1 to 52)
#def get_card(number):
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
