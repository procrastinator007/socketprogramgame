# socketprogramgame
group 63 -> Jai Patel
Port number range : 32000,32499

6 Card Golf Game
This project implements a multiplayer 6-card golf game using Python sockets for communication between a central server (tracker) and multiple players.

Prerequisites
Python 3.x
A local network or a server to run the tracker and players.
Setup Instructions
1. Clone the repository
First, clone this repository and navigate to the project directory:

bash
Copy code
git clone <repository_url>
cd <project_directory>
2. Install Required Packages
Make sure you have the required packages installed. For basic socket communication, no external libraries are needed, but if any additional libraries are required, install them with:

bash
Copy code
pip install -r requirements.txt
Note: The default setup only requires Python's built-in socket library.

Running the Game
The game requires one tracker (server) and multiple players (clients) to be started.

1. Running the Tracker (Server)
The tracker is the central server that manages the game and coordinates the players.

Open a terminal.
Navigate to the directory containing tracker.py.
Run the tracker.py file as follows:
bash
Copy code
python3 tracker.py
Note: The server will start listening on the IP address and port specified when prompted. Make sure this server is accessible to the players over the network.

Example Tracker Input
The server will prompt for an IP address and port number for binding:
java
Copy code
Enter the server IP address: 192.168.0.1
Enter the server port (default 32001): 32001
2. Running the Player (Client)
Each player connects to the tracker to participate in the game.

Open a terminal.
Navigate to the directory containing player.py.
Run the player.py file as follows:
bash
Copy code
python3 player.py
Example Player Input
When starting the player, it will prompt for the following inputs:

IP Address: This is the player's own IP address, used to bind the socket.
Example: 192.168.0.2
Server IP: The IP address of the tracker server.
Example: 192.168.0.1
Registration: After entering the IP addresses, the player will register by entering a username.
Gameplay: The player can start, join, or view games from the menu.
Note: Each player must use a unique name when registering.

Example Player Input
less
Copy code
Enter your IP address: 192.168.0.2
Enter server IP address: 192.168.0.1
Please enter your name (max 15 characters): Alice
Once the player has successfully connected to the tracker, the menu will appear, allowing the player to start or join games.

Game Flow
Tracker Commands:
The tracker will manage the state of the game, keep track of active players, and coordinate rounds.

Player Commands:
Players can interact with the tracker using various commands such as swap, show, reveal, and pass. The commands are entered in the console during gameplay.

Notes:
Ensure that the tracker and players are on the same network for communication.
The server IP address must be reachable by all players.
Multiple players can join and play the game once the tracker is running.

