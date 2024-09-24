import asyncio
from http import HTTPStatus
import http.server
import json
import AcState
import Historian


def getAcString():
    state = asyncio.run(AcState.getAcState(False))
    powerStr = "powered" if state.isOn() else "unpowered"
    coolingStr = (
        "unknown"
        if state.shouldBePullingPower() is None
        else ("cooling" if state.shouldBePullingPower() else "standby")
    )
    pendingStr = (
        "unknown"
        if state.shouldBePullingPower() is None
        else ("pending" if state.disobedientPowerUsage() else "ok")
    )
    return f"{powerStr} {coolingStr} {state.getPowerUsage()}W ({pendingStr})"


# pylint: disable=attribute-defined-outside-init
class RequestHandler(http.server.SimpleHTTPRequestHandler):
    def sendString(self, data, code=HTTPStatus.OK):
        self.send_response(code)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()

        self.wfile.write(data.encode())

    def sendJson(self, data, code=HTTPStatus.OK):
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()

        self.wfile.write(data.encode())

    def sendEmpty(self, code=HTTPStatus.NO_CONTENT):
        self.send_response(code)
        self.end_headers()

    def do_GET(self):
        if self.path == "/":
            self.path = "/index.html"

        if self.path in [
            "/index.html",
            "/index.old.html",
            "/script.js",
            "/script.old.js",
            "/d3.js",
            "/plot.js",
            "/styles.css",
        ]:
            super().do_GET()
        elif self.path == "/status":
            state = asyncio.run(AcState.getAcState(False))
            ac = {
                "powered": state.isOn(),
                "watts": state.getPowerUsage(),
                "lastToggleTime": state.getLastToggleTime(),
                "inCooldown": state.isInAntiShortCycleCooldown(),
                "pullingPower": state.shouldBePullingPower(),
                "disobedientPower": state.disobedientPowerUsage(),
            }
            data = {
                "version": 1,
                "temp": AcState.lastTemp,
                "lowerTemp": AcState.lowerTemp,
                "upperTemp": AcState.upperTemp,
                "ac": ac,
            }
            self.sendJson(json.dumps(data))
        elif self.path == "/history":
            print("Getting history")
            history = Historian.getHistoryDict()
            print("Got history")
            self.sendJson(json.dumps(history))
            print("Done")
        elif self.path == "/temp":
            self.sendString(f"{AcState.lastTemp}")
        elif self.path == "/ac-status":
            self.sendString(getAcString())
        elif self.path == "/lower-temp":
            self.sendString(str(AcState.lowerTemp))
        elif self.path == "/upper-temp":
            self.sendString(str(AcState.upperTemp))
        else:
            self.sendEmpty(HTTPStatus.NOT_FOUND)

    def do_PUT(self):
        if self.path == "/ac-on":
            asyncio.run(AcState.turnAcOn())
            self.sendEmpty()
        elif self.path == "/ac-off":
            asyncio.run(AcState.turnAcOff())
            self.sendEmpty()
        elif self.path == "/lower-temp":
            try:
                AcState.lowerTemp = int(self.rfile.readline().decode())
                self.sendEmpty()
            except ValueError:
                self.sendEmpty(HTTPStatus.BAD_REQUEST)
        elif self.path == "/upper-temp":
            try:
                AcState.upperTemp = int(self.rfile.readline().decode())
                self.sendEmpty()
            except ValueError:
                self.sendEmpty(HTTPStatus.BAD_REQUEST)
        else:
            self.sendEmpty(HTTPStatus.NOT_FOUND)
