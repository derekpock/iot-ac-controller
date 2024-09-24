from collections import deque
import itertools
import threading
import time
import AcState

# Keep 10 second history of last 4 hours of data = ~1440 pts
# Keep 1 minute history of last 24 hours of data = ~1440 pts
# Keep 10 minute history of last 10 days of data = ~1440 pts

MAX_ITEMS = 1440

SHORT_CHECK_SEC = 10
MID_CHECK_SEC = 60
LONG_CHECK_SEC = 600

UNIQUE_MID_IDX_CUTOFF = int(MAX_ITEMS * (SHORT_CHECK_SEC / MID_CHECK_SEC))
UNIQUE_LONG_IDX_CUTOFF = int(MAX_ITEMS * (MID_CHECK_SEC / LONG_CHECK_SEC))

# SHORT_EXPIRE_SEC = 60 * 60 * 4  # (or MAX_ITEMS * SHORT_CHECK_SEC)
# MID_EXPIRE_SEC = 60 * 60 * 24  # (or MAX_ITEMS * MID_CHECK_SEC)
# LONG_EXPIRE_SEC = 60 * 60 * 24 * 10  # (or MAX_ITEMS * LONG_CHECK_SEC)

historyMutex = threading.Lock()
shortHistory: deque[int] = deque([], MAX_ITEMS)
midHistory: deque[int] = deque([], MAX_ITEMS)
longHistory: deque[int] = deque([], MAX_ITEMS)
powerOnHistory: deque[float] = deque()
powerOffHistory: deque[float] = deque()

lastShortCheck = time.time()
lastMidCheck = time.time()
lastLongCheck = time.time()


def getHistoryDict():
    # "[[1233322, 7500],[...],...]"
    # Math below could be confusing.
    # All histories have some overlap with each other in terms of data stored. For example:
    # Samples by time range if maxItems = 8:
    # Short:  X-X-X-X-X-X-X-X
    # Mid:    X---X---X---X---X---X---X---X
    # Long:   X-------X-------X-------X-------X-------X-------X-------X
    #        | short         | mid         | long                      |
    # Shared: X-X-X-X-X-X-X-X-X---X---X---X---X-------X-------X-------X
    # We don't need the first chunk of Mid (since it is covered by Short)
    # We don't need the first chunk of Long (since it is covered by Short and Mid)
    # The unique idx cutoff is the time at which Mid starts storing data that Short has expired.
    # E.g. (SHORT_EXPIRE_SEC / MID_CHECK_SEC)
    # Or   ((MAX_ITEMS * SHORT_CHECK_SEC) / MID_CHECK_SEC)
    # Or   (MAX_ITEMS * (SHORT_CHECK_SEC / MID_CHECK_SEC))
    print("Acquiring lock")
    historyMutex.acquire()
    print("Got it, working")
    now = time.time()
    history = [
        [int((now - (lastShortCheck - (SHORT_CHECK_SEC * idx))) * 1000), temp]
        for idx, temp in enumerate(shortHistory)
    ]
    history += [
        [
            int(
                (now - (lastMidCheck - (MID_CHECK_SEC * (idx + UNIQUE_MID_IDX_CUTOFF))))
                * 1000
            ),
            temp,
        ]
        for idx, temp in enumerate(
            itertools.islice(midHistory, UNIQUE_MID_IDX_CUTOFF, None)
        )
    ]
    history += [
        [
            int(
                (
                    now
                    - (
                        lastLongCheck
                        - (LONG_CHECK_SEC * (idx + UNIQUE_LONG_IDX_CUTOFF))
                    )
                )
                * 1000
            ),
            temp,
        ]
        for idx, temp in enumerate(
            itertools.islice(longHistory, UNIQUE_LONG_IDX_CUTOFF, None)
        )
    ]
    data = {
        "now": int(now * 1000),
        "temp": history,
        "powerOn": [int((now - x) * 1000) for x in powerOnHistory],
        "powerOff": [int((now - x) * 1000) for x in powerOffHistory],
    }
    historyMutex.release()
    print("Released lock")
    return data


def runHistorian():
    global lastShortCheck, lastMidCheck, lastLongCheck

    time.sleep(SHORT_CHECK_SEC)
    while True:
        historyMutex.acquire()
        now = time.time()
        temp = AcState.lastTemp or 0
        shortHistory.appendleft(temp)
        lastShortCheck += SHORT_CHECK_SEC

        if (now - lastMidCheck) > MID_CHECK_SEC:
            midHistory.appendleft(temp)
            lastMidCheck += MID_CHECK_SEC

        if (now - lastLongCheck) > LONG_CHECK_SEC:
            longHistory.appendleft(temp)
            lastLongCheck += LONG_CHECK_SEC
            removeExpired(now, powerOnHistory, MAX_ITEMS * LONG_CHECK_SEC)
            removeExpired(now, powerOffHistory, MAX_ITEMS * LONG_CHECK_SEC)

        historyMutex.release()

        if (lastShortCheck + SHORT_CHECK_SEC) > now - lastShortCheck:
            time.sleep((lastShortCheck + SHORT_CHECK_SEC) - now)


def removeExpired(now: float, history: deque[float], expiry: int):
    expiryTime = now - expiry
    while history:
        if history[0] < expiryTime:
            history.popleft()
        else:
            break
