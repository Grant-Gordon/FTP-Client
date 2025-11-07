from typing import Tuple, Dict, Optional, List
from socket import socket, AF_INET, SOCK_STREAM, timeout
import ftp_utils as utils
from threading import Thread

########PI ONLY##########

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
    
    #Handle user Codes #TODO confirm codes 
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

def close():
    return
    
def quit():
    return 


##########DTP###############

def ls(PI_socket):
    # TYPE A for lsitings
    code, _ =  utils.send_cmd(PI_socket, "TYPE A")
    if code //100 !=2:
        print(f"TYPE A failed with code {code}")
        return False
    
    local_ip = PI_socket.getsockname()[0]
    receptionist = None
    DTP_Socket= None

    try:
        receptionist = socket(AF_INET, SOCK_STREAM)
        receptionist.bind((local_ip, 0))
        receptionist.listen(1)

        _, local_port = receptionist.getsockname()

        a, b, c, d, = local_ip.split(".")
        hi, lo = (local_port // 256), (local_port % 256)
        port_arg = f"{a},{b},{c},{d},{hi},{lo}"

        code, _ = utils.send_cmd(PI_socket, f"PORT {port_arg}")
        if code //100 !=2:
            print(f"PORT failed with code {code}")
            return False
        DTP_Socket, _addr = receptionist.accept()


        code, _ = utils.send_cmd(PI_socket, "NLST") #TODO: something about this
        if code not in (125, 150):
            print(f"NLST not accepted (code {code})")
            return False
        
        chunks = []

        def _recv_all():
            try:
                while True:
                    buf = DTP_Socket.recv(8192)
                    if not buf:
                        break
                    chunks.append(buf)
            finally:
                try:
                    DTP_Socket.close()
                except Exception:
                    pass

        worker = Thread(target=_recv_all, daemon=True)
        worker.start()
        worker.join()

        # Emit listing to stdout (text)
        if chunks:
            try:
                # Server sends text; decode defensively
                print(b"".join(chunks).decode("utf-8", errors="replace"), end="")
            except Exception as e:
                print(f"[warn] decoding listing: {e}")

        # 6) Expect secondary completion reply (226/250)
        code, _ = utils.read_reply(PI_socket)
        if code not in (226, 250):
            print(f"NLST completion not OK (code {code})")
            return False
        return True

    except Exception as e:
        print(f"ls error: {e}")
        return False
    finally:
        try:
            if DTP_Socket:
                DTP_Socket.close()
        except Exception:
            pass
        try:
            if receptionist:
                receptionist.close()
        except Exception:
            pass



    
def get():
    return
    
def put():
    return