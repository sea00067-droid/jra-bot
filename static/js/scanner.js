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
    if (scannedCodes.includes(decodedText)) return; // Avoid dupe

    scannedCodes.push(decodedText);
    document.getElementById("scan-status").innerText = `${scannedCodes.length}個目のQRを読み取りました`;

    if (scannedCodes.length >= 2) {
        // Stop scanning
        html5QrCode.stop().then(() => {
            document.getElementById("reader").style.display = "none";
            document.getElementById("scan-status").innerText = "読み取り完了！解析中...";
            processScannedData();
        }).catch(err => console.error(err));
    }
}

async function processScannedData() {
    let combined = scannedCodes.join("");
    document.getElementById("parsed-data").innerText = "解析中...";

    try {
        const response = await fetch('/api/parse_qr', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ raw_qr: combined })
        });

        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.detail || "解析エラー");
        }

        const res = await response.json();
        const d = res.data;

        // Show parsed data
        const html = `
            <div style="text-align:left; font-size:14px; margin:10px 0;">
                <p><strong>場所:</strong> ${d.place_code}</p>
                <p><strong>レース:</strong> ${d.race_num}R</p>
                <p><strong>式別:</strong> ${d.bet_type}</p>
                <p><strong>詳細:</strong> ${d.buy_details}</p>
                <p><strong>金額:</strong> ${d.amount}円</p>
            </div>
        `;
        document.getElementById("parsed-data").innerHTML = html;
        document.getElementById("scan-result").style.display = "block";

        // Setup Submit Button
        document.getElementById("submit-scan-btn").onclick = function () {
            registerBet(d);
        };

    } catch (e) {
        console.error(e);
        document.getElementById("parsed-data").innerText = "エラー: " + e.message;
        // Allow retry
        const retryBtn = document.createElement("button");
        retryBtn.innerText = "再スキャン";
        retryBtn.className = "btn btn-secondary";
        retryBtn.onclick = function () { location.reload(); };
        document.getElementById("parsed-data").appendChild(retryBtn);
    }
}

async function registerBet(ticketItem) {
    try {
        const response = await fetch('/api/bets', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ tickets: [ticketItem] })
        });

        if (!response.ok) throw new Error("登録エラー");

        const res = await response.json();
        alert("登録しました！");
        location.reload();

    } catch (e) {
        alert("登録に失敗しました: " + e.message);
    }
}
