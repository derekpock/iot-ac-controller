import asyncio
import socket
import threading
import time
import traceback
import AcState

TEMP_EXPIRY_SEC = 60
DEBOUNCE_SEC = 45  # 6 time updates above/below the temp threshold (single device)


class TempSample:
    def __init__(self, temp: int):
        self.temp = temp
        self.time = time.time()

    def isExpired(self):
        return (time.time() - self.time) > TEMP_EXPIRY_SEC


class Client:
    def __init__(self, address: str, temp: int):
        self.address = address
        self.offset = 0
        self.updateSample(temp)

    def updateSample(self, temp: int):
        self.sample = TempSample(temp)
        self._updateOffset()

    def _updateOffset(self):
        clientsMutex.acquire()
        otherSamples = [
            client.sample.temp
            for client in clients.values()
            if client.address != self.address
        ]
        clientsMutex.release()

        if otherSamples:
            otherAverage = int(sum(otherSamples) / len(otherSamples))
            self.offset = (otherAverage - self.sample.temp) / 2

    def getOffsetSample(self):
        return self.sample.temp + self.offset


clientsMutex = threading.RLock()
clients: dict[str, Client] = {}
debounceTimer: float | None = None


def clearExpiredSamples():
    clientsMutex.acquire()
    expiredKeys = [key for key, client in clients.items() if client.sample.isExpired()]
    for key in expiredKeys:
        print("Removing expired client:", key)
        clients.pop(key)
    clientsMutex.release()


def calculateLastTemp():
    clientsMutex.acquire()
    temps = [client.getOffsetSample() for client in clients.values()]
    clientsMutex.release()
    if temps:
        AcState.lastTemp = int(sum(temps) / len(temps))
    else:
        AcState.lastTemp = 0


def checkStateChange(state: AcState._AcState):
    global debounceTimer

    if state.isInAntiShortCycleCooldown():
        # Don't spam on/off when in anti-short-cycle cooldown.
        return

    if AcState.lastTemp < AcState.lowerTemp:
        if state.shouldBePullingPower() is False:
            # Already off, don't need to debounce.
            return

        if debounceTimer is None:
            # Start tracking how long temp is below the threshold.
            debounceTimer = time.time()
            return

        # TODO: debounceTimer can still be null here due to async.
        if (time.time() - debounceTimer) > DEBOUNCE_SEC:
            # Temp was below threshold for long enough to turn off AC.
            # acRunning = True  Why was this done before turning off?
            debounceTimer = None
            asyncio.run(AcState.turnAcOff())

        return

    if AcState.lastTemp > AcState.upperTemp:
        if state.shouldBePullingPower() is True:
            # Already on, don't need to debounce.
            return

        if debounceTimer is None:
            # Start tracking how long temp is above the threshold.
            debounceTimer = time.time()
            return

        # TODO: debounceTimer can still be null here due to async.
        if (time.time() - debounceTimer) > DEBOUNCE_SEC:
            # Temp was above threshold for long enough to turn on AC.
            # acRunning = False  Why was this done before turning on?
            debounceTimer = None
            asyncio.run(AcState.turnAcOn())

        return

    # Temp not beyond any threshold. Reset debounce.
    debounceTimer = None


def handleReceivedTemp() -> bool | None:
    clearExpiredSamples()
    calculateLastTemp()
    print(f"Average temp: {AcState.lastTemp}")

    state = asyncio.run(AcState.getAcState(False))
    checkStateChange(state)
    if state.disobedientPowerUsage():
        return state.shouldBePullingPower()

    return None


def handleConnection(conn: socket.socket):
    try:
        address = conn.getpeername()[0]
        data = conn.recv(1024)
        print(f"Received {data} from {address}")
        strData = data.decode()
        if strData == "ping":
            conn.sendall("pong".encode())
            return

        mapData = {
            keyValue.split(":")[0]: keyValue.split(":")[1]
            for keyValue in strData.split("\t")
        }

        version = 0
        if "v" in mapData:
            version = int(mapData["v"])

        if "temp" in mapData:
            temp = int(mapData["temp"])

            if temp >= 0:
                clientsMutex.acquire()
                if address in clients:
                    clients[address].updateSample(temp)
                else:
                    clients[address] = Client(address, temp)
                clientsMutex.release()

                actionPowerSet = handleReceivedTemp()
                if version >= 1 and actionPowerSet is not None:
                    print(f"sending {actionPowerSet}")
                    conn.sendall(("1" if actionPowerSet else "0").encode())

                    while len(conn.recv(1024)) > 0:
                        pass

    except KeyError as e:
        print("Malformed input, KeyError:", e)
        traceback.print_exc()
    except ValueError as e:
        print("Malformed input, ValueError:", e)
        traceback.print_exc()
    except IndexError as e:
        print("Malformed input, IndexError:", e)
        traceback.print_exc()
    except Exception as e:
        print("Exception handling request:", e)
        traceback.print_exc()
    finally:
        try:
            conn.close()
        except Exception as e:
            print("Exception closing connection:", e)
            traceback.print_exc()
