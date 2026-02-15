const LIFF_ID = "2009134533-h8bU1BkZ";
let scannedCodes = []; // To store 1st and 2nd QR parts

document.addEventListener("DOMContentLoaded", function () {
    // Manual tab toggle
    document.getElementById("tab-manual").addEventListener("click", () => {
        document.getElementById("scan-view").style.display = "none";
        document.getElementById("manual-view").style.display = "block";
    });

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
            alert("LIFF Init Failed: " + err);
        });

    // Native Scan Button
    document.getElementById("start-native-scan-btn").addEventListener("click", startNativeScan);

    // Initial race num population
    const raceSelect = document.getElementById("race-num");
    for (let i = 1; i <= 12; i++) {
        let opt = document.createElement("option");
        opt.value = i;
        opt.text = i + "R";
        raceSelect.add(opt);
    }
});

function startNativeScan() {
    if (!liff.isInClient()) {
        alert("この機能はLINEアプリ内でのみ使用できます。");
        return;
    }

    // Check if scanCode is available (it might be deprecated/removed in some envs)
    if (!liff.scanCode && !liff.scanCodeV2) {
        alert("この環境ではQRスキャン機能が利用できません。");
        return;
    }

    // Try V2 first, then V1
    const scanFunc = liff.scanCodeV2 ? liff.scanCodeV2 : liff.scanCode;

    scanFunc().then(result => {
        // result.value contains the string
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

    // JRA tickets have 2 codes. 
    // If 1st scanned, ask for 2nd?
    // Native scanner closes after 1 scan.
    // We need to ask user to scan again if length < 2.

    if (scannedCodes.length < 2) {
        if (confirm("1つ目のQRを読み取りました。\n続けて2つ目をスキャンしますか？")) {
            startNativeScan();
        } else {
            // User canceled 2nd scan, try processing anyway?
            processScannedData();
        }
    } else {
        processScannedData();
    }
}

async function processScannedData() {
    let combined = scannedCodes.join("");
    document.getElementById("parsed-data").innerText = "解析中... (" + combined.length + "桁)";

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
        // Remove existing button to avoid dupes
        const oldBtn = document.getElementById("submit-scan-btn");
        if (oldBtn) oldBtn.remove();

        const btn = document.createElement("button");
        btn.id = "submit-scan-btn";
        btn.className = "btn btn-primary";
        btn.innerText = "登録する";
        btn.onclick = function () { registerBet(d); };
        document.getElementById("scan-result").appendChild(btn);

    } catch (e) {
        console.error(e);
        document.getElementById("parsed-data").innerText = "エラー: " + e.message;

        const retryBtn = document.createElement("button");
        retryBtn.innerText = "最初からやり直す";
        retryBtn.className = "btn btn-secondary";
        retryBtn.onclick = function () {
            scannedCodes = [];
            location.reload();
        };
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

        alert("登録しました！");
        scannedCodes = [];
        location.reload();

    } catch (e) {
        alert("登録に失敗しました: " + e.message);
    }
}
