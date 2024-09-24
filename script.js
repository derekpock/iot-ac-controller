import * as Plot from "https://cdn.jsdelivr.net/npm/@observablehq/plot@0.6/+esm";

const ADDRESS = "http://10.0.0.140:53893";
const X_SCALE = (1 / (1000 * 60));

const startTime = Date.now();
let maxAgeHours = 4;
let tempHistory = [];
let powerOnHistory = [];
let powerOffHistory = [];
let powerState = null;
let upperTemp = 0;
let lowerTemp = 0;
let lastPowerChange = 0;
let inCooldown = null;

window.tempHistory = tempHistory;
window.powerOnHistory = powerOnHistory;
window.powerOffHistory = powerOffHistory;

const labTemp = document.getElementById("temp");
const labAcStatus = document.getElementById("acStatus");
const labLastPowerChange = document.getElementById("lastPowerChange");

const butAcOn = document.getElementById("butAcOn");
const butAcOff = document.getElementById("butAcOff");

const inUpperTemp = document.getElementById("inUpperTemp");
const inLowerTemp = document.getElementById("inLowerTemp");
const inHistoryHours = document.getElementById("inHistoryHours");
const butUpperTemp = document.getElementById("butUpperTemp");
const butLowerTemp = document.getElementById("butLowerTemp");
const butHistoryHours = document.getElementById("butHistoryHours");

async function doPutEmpty(api, button) {
    await doPutBody(api, button, null);
}

async function doPutBody(api, button, body) {
    button.disabled = true;
    try {
        const response = await fetch(ADDRESS + api, {
            method: "PUT",
            body: body
        });
        if (!response.ok) {
            throw new Error("Non OK response for PUT " + api);
        }
        const data = await response.text();
    } catch (reason) {
        console.log("Error in PUT " + api, reason);
    } finally {
        button.disabled = false;
    }
}

async function doGetPeriodically(api, onData, period) {
    try {
        const response = await fetch(ADDRESS + api);
        if (!response.ok) {
            throw new Error("Non OK response for GET " + api);
        }
        const data = await response.text();
        onData(data);
    } catch (reason) {
        console.log("Error GET " + api + ":", reason);
    } finally {
        if (period > 0) {
            setTimeout(() => {
                doGetPeriodically(api, onData, period);
            }, period);
        }
    }
}

function updatePlot() {
    const plot = Plot.plot({
        y: { grid: true },
        marks: [
            Plot.ruleY([upperTemp, lowerTemp]),
            Plot.ruleX(powerOnHistory, { stroke: "green" }),
            Plot.ruleX(powerOffHistory, { stroke: "red" }),
            Plot.lineY(tempHistory, { x: "time", y: "temp", stroke: "steelblue", marker: "none" })
        ]
    });
    const div = document.querySelector("#tempGraph");
    div.replaceChildren(plot);
}

function handleTempButton(api, input, button) {
    let temp = parseFloat(input.value);
    if (isNaN(temp)) {
        console.log("Input is not a number");
        return;
    }
    temp = Math.round(temp * 100);
    doPutBody(api, button, temp + "\n").then(() => {
        updateStatus(0);
    });
}

function trimHistory() {
    const maxAgeMs = maxAgeHours * 1000 * 60 * 60;
    const cutoffTime = (Date.now() - startTime - maxAgeMs) * X_SCALE;
    tempHistory = tempHistory.filter(item => item.time >= cutoffTime);
    powerOnHistory = powerOnHistory.filter(item => item >= cutoffTime);
    powerOffHistory = powerOffHistory.filter(item => item >= cutoffTime);
}

function updateLastPowerChange(reschedule) {
    let change = lastPowerChange;
    if (change == 0) {
        change = startTime;
    }

    const elapsed = Math.floor((Date.now() - change) / 1000);
    const minutes = Math.floor(elapsed / 60);
    const seconds = (elapsed - (minutes * 60));
    let text = "";

    if (lastPowerChange == 0) {
        text += "at least ";
    }

    if (minutes > 0) {
        if (minutes == 1) {
            text += minutes + " minute ";
        } else {
            text += minutes + " minutes ";
        }
    }

    if (seconds > 0) {
        if (minutes > 0) {
            text += "and ";
        }
        if (seconds == 1) {
            text += seconds + " second ";
        } else {
            text += seconds + " seconds ";
        }
    }

    if (minutes == 0 && seconds == 0) {
        text += "now";
    } else {
        text += "ago";
    }

    if (inCooldown != null) {
        if (inCooldown) {
            text += " (on cooldown)";
        } else {
            text += " (ready)";
        }
    }

    labLastPowerChange.innerText = text;

    if (reschedule) {
        setTimeout(() => {
            updateLastPowerChange(true);
        }, 1000);
    }
}

