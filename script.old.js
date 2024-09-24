import * as Plot from "https://cdn.jsdelivr.net/npm/@observablehq/plot@0.6/+esm";

const startTime = Date.now();
let maxAgeHours = 4;
let tempHistory = [];
let powerOnHistory = [];
let powerOffHistory = [];
let powerState = "";
let upperTemp = 0;
let lowerTemp = 0;
let lastPowerChange = 0;

window.tempHistory = tempHistory
window.powerOnHistory = powerOnHistory
window.powerOffHistory = powerOffHistory

const butAcOn = document.getElementById("butAcOn");
const butAcOff = document.getElementById("butAcOff");
const inUpperTemp = document.getElementById("inUpperTemp");
const inLowerTemp = document.getElementById("inLowerTemp");
const inHistoryHours = document.getElementById("inHistoryHours");
const butUpperTemp = document.getElementById("butUpperTemp");
const butLowerTemp = document.getElementById("butLowerTemp");
const butHistoryHours = document.getElementById("butHistoryHours");

function updateField(api, id, period, formatData = data => { return data; }) {
    fetch("http://10.0.0.140:53893" + api).then(response => {
        if (!response.ok) {
            throw new Error("Non OK response for GET " + api);
        }
        return response.text();
    }).then(data => {
        document.getElementById(id).innerText = formatData(data);
    }).catch(reason => {
        console.log("Error updating " + id, reason);
        document.getElementById(id).innerText = "Error";
    }).finally(() => {
        if (period > 0) {
            setTimeout(() => {
                updateField(api, id, period, formatData);
            }, period);
        }
    });
}

function putEmpty(api, button, onComplete = null) {
    putBody(api, button, null, onComplete);
}

function putBody(api, button, body, onComplete = null) {
    button.disabled = true;
    fetch("http://10.0.0.140:53893" + api, {
        method: "PUT",
        body: body
    }).then(response => {
        if (!response.ok) {
            throw new Error("Non OK response for PUT " + api);
        }
        return response.text();
    }).then(data => {
    }).catch(reason => {
        console.log("Error in PUT " + api, reason);
    }).finally(() => {
        button.disabled = false;
        if (onComplete != null) {
            onComplete();
        }
    });
}

function formatTemp(data) {
    return parseInt(data) / 100;
}

function updatePlot() {
    const plot = Plot.plot({
        y: { grid: true },
        marks: [
            Plot.ruleY([upperTemp, lowerTemp]),
            Plot.ruleX(powerOnHistory, { stroke: "green" }),
            Plot.ruleX(powerOffHistory, { stroke: "red" }),
            Plot.lineY(tempHistory, { x: "time", y: "temp", stroke: "steelblue", marker: "dot" })
        ]
    });
    const div = document.querySelector("#tempGraph");
    div.replaceChildren(plot);
}

function handleTempButton(api, input, button, onComplete) {
    let temp = parseFloat(input.value);
    if (isNaN(temp)) {
        console.log("Input is not a number");
        return;
    }
    temp = Math.round(temp * 100);
    putBody(api, button, temp + "\n", onComplete);
}

function trimHistory() {
    const maxAgeMs = maxAgeHours * 1000 * 60 * 60;
    const cutoffTime = Date.now() - startTime - maxAgeMs;
    tempHistory = tempHistory.filter(item => item.time >= cutoffTime);
    powerOnHistory = powerOnHistory.filter(item => item >= cutoffTime);
    powerOffHistory = powerOffHistory.filter(item => item >= cutoffTime);
}

function updateLastPowerChange(reschedule) {
    const change = Math.max(lastPowerChange, startTime)

    const elapsed = Math.floor((Date.now() - change) / 1000);
    const minutes = Math.floor(elapsed / 60)
    const seconds = (elapsed - (minutes * 60));
    let text = "";

    if (lastPowerChange == 0) {
        text += "at least "
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
            text += "and "
        }
        if (seconds == 1) {
            text += seconds + " second "
        } else {
            text += seconds + " seconds "
        }
    }

    if (minutes == 0 && seconds == 0) {
        text += "now";
    } else {
        text += "ago"
    }

    const label = document.getElementById("lastPowerChange");
    label.innerText = text;

    if (reschedule) {
        setTimeout(() => {
            updateLastPowerChange(true);
        }, 1000);
    }
}

function updateTemp(reschedule) {
    updateField("/temp", "temp", (reschedule ? 10000 : 0), data => {
        const adjustedTemp = formatTemp(data);
        tempHistory.push({ "time": Date.now() - startTime, "temp": adjustedTemp });
        trimHistory();
        updatePlot();
        return adjustedTemp;
    });
}

function updateUpperTemp(reschedule) {
    updateField("/upper-temp", "upperTemp", (reschedule ? 60000 : 0), data => {
        const adjustedTemp = formatTemp(data);
        upperTemp = adjustedTemp;
        inUpperTemp.value = upperTemp;
        updatePlot();
        return adjustedTemp;
    });
}

function updateLowerTemp(reschedule) {
    updateField("/lower-temp", "lowerTemp", (reschedule ? 60000 : 0), data => {
        const adjustedTemp = formatTemp(data);
        lowerTemp = adjustedTemp;
        inLowerTemp.value = lowerTemp;
        updatePlot();
        return adjustedTemp;
    });
}

function updateStatus(reschedule) {
    updateField("/ac-status", "status", (reschedule ? 10000 : 0), data => {
        const newPowerState = data.split(" ")[1]
        if (powerState === "") {
            powerState = newPowerState;
        } else if (powerState != newPowerState) {
            powerState = newPowerState;
            lastPowerChange = Date.now();
            if (powerState === "cooling") {
                powerOnHistory.push(Date.now() - startTime);
            } else if (powerState === "standby") {
                powerOffHistory.push(Date.now() - startTime);
            } else if (!powerState === "unknown") {
                console.error("Power state not parsed:", data);
            }
        }
        return data;
    });
}

butAcOn.onclick = () => {
    putEmpty("/ac-on", butAcOn, () => {
        updateStatus(false);
        updateLastPowerChange(false);
    });
}

butAcOff.onclick = () => {
    putEmpty("/ac-off", butAcOff, () => {
        updateStatus(false);
        updateLastPowerChange(false);
    });
}

butUpperTemp.onclick = () => {
    handleTempButton("/upper-temp", inUpperTemp, butUpperTemp, () => {
        updateUpperTemp(false);
    });
}

butLowerTemp.onclick = () => {
    handleTempButton("/lower-temp", inLowerTemp, butLowerTemp, () => {
        updateLowerTemp(false);
    });
}

butHistoryHours.onclick = () => {
    const hours = parseFloat(inHistoryHours.value);
    if (isNaN(hours)) {
        console.log("Input is not a number");
        return;
    }
    maxAgeHours = hours;
}

inHistoryHours.value = maxAgeHours;
updateLastPowerChange(true);
updateTemp(true);
updateUpperTemp(true);
updateLowerTemp(true);
updateStatus(true);