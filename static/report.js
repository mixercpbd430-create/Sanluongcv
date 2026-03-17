/* ============================================
   REPORT PAGE - Daily Report Logic
   Fetches data from /api/report/<day>
   ============================================ */

let currentDay = 1;
let saveTimers = {};  // debounce timers for auto-save

document.addEventListener('DOMContentLoaded', () => {
    updateSubtitle();

    // Highlight days that have production data
    if (typeof DAYS_WITH_DATA !== 'undefined' && DAYS_WITH_DATA.length > 0) {
        DAYS_WITH_DATA.forEach(day => {
            const btn = document.getElementById(`day-btn-${day}`);
            if (btn) btn.classList.add('has-data');
        });

        // Default to the latest day with completed data
        currentDay = DAYS_WITH_DATA[DAYS_WITH_DATA.length - 1];
    } else {
        currentDay = 1;
    }

    // Auto-save SALE/STOCK inputs on change (debounced 500ms)
    const saleInput = document.getElementById('sale-input');
    const stockInput = document.getElementById('stock-input');

    if (saleInput) {
        saleInput.addEventListener('input', () => debounceAutoSave('sale', saleInput));
    }
    if (stockInput) {
        stockInput.addEventListener('input', () => debounceAutoSave('stock', stockInput));
    }

    selectDay(currentDay);
});

function updateSubtitle() {
    const sel = AVAILABLE_MONTHS.find(m => m.key === SELECTED_MONTH);
    const label = sel ? sel.label : '';
    document.getElementById('report-subtitle').textContent = label;
}

function changeMonth(monthKey) {
    window.location.href = `/report?month=${monthKey}`;
}

function selectDay(day) {
    currentDay = day;

    // Update active button
    document.querySelectorAll('.day-btn').forEach(btn => {
        btn.classList.toggle('active', parseInt(btn.dataset.day) === day);
    });

    // Update day display
    document.getElementById('cell-day').textContent = day;

    // Update title
    const parts = SELECTED_MONTH.split('-');
    const monthNum = parseInt(parts[1]);
    const year = parts[0];
    document.getElementById('report-title').textContent =
        `SẢN LƯỢNG THÁNG ${monthNum}.${year}`;

    // Clear inputs before fetching (avoid showing stale data)
    document.getElementById('sale-input').value = '';
    document.getElementById('stock-input').value = '';

    // Fetch data
    loadDayReport(day);
}

function loadDayReport(day) {
    fetch(`/api/report/${day}?month=${SELECTED_MONTH}`)
        .then(res => res.json())
        .then(data => {
            renderReport(data);
        })
        .catch(err => {
            console.error('Load report failed:', err);
        });
}

function fmtVal(num) {
    if (!num || num === 0) return '-';
    return num.toLocaleString('vi-VN', { minimumFractionDigits: 1, maximumFractionDigits: 1 });
}

function renderReport(data) {
    // MIXER row
    const m = data.mixer;
    document.getElementById('mixer-ca1').textContent = fmtVal(m.ca1);
    document.getElementById('mixer-ca2').textContent = fmtVal(m.ca2);
    document.getElementById('mixer-ca3').textContent = fmtVal(m.ca3);
    document.getElementById('mixer-total').textContent = fmtVal(m.total);

    // Cám bột
    document.getElementById('cam-bot-val').textContent = fmtVal(m.cam_bot);

    // Total Pellet
    const tp = data.total_pellet;
    document.getElementById('tp-ca1').textContent = fmtVal(tp.ca1);
    document.getElementById('tp-ca2').textContent = fmtVal(tp.ca2);
    document.getElementById('tp-ca3').textContent = fmtVal(tp.ca3);
    document.getElementById('tp-total').textContent = fmtVal(tp.total);

    // PL1-PL7
    for (let i = 0; i < data.pellets.length; i++) {
        const pl = data.pellets[i];
        const num = i + 1;
        document.getElementById(`pl${num}-ca1`).textContent = fmtVal(pl.ca1);
        document.getElementById(`pl${num}-ca2`).textContent = fmtVal(pl.ca2);
        document.getElementById(`pl${num}-ca3`).textContent = fmtVal(pl.ca3);
        document.getElementById(`pl${num}-total`).textContent = fmtVal(pl.total);
    }

    // SALE/STOCK — load saved values or leave empty
    const saleInput = document.getElementById('sale-input');
    const stockInput = document.getElementById('stock-input');

    saleInput.value = (data.sale !== null && data.sale !== undefined) ? data.sale : '';
    stockInput.value = (data.stock !== null && data.stock !== undefined) ? data.stock : '';

    // Animate values
    document.querySelectorAll('.report-table .value-cell, .report-table .total-cell').forEach(cell => {
        cell.style.animation = 'none';
        cell.offsetHeight; // trigger reflow
        cell.style.animation = 'fadeInUp 0.3s ease forwards';
    });
}

// ---- Auto-save SALE/STOCK ----

function debounceAutoSave(field, inputEl) {
    // Clear previous timer for this field
    if (saveTimers[field]) clearTimeout(saveTimers[field]);

    // Set visual feedback: typing...
    inputEl.style.borderColor = '#f59e0b';

    // Save after 500ms of no typing
    saveTimers[field] = setTimeout(() => {
        const value = parseFloat(inputEl.value);
        if (isNaN(value) && inputEl.value === '') {
            // User cleared the field — save as 0 to represent "no input"
            // But we actually want to leave it empty, so don't save
            inputEl.style.borderColor = '';
            return;
        }
        if (isNaN(value)) {
            inputEl.style.borderColor = '#ef4444'; // red = invalid
            return;
        }
        saveManualInput(field, value, inputEl);
    }, 500);
}

function saveManualInput(field, value, inputEl) {
    fetch('/api/manual-input', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            month: SELECTED_MONTH,
            day: currentDay,
            field: field,
            value: value,
        }),
    })
    .then(res => res.json())
    .then(data => {
        if (data.status === 'ok') {
            // Green flash = saved
            inputEl.style.borderColor = '#10b981';
            setTimeout(() => { inputEl.style.borderColor = ''; }, 1500);
        }
    })
    .catch(err => {
        console.error('Save failed:', err);
        inputEl.style.borderColor = '#ef4444';
    });
}
