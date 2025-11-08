
import socket 
from typing import Tuple, List, Dict, Optional
from threading import Thread
from socket import socket, AF_INET, SOCK_STREAM, timeout
def normalize_inputs(raw_input: str) -> tuple[str, list[str]]:
    
    if not raw_input or not raw_input.strip():
        return "", []

    # Normalize whitespace and case
    tokens = raw_input.strip().lower().split()
    cmd = tokens[0]
    args = tokens[1:]

    # Known FTP commands and their expected arg counts
    expected_args = {
        "open": 1,
        "user": 1,
        "pass": 1,
        "ls": 0,
        "dir": 0,
        "cd": 1,
        "get": 1,
        "put": 1,
        "close": 0,
        "quit": 0,
        "help": 0,
    }

    if cmd in expected_args:
        required = expected_args[cmd]
        if required == 0 and args:
            print(f"'{cmd}' takes no arguments but got: {' '.join(args)}")
        elif required > 0 and len(args) < required:
            print(f"'{cmd}' expects {required} argument(s), but got none.")
        elif cmd == "open" and args: #quick warning quard 
            host = args[0]
            if "." not in host:
                print(f"Warning: 'open' expects a host like xxx.yyy.zzz, got '{host}'")
    else:
        print(f"Unknown command '{cmd}'. Type 'help' for available commands.")

    return cmd, args


#sends the FTP Command to the server given a socket, returns the reply #TODO: confirm DTP Commands work the same with multithreading
def send_cmd(pi_sock: socket, cmd: str) -> tuple[int, str]:
    if not cmd or not isinstance(cmd, str):
        raise ValueError("send_cmd() requires a non-empty string command")

    # Always send CRLF-terminated commands (per RFC959 4.1)
    message = f"{cmd}\r\n".encode("utf-8")

    try:
        pi_sock.sendall(message)
    except OSError as e:
        raise ConnectionError(f"Failed to send command '{cmd}': {e}")

    # Immediately read the full reply (single or multiline)
    code, reply_text = read_reply(pi_sock)
    return code, reply_text

#Read and fully parse the reply from FTP
def read_reply(pi_sock: socket, *, chunk_size: int = 4096, timeout: Optional[float] = None) -> Tuple[int, str]:

    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")

    old_timeout = pi_sock.gettimeout()
    if timeout is not None:
        pi_sock.settimeout(timeout)

    try:
        buf = bytearray()
        code: Optional[int] = None
        multiline = False

        while True:
            # Always try to interpret what we have
            text = buf.decode("utf-8", errors="replace")
            lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")

            # Do we know the code yet?
            if code is None and lines and len(lines[0]) >= 3 and lines[0][:3].isdigit():
                code = int(lines[0][:3])
                multiline = len(lines[0]) > 3 and lines[0][3] == "-"

            # No code yet → need more data
            if code is None:
                chunk = pi_sock.recv(chunk_size)
                if not chunk:
                    raise ConnectionError("Connection closed before any reply received.")
                buf.extend(chunk)
                continue

            # --- Single-line replies ----------------------------------------
            if not multiline:
                # Reply complete once first line ends with CRLF or '\n'
                if "\n" in text:
                    break
                chunk = pi_sock.recv(chunk_size)
                if not chunk:
                    raise ConnectionError("Connection closed mid-reply.")
                buf.extend(chunk)
                continue

            # --- Multiline replies ------------------------------------------
            # Done when any line begins with 'XYZ ' (code + space)
            terminator = f"{code} "
            if any(ln.startswith(terminator) for ln in lines):
                break

            chunk = pi_sock.recv(chunk_size)
            if not chunk:
                raise ConnectionError("Connection closed mid-multiline reply.")
            buf.extend(chunk)

    finally:
        if timeout is not None:
            pi_sock.settimeout(old_timeout)

    reply_text = buf.decode("utf-8", errors="replace")

    if code is None:
        raise ValueError(f"Malformed FTP reply (no numeric code): {reply_text!r}")

    return code, reply_text


#Format a,b,c,d,hi,lo for the PORT command.
def encode_port_arg(local_ip: str, port: int) -> str:
    a, b, c, d = local_ip.split(".")
    return f"{a},{b},{c},{d},{port//256},{port%256}"

def dtp_connect(pi_sock: socket, *, backlog: int = 1):

    local_ip = pi_sock.getsockname()[0]

    receptionist: Optional[socket] = None
    data_sock: Optional[socket] = None
    try:
        receptionist = socket(AF_INET, SOCK_STREAM)
        receptionist.bind((local_ip, 0))     # ephemeral port
        receptionist.listen(backlog)
        _, local_port = receptionist.getsockname()

        port_arg = encode_port_arg(local_ip, local_port)
        code, _ = send_cmd(pi_sock, f"PORT {port_arg}")
        if not (200 <= code < 300):
            raise ConnectionError(f"PORT failed with code {code}")

        data_sock, _ = receptionist.accept()
        #don't need the listener anymore
        receptionist.close()
        receptionist = None
        return data_sock

    except Exception:
        # if anything failed, clean up and re-raise
        if data_sock:
            try: data_sock.close()
            except: pass
        raise
    finally:
        if receptionist:
            try: receptionist.close()
            except: pass


def start_recv_thread(data_sock: socket, *, chunk_size: int = 65536) -> Tuple[Thread, List[bytes]]: #TODO figure out byte size
    """
    Start a daemon thread that drains data_sock into a list of byte chunks.
    Returns (thread, chunks). Caller should .join() the thread.
    """
    chunks: List[bytes] = []

    def _recv_all():
        try:
            while True:
                buf = data_sock.recv(chunk_size)
                if not buf:
                    break
                chunks.append(buf)
        finally:
            try:
                data_sock.close()
            except Exception:
                pass

    t = Thread(target=_recv_all, daemon=True)
    t.start()
    return t, chunks

def start_send_file_thread(data_sock: socket, file_path: str, *, chunk_size: int = 65536) -> Thread:
    """
    Start a daemon thread that streams a local file over data_sock.
    Caller should .join() the thread.
    """
    def _send_file():
        try:
            with open(file_path, "rb") as f:
                while True:
                    buf = f.read(chunk_size)
                    if not buf:
                        break
                    data_sock.sendall(buf)
        finally:
            try:
                data_sock.close()
            except Exception:
                pass

    t = Thread(target=_send_file, daemon=True)
    t.start()
    return t