#ftp_client.py
import ftp_utils as utils
import ftp_command_functions as cmds
from typing import Tuple, Dict, Optional

from socket import socket, AF_INET, SOCK_STREAM, timeout


def main():

    # It shall support the following user commands
    # open xxx.yyy.zzz: Connect to a remote FTP server and necessary user authentication
    # dir or ls: Show list of remote files
    # cd: Change current directory on the remote host
    # get xxxxx Download file xxxxx from the remote host
    # put yyyyy Upload file yyyyy to the remote host
    # close terminate the current FTP session, but keep your program running
    # quit terminate both the current FTP session and your program.
#
    print("In main")
    PI_socket = None
    session_open = False

    while(True):
        user_input = input("ftp> (type 'open <host>' or 'help' or 'quit'): ").strip()
        if not user_input:
            continue
        cmd, args = utils.normalize_inputs(user_input)
        if cmd == "help":
            print("Commands available before connecting:")
            print("  open <host>  - connect to a remote FTP server")
            print("  quit         - exit the program")
            print("Once connected, additional commands (ls, cd, get, put, close) become available.\n")
        elif cmd == "quit":
            print("Exiting FTP client")
            return
        elif cmd == "open":
            if not args:
                print("Usage: open <xxx.yyy.zzz>")
                continue
            PI_socket, session_open = cmds.open(args[0])
            if session_open:
                print(f"Connected to {args[0]}")
                break
            else:
                print(f"Failed to connect or authenticate with {args[0]}. Try again.\n")
        else:
            print("Invalid command. Type 'help' for usage information.")

    while(True):
        user_input = input("\nFor usage type: help:\n")
        cmd, args = utils.normalize_inputs(user_input)

        match cmd:
            case "help" | "h" | "usage":
                print("available Comands:")
                print("  ls | dir                 - list remote directory")
                print("  cd <path>                - change remote directory")
                print("  get <remote> [local]     - download file")
                print("  put <local> [remote]     - upload file")
                print("  close                    - close current FTP session")
                print("  quit                     - exit program")
            case "ls" | "dir":
                cmds.ls(PI_socket)
            case "cd":
                cmds.cd(PI_socket, args)
            case "get":
                cmds.get(PI_socket, args[0], args[1])
            case "put":
                cmds.put(PI_socket, args[0], args[1])
            case "close":
                if session_open==False:
                    print("No session is opon. Cannot close. ")
                    continue
                cmds.close(PI_socket)
                session_open=False
            case "quit":
                cmds.close(PI_socket)
                break
                
            case "open":
                if session_open == True:
                    print(f"A Connection to a FTP Server is already open. Close the connection with cmd 'close'")
                    continue
                cmds.open(PI_socket, args)
                session_open=True
        #switch cmd ... # (ls/dir, cd, get, put, closer, quit)
            

#somehwere if SIGKILL/SIGINT call exit_gracefully(). 

    #init whats neccessary
    #Init PI socket (port 21, connect(), expect 220 on success)

    #user login

    #User input
    #while(True):
        #get user input
            #(userm dir/ls, cd, get, put, close, quit)
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
    



if __name__ == "__main__":
    main()