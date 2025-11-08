from typing import Tuple, Dict, Optional, List
from socket import socket, AF_INET, SOCK_STREAM, timeout
import ftp_utils as utils
from threading import Thread

########PI ONLY##########

###############  OPEN  ###########
#connect to ftp server on port 21 with USER & PASS
def open(host: str) -> Tuple[Optional[socket], bool]:
    pi_sock = None
    
    #Open Socket
    try:
        pi_sock = socket(AF_INET, SOCK_STREAM)
        pi_sock.settimeout(10.0)
        pi_sock.connect((host, 21))
    except timeout:
        print(f"Connection to {host}: 21 timeed out")
        return None, False
    except OSError:
        print(f"Failled to connect to {host}:21 {OSError}")
    

    #Read Reply
    try:
        code, _ = utils.read_reply(pi_sock) #TODO read reply
    except Exception as e:
        print(f"Error reading server Banner: {e}")
        try:
            pi_sock.close()
        except Exception:
            pass
        return None, False
    #Status code of opening socket 
    if code != 220:
        print(f"Unexpected server banner code {code}; expected 220. Aborting.")
        try:
            pi_sock.close()
        except Exception:
            pass
        return None, False
    
    #Get user credentials 
    try:
        username = input("User: ").strip()
        if not username:
            username = "anonymous" #TODO anonymous intended behavoir 

        code, _ = utils.send_cmd(pi_sock, f"USER {username}") #TODO send_cmd
    except Exception as e:
        print(f"Error during USER command: {e}")
        try:
            pi_sock.close()
        except Exception:
            pass
        return None, False
    
    #Handle user Codes 
    if code == 230:
        # Logged in without PASS
        return pi_sock, True
    elif code == 331:
        # Need password
        password = input("Password: ")
        try:
            code, _ = utils.send_cmd(pi_sock, f"PASS {password}")
        except Exception as e:
            print(f"Error during PASS command: {e}")
            try:
                pi_sock.close()
            except Exception:
                pass
            return None, False

        if code == 230: #TODO populate codes
            return pi_sock, True
        elif code == 332:
            print("Server requests an account (332) — not supported in this client.")
        else:
            print(f"Authentication failed with code {code}.")
    elif code == 332:
        print("Server requests an account (332) — not supported in this client.")
    else:
        # 4xx/5xx errors and any other unexpected codes
        print(f"USER rejected with code {code}.")
    
    
    # Failure path: close and return
    try:
        pi_sock.close()
    except Exception:
        pass
    return None, False

def cd(pi_sock: socket, path: str) -> bool:
    code, _ = utils.send_cmd(pi_sock, f"CWD {path}")
    if code // 100 != 2:
        print(f"CWD failed: {code}")
        return False
    return True


############  CLOSE  #############
def close(PI_socket: socket):
    if PI_socket is None:
        print("No active connection to close")
        return False
    
    try:
        code, _ = utils.send_cmd(PI_socket, "QUIT")
        if code //100 == 2:
            print("Session closed by server.")
        else:
            print(f"Server returned code {code} on QUIT.")

    except Exception as e:
        print(f"Failed to send Quit: {e}")
    finally:
        try:
            PI_socket.close()
        except Exception:
            pass
    return True


############  QUIT  ###############
def quit(PI_socket: socket):
    if PI_socket is not None:
        try:
            code, _  = utils.send_cmd(PI_socket, "QUIT")
            if code //100 == 2:
                print(f"Session closed by Server.")
        except Exception:
            pass
        finally:
            try:
                PI_socket.close()
            except Exception:
                pass
    print("Exiting program")

#############################################
#-----------  DTP  commands  ----------------
#############################################

#############  LS  #######################33
def ls(pi_sock: socket, *, names_only: bool = False) -> bool:
    if pi_sock is None:
        print("Not connected."); return False

    code, _ = utils.send_cmd(pi_sock, "TYPE A")
    if not (200 <= code < 300):
        print(f"TYPE A failed: {code}"); return False

    try:
        ds = utils.dtp_connect(pi_sock)  # <-- no 'with', just a normal function
    except Exception as e:
        print(f"PORT/accept failed: {e}"); return False

    ftp_cmd = "LIST" #NLST?
    code, _ = utils.send_cmd(pi_sock, ftp_cmd)
    if code not in (125, 150):
        print(f"{ftp_cmd} not accepted: {code}")
        ds.close()
        return False

    # receive directory listing (can use a thread helper or do it inline)
    chunks = []
    try:
        while True:
            buf = ds.recv(8192)
            if not buf: break
            chunks.append(buf)
    finally:
        try: ds.close()
        except: pass

    code, _ = utils.read_reply(pi_sock)
    if code not in (226, 250):
        print(f"{ftp_cmd} completion not OK: {code}"); return False

    if chunks:
        print(b"".join(chunks).decode("utf-8", errors="replace"), end="")
    return True
    

#####################  GET  ######################
def get(PI_socket, remote:str, local_path: str):
    try:
        out = open(local_path, 'wb')
    except OSError as e:
        print (f" local open failed: {e}")
        return False
    
    code, _ = utils.send_cmd(PI_socket, "TYPE I")
    if not (200 <= code < 300):
        print("TYPE I failed")
        out.close
        return False

    with utils.dtp_connect(PI_socket) as ds:
        code, _ = utils.send_cmd(PI_socket, f"RETR {remote}")
        if code not in (125, 150):
            print(f"RETR prelim failed: {code}")
            out.close
            return False
        t, chunks = utils.start_recv_thread(ds)
        t.join() #recieved all file Bytes

    code, _ = utils.read_reply(PI_socket)
    if code not in (226, 250):
        print(f"RETR completion failed: code {code}")
        out.close
        return False
    
    try:
        out.write(b"".join(chunks))
    finally:
        out.close()
    return True
    

#############  PUT  ############ 
def put(PI_socket, local_path, remote):
    try:
        with open(local_path, 'rb'):
            pass
    except OSError as e:
        print(f"local open failed: {e}")
        return False
    
    code, _ = utils.send_cmd(PI_socket, "TYPE I")
    if not (200 <= code < 300):
        print(f"TYPE I failed")
        return False
    
    with utils.dtp_connect(PI_socket) as ds:
        code, _ = utils.send_cmd(PI_socket, f"STOR {remote}")
        if code not in (125, 150):
            print(f"STOR preliminary failed: code {code}")
            return False
        t = utils.start_send_file_thread(ds, local_path)
        t.join() # File fully sent

    code, _ = utils.read_reply(PI_socket)
    if code not in (226, 250):
        print(f"STOR completion failed: code {code}")
        return False
    return True
    
    