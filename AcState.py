import time
import kasa
import Historian

AC_KASA_ADDRESS = "10.0.0.206"
PLUG_UPDATE_EXPIRY_SEC = 10
PLUG_POWER_RUNNING = 30
ANTI_SHORT_CYCLE_COOLDOWN_SEC = 60 * 20  # 20 min

lowerTemp = 7400
upperTemp = 8500
lastTemp: int | None = None

_acShouldBePullingPower: bool | None = None
_lastToggleTime: float | None = None


class _AcState:
    def __init__(self, plug: kasa.SmartPlug):
        self._powered = plug.is_on
        self._powerUsage = plug.emeter_realtime.power
        self._time = time.time()

    def getLastToggleTime(self):
        return _lastToggleTime

    def isInAntiShortCycleCooldown(self):
        if _lastToggleTime is None:
            return False
        return (time.time() - _lastToggleTime) < ANTI_SHORT_CYCLE_COOLDOWN_SEC

    def isExpired(self):
        return (time.time() - self._time) > PLUG_UPDATE_EXPIRY_SEC

    def isOn(self):
        return self._powered

    def getPowerUsage(self):
        return self._powerUsage

    def shouldBePullingPower(self):
        return _acShouldBePullingPower

    def disobedientPowerUsage(self):
        return _acShouldBePullingPower != (self._powerUsage > PLUG_POWER_RUNNING)


_acState: _AcState | None = None


async def getAcState(forceUpdate: bool):
    global _acState

    if (
        forceUpdate
        or _acState is None
        or _acState.isExpired()
        or _acState.disobedientPowerUsage()
    ):
        plug = kasa.SmartPlug(AC_KASA_ADDRESS)
        await plug.update()
        _acState = _AcState(plug)

    return _acState


async def turnAcOn():
    global _acState, _acShouldBePullingPower, _lastToggleTime

    print("Turning AC on")
    # plug = kasa.SmartPlug(AC_KASA_ADDRESS)
    # await plug.turn_on()
    wasPullingPower = _acShouldBePullingPower
    _acShouldBePullingPower = True
    _lastToggleTime = time.time()
    _acState = None  # Force update next call
    if wasPullingPower is False:
        Historian.historyMutex.acquire()
        Historian.powerOnHistory.append(time.time())
        Historian.historyMutex.release()
    print("Done with toggle")


async def turnAcOff():
    global _acState, _acShouldBePullingPower, _lastToggleTime

    print("Turning AC off")
    # plug = kasa.SmartPlug(AC_KASA_ADDRESS)
    # await plug.turn_off()
    wasPullingPower = _acShouldBePullingPower
    _acShouldBePullingPower = False
    _lastToggleTime = time.time()
    _acState = None  # Force update next call
    if wasPullingPower is True:
        Historian.historyMutex.acquire()
        Historian.powerOffHistory.append(time.time())
        Historian.historyMutex.release()
    print("Done with toggle")
