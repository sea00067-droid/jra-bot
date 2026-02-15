const LIFF_ID = "2009134533-h8bU1BkZ";
let scannedCodes = []; // To store 1st and 2nd QR parts

document.addEventListener("DOMContentLoaded", function () {
    // Tab switching
    document.getElementById("tab-scan").addEventListener("click", () => switchTab("scan"));
    document.getElementById("tab-upload").addEventListener("click", () => switchTab("upload"));
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

    // Native Scan Button
    document.getElementById("start-native-scan-btn").addEventListener("click", startNativeScan);

    // File Upload Setup
    document.getElementById("select-file-btn").addEventListener("click", () => {
        document.getElementById("file-input").click();
    });
    document.getElementById("file-input").addEventListener("change", (e) => handleFileUpload(e));

    // Manual Entry Setup
    document.getElementById("add-manual-btn").addEventListener("click", registerManualBet);

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
    // Hide all
    document.getElementById("scan-view").style.display = "none";
    document.getElementById("upload-view").style.display = "none";
    document.getElementById("manual-view").style.display = "none";
    document.getElementById("scan-result").style.display = "none";

    // Deactivate tabs
    document.getElementById("tab-scan").classList.remove("active");
    document.getElementById("tab-upload").classList.remove("active");
    document.getElementById("tab-manual").classList.remove("active");

    // Activate target
    if (mode === "scan") {
        document.getElementById("scan-view").style.display = "block";
        document.getElementById("tab-scan").classList.add("active");
    } else if (mode === "upload") {
        document.getElementById("upload-view").style.display = "block";
        document.getElementById("tab-upload").classList.add("active");
    } else {
        document.getElementById("manual-view").style.display = "block";
        document.getElementById("tab-manual").classList.add("active");
    }
}

// --- NATIVE SCAN LOGIC ---
function startNativeScan() {
    if (!liff.isInClient()) {
        alert("この機能はLINEアプリ内でのみ使用できます。");
        return;
    }

    if (!liff.scanCode && !liff.scanCodeV2) {
        alert("この環境ではQRスキャン機能が利用できません。");
        return;
    }

    // Try V2 first, then V1
    const scanFunc = liff.scanCodeV2 ? liff.scanCodeV2 : liff.scanCode;

    scanFunc().then(result => {
        const decodedText = result.value;
        if (!decodedText) return;
        handleScannedText(decodedText);
    }).catch(err => {
        console.error(err);
        alert("スキャンエラー: " + err);
    });
}

function handleScannedText(text) {
    if (scannedCodes.includes(text)) return;
    scannedCodes.push(text);

    // Show intermediate status
    document.getElementById("parsed-data").innerText = `${scannedCodes.length}個目のQRを読み取りました`;
    document.getElementById("scan-result").style.display = "block";

    if (scannedCodes.length < 2) {
        if (confirm("1つ目のQRを読み取りました。\n続けて2つ目をスキャンしますか？")) {
            startNativeScan();
        } else {
            // Processing with what we have
            processScannedData();
        }
    } else {
        processScannedData();
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
        showParsedResult(res.data);

    } catch (e) {
        console.error(e);
        document.getElementById("parsed-data").innerText = "エラー: " + e.message;
        addRetryButton();
    }
}

// --- PHOTO UPLOAD LOGIC ---
async function handleFileUpload(event) {
    const file = event.target.files[0];
    if (!file) return;

    document.getElementById("parsed-data").innerText = "アップロード中...";
    document.getElementById("scan-result").style.display = "block";

    const formData = new FormData();
    formData.append("file", file);

    try {
        const response = await fetch('/api/scan_image', {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.detail || err.message || "解析エラー");
        }

        const res = await response.json();
        if (res.status === "failed") throw new Error(res.message);

        showParsedResult(res.data);

    } catch (e) {
        console.error(e);
        document.getElementById("parsed-data").innerText = "エラー: " + e.message;
        addRetryButton();
    }
}

// --- MANUAL ENTRY LOGIC ---
function registerManualBet() {
    const place = document.getElementById("place").value; // e.g. "05" -> "東京" (Need to map?)
    // Actually the value is "05", "01" etc.
    // The select options have text "東京" but value "05".
    // Let's assume backend expects Place Name or Code?
    // Current backend implementation of calculator.add_bet expects "place_code" string.
    // Let's send the text for display, or value? 
    // JRAParser logic returns "東京" (name). 
    // Let's get the text from the select.
    const placeSelect = document.getElementById("place");
    const placeName = placeSelect.options[placeSelect.selectedIndex].text;

    const raceNum = parseInt(document.getElementById("race-num").value);
    const betType = document.getElementById("bet-type").value;
    const buyDetails = document.getElementById("buy-details").value;
    const amount = parseInt(document.getElementById("amount").value);

    if (!amount || !buyDetails) {
        alert("必須項目を入力してください");
        return;
    }

    const ticket = {
        place_code: placeName,
        race_num: raceNum,
        bet_type: betType,
        buy_details: buyDetails,
        amount: amount
    };

    registerBet(ticket);
}


// --- SHARED UI LOGIC ---

function showParsedResult(d) {
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

    // Clear old buttons
    const oldBtn = document.getElementById("submit-scan-btn");
    if (oldBtn) oldBtn.remove();
    const oldRetry = document.getElementById("retry-btn");
    if (oldRetry) oldRetry.remove();

    const btn = document.createElement("button");
    btn.id = "submit-scan-btn";
    btn.className = "btn btn-primary";
    btn.innerText = "登録する";
    btn.onclick = function () { registerBet(d); };
    document.getElementById("scan-result").appendChild(btn);
}

function addRetryButton() {
    const oldRetry = document.getElementById("retry-btn");
    if (oldRetry) oldRetry.remove();

    const retryBtn = document.createElement("button");
    retryBtn.id = "retry-btn";
    retryBtn.innerText = "やり直す";
    retryBtn.className = "btn btn-secondary";
    retryBtn.style.marginTop = "10px";
    retryBtn.onclick = function () {
        scannedCodes = [];
        location.reload();
    };
    document.getElementById("parsed-data").appendChild(retryBtn);
}

async function registerBet(ticketItem) {
    try {
        const response = await fetch('/api/bets', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ tickets: [ticketItem] })
        });

        if (!response.ok) throw new Error("登録エラー");

        alert("登録しました！");
        scannedCodes = [];
        location.reload();

    } catch (e) {
        alert("登録に失敗しました: " + e.message);
    }
}