async function refreshHistory() {
    await doGetPeriodically("/history", handleHistory, 0);
}

function handleHistory(dataStr) {
    const data = JSON.parse(dataStr);
    const now = data["now"];

    const temp = data["temp"];
    tempHistory.length = 0;
    for (const idx in temp.reverse()) {
        tempHistory.push({ "time": ((now - temp[idx][0]) - startTime) * X_SCALE, "temp": temp[idx][1] / 100 });
    }

    const powerOn = data["powerOn"];
    powerOnHistory.length = 0;
    for (const idx in powerOn) {
        powerOnHistory.push(((now - powerOn[idx]) - startTime) * X_SCALE);
    }

    const powerOff = data["powerOff"];
    powerOffHistory.length = 0;
    for (const idx in powerOff) {
        powerOffHistory.push(((now - powerOff[idx]) - startTime) * X_SCALE);
        window.myNow = now;
        window.myIdx = powerOff[idx];
    }
}

async function updateStatus(period) {
    await doGetPeriodically("/status", handleStatus, period);
}

function handleStatus(dataStr) {
    const data = JSON.parse(dataStr);

    const temp = data["temp"] / 100;
    upperTemp = data["upperTemp"] / 100;
    lowerTemp = data["lowerTemp"] / 100;

    labTemp.innerText = temp;
    inUpperTemp.value = upperTemp;
    inLowerTemp.value = lowerTemp;

    tempHistory.push({ "time": (Date.now() - startTime) * X_SCALE, "temp": temp });

    const ac = data.ac;
    lastPowerChange = ac.lastToggleTime * 1000;
    inCooldown = ac.inCooldown;
    if (ac.pullingPower != null && powerState == null) {
        // Do not treat first update as a trigger edge.
        powerState = ac.pullingPower;
    } else if (ac.pullingPower != null && powerState !== ac.pullingPower) {
        powerState = ac.pullingPower;
        if (powerState) {
            powerOnHistory.push((Date.now() - startTime) * X_SCALE);
        } else {
            powerOffHistory.push((Date.now() - startTime) * X_SCALE);
        }
    }
    const poweredStr = (ac.powered ? "powered" : "unpowered");
    const coolingStr = (ac.pullingPower != null ? (ac.pullingPower ? "cooling" : "standby") : "unknown");
    const wattsStr = ac.watts + "W";
    const pendingStr = (ac.pullingPower != null ? (ac.disobedientPower ? "pending" : "ok") : "unknown");

    labAcStatus.innerText = poweredStr + " " + coolingStr + " " + wattsStr + " (" + pendingStr + ")";

    trimHistory();
    updatePlot();
    updateLastPowerChange(false);
}

butAcOn.onclick = () => {
    doPutEmpty("/ac-on", butAcOn).then(() => {
        updateStatus(0);
    });
};

butAcOff.onclick = () => {
    doPutEmpty("/ac-off", butAcOff).then(() => {
        updateStatus(0);
    });
};

butUpperTemp.onclick = () => {
    handleTempButton("/upper-temp", inUpperTemp, butUpperTemp);
};

butLowerTemp.onclick = () => {
    handleTempButton("/lower-temp", inLowerTemp, butLowerTemp);
};

butHistoryHours.onclick = () => {
    const hours = parseFloat(inHistoryHours.value);
    if (isNaN(hours)) {
        console.log("Input is not a number");
        return;
    }
    maxAgeHours = hours;
    butHistoryHours.disabled = true;
    inHistoryHours.disabled = true;
    refreshHistory().then(() => {
        trimHistory();
        updatePlot();
    }).finally(() => {
        inHistoryHours.disabled = false;
        butHistoryHours.disabled = false;
    });
};

inHistoryHours.value = maxAgeHours;
updateLastPowerChange(true);
refreshHistory().then(() => {
    updateStatus(10000);
});
