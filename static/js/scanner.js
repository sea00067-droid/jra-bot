const LIFF_ID = "2009134533-h8bU1BkZ";

document.addEventListener("DOMContentLoaded", function () {
    // Initialize LIFF
    liff.init({ liffId: LIFF_ID })
        .then(() => {
            if (!liff.isLoggedIn()) {
                liff.login();
            }
        })
        .catch((err) => {
            console.error("LIFF Init Error", err);
        });

    // File Upload Handler
    const fileInput = document.getElementById("file-input");
    const selectBtn = document.getElementById("select-file-btn");

    selectBtn.addEventListener("click", () => {
        fileInput.click();
    });

    fileInput.addEventListener("change", async (e) => {
        const file = e.target.files[0];
        if (!file) return;
        await handleFileUpload(file);
    });

    // Manual Form Toggle
    const manualHeader = document.getElementById("toggle-manual");
    const manualForm = document.getElementById("manual-form");

    manualHeader.addEventListener("click", () => {
        if (manualForm.style.display === "none") {
            manualForm.style.display = "block";
            manualHeader.querySelector(".toggle-icon").innerText = "▲";
        } else {
            manualForm.style.display = "none";
            manualHeader.querySelector(".toggle-icon").innerText = "▼";
        }
    });

    // Manual Submit
    document.getElementById("add-manual-btn").addEventListener("click", registerManualBet);

    // Initial Race Options
    const raceSelect = document.getElementById("race-num");
    for (let i = 1; i <= 12; i++) {
        let opt = document.createElement("option");
        opt.value = i;
        opt.text = i + "R";
        raceSelect.add(opt);
    }
});

async function handleFileUpload(file) {
    showLoading(true);
    const formData = new FormData();
    formData.append("file", file);

    try {
        const response = await fetch('/api/scan_image', {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.detail || "解析エラー");
        }

        const res = await response.json();
        if (res.status === "failed") throw new Error(res.message);

        showParsedResult(res.data);

    } catch (e) {
        console.error(e);
        alert("読み取りに失敗しました: " + e.message + "\nもう一度、近づきすぎずズームして撮影してみてください。");
    } finally {
        showLoading(false);
        // Reset input to allow selecting same file again
        document.getElementById("file-input").value = "";
    }
}

function showParsedResult(d) {
    const container = document.getElementById("scan-result");
    const content = document.getElementById("parsed-data");

    container.style.display = "block";
    content.innerHTML = `
        <div class="result-item"><strong>場所:</strong> <span>${d.place_code}</span></div>
        <div class="result-item"><strong>レース:</strong> <span>${d.race_num}R</span></div>
        <div class="result-item"><strong>式別:</strong> <span>${d.bet_type}</span></div>
        <div class="result-item"><strong>買い目:</strong> <span>${d.buy_details}</span></div>
        <div class="result-item"><strong>金額:</strong> <span>${d.amount}円</span></div>
    `;

    // Clear old buttons
    const oldBtn = document.getElementById("submit-scan-btn");
    if (oldBtn) oldBtn.remove();

    const btn = document.createElement("button");
    btn.id = "submit-scan-btn";
    btn.className = "btn btn-success btn-block";
    btn.innerText = "この内容で登録する";
    btn.onclick = () => registerBet(d);

    container.appendChild(btn);

    // Scroll to result
    container.scrollIntoView({ behavior: 'smooth' });
}

async function registerBet(ticketItem) {
    if (!confirm("登録しますか？")) return;

    try {
        const response = await fetch('/api/bets', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ tickets: [ticketItem] })
        });

        if (!response.ok) throw new Error("登録エラー");

        alert("登録しました！");
        location.reload();

    } catch (e) {
        alert("登録に失敗しました: " + e.message);
    }
}

function registerManualBet() {
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

function showLoading(show) {
    const el = document.getElementById("loading");
    if (el) el.style.display = show ? "flex" : "none";
}
