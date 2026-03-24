Notes for thermal printer http request server

You will need to get the IP address of the raspberry pi. Once it’s connected to the network, you should get a message containing 4 numbers separated by a dot. This is the IP_ADDRESS.

To run the script on a raspberry pi, load a terminal window, change the directory to the python file and type:

python3 http_test_1.py

Once the script starts running, use another computer and put this in the address bar: 

IP_ADDRESS:8080/?code=MESSAGE_TO_BE_PRINTED 

if everything works, the thermal printer should output the message from the other computer.

Hopefully you can edit the code to do what you need in terms of communicating with the bot. 
