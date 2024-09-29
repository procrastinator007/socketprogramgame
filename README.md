# socketprogramgame
group 63 -> Jai Patel
Port number range : 32000,32499

Process of writing Tracker.py

once you recieve message from the client side try reading the string till the first < make a record of it and if it equals to string 'register'  then launch register function with an input string starting with the first  < . if it equals to string 'start game'  then launch start game function with an input string starting with the first  < . if it equals to string 'end'  then launch register function with an input string starting with the first  < . if it equals to string 'de-register'  then launch register function with an input string starting with the first  < .  if there is no < then read the entire message if it equals 'query players' or 'query games' then respectively launch the function respectively without any input  else throw an error in valid input. 

lets create a function called start game that takes in three inputs: client_ip client_port and input_string.  just like register split input string into three parts first take in <player>, then <n> being number of players in the game. third being number of rounds <#holes> split the values into seperate variables check if <player> == <player> in the global array of tuples containing {player, ip, t-port, p-port}. if it does not the send a return message via the client ip and and client port to the client saying you are not registered with that name, try again and throws you out of the function. but if the player is found in the array of tuple then check next variable <n> to be it the range of 2<= x<=4. if it does not then throw an error message to user by retrieving t-port and ip associated with the player in the global variable. if it does then check <#holes> to be in the range 1<= x<=9 or -1; if it is -1 then update the variable to 9. if the #holes are beyond 9 or 0 or any other int thats not in the domain then if it does not then throw an error message to user by retrieving t-port and ip associated with the player.  if the three variables from input strings pass the test then append the global array of tuples game_identifier in the format {<index>, <name> ,<number of players in game>, <players needed>, <rounds> <ongoing>} . <index> being the position in game_identifier it is being appended to. <name> will be a string that says "<player>'s Game" <number of players in game> is 2 tuple pointer array {<index>, <player>} index is set to 1, and player point to a specific tuple in <player_group> and length of this 2-tuple array is finite and determined by players needed so if input of <n> was 2 then length of array will be 2 to have to players in the game. the number of empty tuples will determine <players needed> and if the array is full then <ongoing> will be a boolean initialised to false. once game identifier is appended.<rounds> being equal to <#holes>. you send us to a function waiting room. waiting room runs infinitely till it sends true. then you send us to a function play game. runs infinitily till it returns true. then you send us to end game.

create a function query players, to query the games currently ongoing. 
This command returns a message to the client that requested the function to server. the message  is a long string that should retrived from the global variable player_group = []  # Contains tuples like {player, ip, t-port, p-port}. But you need to print the entire list in the message in the format :  
player0 IP-addr0 p-port0
player1 IP-addr1 p-port1
player2 IP-addr2 p-port2
playern IP-addrn p-portn

write a function query_games that retrieves from game identifier : 
game_entry
{ "index": game_index,
        "name": game_name,
        "players": players_array,
        "players_needed": n - 1,  # Players still needed to start
        "rounds": holes,
        "ongoing": False
}
split the data into a string that prints all the game_entries:
for example game_indentifier[1]
1. "name" is in waiting room, "rounds" will be played and "player_needed" more are needed (if ongoing == false)
else
1. "name" is being played. (ongoing == true)
make sure to go through all game entries and print all the games in the game identifier

write a function join game on the server side has a string formatted input "<player> <game_index>". strip off <> and store game index in an int variable and player in a string variable. use game index to retrieve the tuple that it is assigned to in the global array game_indentifier with the structure: players_array = [(1, registered_player)]  # Initially one player with index 1
    # Game tuple: {<index>, <name>, <number of players in game>, <players needed>, <rounds>, <ongoing>}
    game_entry = {
        "index": game_index,
        "name": game_name,
        "players": players_array,
        "players_needed": n - 1,  # Players still needed to start
        "rounds": holes,
        "ongoing": False  # Initially set to False
    }
use player name to retrieve its associated value from a global array of 4-tuple named: player_group = []  # Contains tuples like {player, ip, t-port, p-port}. once you copy the tuple on a temp variable append it in the players_array. decrement the players needed; if players needed == 0 then switch ongoing to true. update the game identifier array. exit the function and enter the function play game.  elif players needed =! 0 then let ongoing be false update game identifier exit the function and enter waiting_room function. 

write a function de-register with an input named clientip and clientport and input_string that in the form <players> so you remove '< read the data and then remove >. take the message and look for it in the global array of tuples named player_group which has the following tuple {player, ip ,tport pport}. look for  the tuple by comparing player == message(<player> without the '<>'). once you find it delete the entry and update the global array. now take client ip and client port send a return message saying 'terminate' . 

Player.py : 
Create two separate sockets on the player side that randomly assign port numbers between the range of 32002 to 32499 and check if the port number is available. name one socket t-socket and the p-socket. and ports as t-port and p-port. retrive ip address from the system make sure the ip addr is same for both

create first layer, which should be visible as you launch player.py and it should look like:

Welcome!
BEFORE PLAYING PLEASE ESTABLISH CONNECTION.
-X-
this basically launches function register

the function register asks for your name; input is recorded if it is less than or equal to 15 characters or throws an error saying too long. Once the name is taken, a message is sent via the t-socket to port 32001 in this exact format: "register <name> <IPv4> <t-port> <p-port>" name is the input.  IPv4, t-port and p-port are the ones that we have assigned previously, so basically a message should look like "register <romeo> <124.234.0.1> <32005> <32454>." The puts the system into infinite listening mode till it recieves a message from the 32001 port. Print that message and move to the next function named startpage that should look like

What would you like to do today? Enter 1-5
1. Start a game of 6 card golf.
2. Join a game of 6 card gold.
3. See active players.
4. See active Games.
5. Exit

the choice is made == 1 so you launch a function called start game. It will take two inputs: number of players in the game 2<= x <=4 and another input being number of rounds or holes it needs to be in the range 1<= x<= 9. second input can be skipped if you just press enter that will set holes as -1 and that is acceptable. then you send a message to the server on the port 32001 "start game <player> <n> <#holes>" player is the name inputed at the very start which is a global variable.  n is the number of players and <# holes> is the second input so a sample message should look like == "start game <romeo> <3> <-1>" there should be exit interrupt command until you input value for holes (basically press escape to go back to previous page) this should throw you into startpage again.  once you input both the values it goes infinite loop of listening till a command from the server port interrupts. While it is in infinite loop of listening and user can have no inputs while in listening mode all it can do is just listen and execute commands from server side till it is asked for an input.
 print "waiting for players to join the game" 


