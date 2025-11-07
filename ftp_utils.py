
import socket 
from typing import Tuple, List, Dict, Optional
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
