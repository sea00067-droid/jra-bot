const LIFF_ID = "2009134533-h8bU1BkZ";
let html5QrCode;
let scannedCodes = []; // To store 1st and 2nd QR parts

document.addEventListener("DOMContentLoaded", function () {
    // Tab switching
    document.getElementById("tab-scan").addEventListener("click", () => switchTab("scan"));
    document.getElementById("tab-manual").addEventListener("click", () => switchTab("manual"));

    // Initialize LIFF
    liff.init({ liffId: LIFF_ID })
        .then(() => {
            if (!liff.isLoggedIn()) {
                liff.login();
            }
            console.log("LIFF Initialized");
        })
        .catch((err) => {
            console.error(err);
            document.getElementById("log").innerText = "LIFF Init Error: " + err;
        });

    // Camera Start Button
    document.getElementById("start-scan-btn").addEventListener("click", startScan);

    // Initial race num population
    const raceSelect = document.getElementById("race-num");
    for (let i = 1; i <= 12; i++) {
        let opt = document.createElement("option");
        opt.value = i;
        opt.text = i + "R";
        raceSelect.add(opt);
    }
});

function switchTab(mode) {
    if (mode === "scan") {
        document.getElementById("scan-view").style.display = "block";
        document.getElementById("manual-view").style.display = "none";
        document.getElementById("tab-scan").classList.add("active");
        document.getElementById("tab-manual").classList.remove("active");
    } else {
        document.getElementById("scan-view").style.display = "none";
        document.getElementById("manual-view").style.display = "block";
        document.getElementById("tab-scan").classList.remove("active");
        document.getElementById("tab-manual").classList.add("active");
        if (html5QrCode) {
            html5QrCode.stop().catch(err => console.error(err));
        }
    }
}

function startScan() {
    html5QrCode = new Html5Qrcode("reader");
    const config = { fps: 10, qrbox: { width: 250, height: 250 } };

    html5QrCode.start({ facingMode: "environment" }, config, onScanSuccess)
        .catch(err => {
            document.getElementById("log").innerText = "Camera Start Error: " + err;
        });

    document.getElementById("start-scan-btn").style.display = "none";
    document.getElementById("scan-status").innerText = "QRコードをかざしてください...";
}

function onScanSuccess(decodedText, decodedResult) {
    // Check if it looks like JRA QR
    // JRA QR is usually 190 digits split into two? Or concatenated?
    // Actually, each QR is a part.
    // We need to collect them.

    if (scannedCodes.includes(decodedText)) return; // Avoid dupe

    scannedCodes.push(decodedText);
    document.getElementById("scan-status").innerText = `${scannedCodes.length}個目のQRを読み取りました`;

    // Determine if we have enough
    // Logic: Look for "190 digits" total?
    // Or just say "Scan next"?

    if (scannedCodes.length >= 2) {
        // Stop scanning
        html5QrCode.stop().then(() => {
            document.getElementById("reader").style.display = "none";
            document.getElementById("scan-status").innerText = "読み取り完了！解析中...";
            processScannedData();
        }).catch(err => console.error(err));
    }
}

function processScannedData() {
    // Send to API
    // Combine QRs. Order matters?
    // Usually JRA QRs have sequence info in them, but simple concat often works
    // if sorted by ... something?
    // For now, let's just concat in order scanned or try both perms server side?
    // Let's create a combined string.

    let combined = scannedCodes.join("");

    // Mock parsing for display in UI (real parsing should happen on server or here if possible)
    // Display result to user

    document.getElementById("scan-result").style.display = "block";
    document.getElementById("parsed-data").innerText = "データ送信準備完了 (サーバーで解析します)";

    document.getElementById("submit-scan-btn").onclick = function () {
        submitData(combined);
    };
}

function submitData(qrData) {
    // To be implemented: API call
    console.log("Submitting: " + qrData);
    // For now, let's restart scan
    alert("送信機能は未実装です(Coming soon)");
    location.reload();
}
