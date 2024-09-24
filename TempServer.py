import http.server
import socket
import threading
import ArduinoServer
import StatusHttpServer
import Historian

ARDUINO_PORT = 53892
HTTP_PORT = 53893


def runHttpServer():
    with http.server.ThreadingHTTPServer(
        ("", HTTP_PORT), StatusHttpServer.RequestHandler
    ) as server:
        server.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.serve_forever()


def main():
    httpServerThread = threading.Thread(target=runHttpServer)
    httpServerThread.daemon = True
    httpServerThread.start()

    historianThread = threading.Thread(target=Historian.runHistorian)
    historianThread.daemon = True
    historianThread.start()

    with socket.socket() as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("", ARDUINO_PORT))
        sock.listen()
        while True:
            conn, _ = sock.accept()
            handleConnectionThread = threading.Thread(
                target=ArduinoServer.handleConnection, args=(conn,)
            )
            handleConnectionThread.daemon = True
            handleConnectionThread.start()


if __name__ == "__main__":
    main()
