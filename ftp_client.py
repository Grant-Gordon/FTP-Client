from socket import socket, AF_INET, SOCK_STREAM
import argparse
import sys



def main():

#somehwere if SIGKILL/SIGINT call exit_gracefully(). 

    #init whats neccessary
    #Init PI socket (port 21)

    #user login

    #User input
    while(True):
        #get user input
        #case: PI command
        #   handle with PU socket
        #case: data transfer command
            #new thread with new DTP socket
            #ensure TPYE I/A
            #send command
            #read ASCII bytes from buffer while not EOF
            #kill socket and thread (dont worry about cold starts/keeping thread pools hot)
        #case: quit 
            # exit_gracefull()\
    



if __name__ == "__main__()":
    main()