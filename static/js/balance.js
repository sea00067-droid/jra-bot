const LIFF_ID = "2009134533-h8bU1BkZ";
let balanceChart = null;

document.addEventListener("DOMContentLoaded", function () {
    // Initialize LIFF
    liff.init({ liffId: LIFF_ID })
        .then(() => {
            if (!liff.isLoggedIn()) {
                liff.login();
            }
        })
        .catch((err) => {
            console.error(err);
        });

    // Set default month to current
    const dateInput = document.getElementById("month-select");
    const now = new Date();
    const yyyy = now.getFullYear();
    const mm = String(now.getMonth() + 1).padStart(2, '0');
    dateInput.value = `${yyyy}-${mm}`;

    // Add event listener
    dateInput.addEventListener("change", loadData);

    // Initial load
    loadData();
});

async function loadData() {
    const val = document.getElementById("month-select").value; // "YYYY-MM"
    if (!val) return;

    const [year, month] = val.split("-");

    try {
        const response = await fetch(`/api/balance/${year}/${parseInt(month)}`); // parseInt to remove leading zero if backend expects int
        if (!response.ok) throw new Error("API Error");

        const data = await response.json();
        renderDashboard(data, year, month);

    } catch (e) {
        console.error(e);
        alert("データの取得に失敗しました");
    }
}

function renderDashboard(data, year, month) {
    // 1. Text Summary
    document.getElementById("total-bet").innerText = data.total_bet.toLocaleString();
    document.getElementById("total-return").innerText = data.total_return.toLocaleString();
    const balEl = document.getElementById("balance");
    balEl.innerText = (data.balance > 0 ? "+" : "") + data.balance.toLocaleString();

    if (data.balance > 0) balEl.style.color = "gold";
    else if (data.balance < 0) balEl.style.color = "#ff4d4d";
    else balEl.style.color = "white";

    // 2. Calendar Grid
    renderCalendar(data.details, year, month);

    // 3. Chart
    renderChart(data.details, year, month);
}

function renderCalendar(details, year, month) {
    const grid = document.getElementById("calendar-grid");
    grid.innerHTML = ""; // Clear

    // Create map for O(1) lookup
    const dailyMap = {};
    if (details) {
        details.forEach(d => dailyMap[d.date] = d);
    }

    const yearInt = parseInt(year);
    const monthInt = parseInt(month); // 1-12

    const daysInMonth = new Date(yearInt, monthInt, 0).getDate();

    for (let day = 1; day <= daysInMonth; day++) {
        const dateStr = `${year}-${String(month).padStart(2, '0')}-${String(day).padStart(2, '0')}`;

        const cell = document.createElement("div");
        cell.className = "day-cell";

        const dayNum = document.createElement("div");
        dayNum.innerText = day;
        cell.appendChild(dayNum);

        if (dailyMap[dateStr]) {
            const info = dailyMap[dateStr];
            const balance = info.balance;

            const balText = document.createElement("div");
            balText.style.fontSize = "10px";
            balText.innerText = (balance > 0 ? "+" : "") + balance;
            cell.appendChild(balText);

            if (balance > 0) cell.classList.add("win");
            else if (balance < 0) cell.classList.add("loss");
        }

        grid.appendChild(cell);
    }
}

function renderChart(details, year, month) {
    const ctx = document.getElementById("balanceChart").getContext("2d");

    if (balanceChart) {
        balanceChart.destroy();
    }

    // Prepare data
    // We want cumulative balance over days
    // details only has existing days. We should fill valid days or just plot points.
    // Let's just plot active days for simplicity

    let labels = [];
    let dataPoints = [];
    let cumulative = 0;

    if (details) {
        details.forEach(d => {
            labels.push(d.date.substring(5)); // MM-DD
            cumulative += d.balance;
            dataPoints.push(cumulative);
        });
    }

    balanceChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: '累積収支',
                data: dataPoints,
                borderColor: '#00b900',
                backgroundColor: 'rgba(0, 185, 0, 0.1)',
                tension: 0.1,
                fill: true
            }]
        },
        options: {
            responsive: true,
            scales: {
                y: {
                    grid: { color: '#444' },
                    ticks: { color: '#ccc' }
                },
                x: {
                    grid: { color: '#444' },
                    ticks: { color: '#ccc' }
                }
            },
            plugins: {
                legend: { labels: { color: '#fff' } }
            }
        }
    });
}
