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
    
    print(f"UDP server is listening on port {server_port}")

    udp_socket.close()

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
