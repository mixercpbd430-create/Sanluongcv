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
    document.getElementById('report-subtitle').textContent = `Nhà Máy Bình Dương — ${label}`;
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
    // 1) Load production data (fast — from DB)
    fetch(`/api/report/${day}?month=${SELECTED_MONTH}`)
        .then(res => res.json())
        .then(data => {
            renderReport(data);
        })
        .catch(err => {
            console.error('Load report failed:', err);
        });

    // 2) Load NVVH + LOSS details (slower — reads Excel files)
    fetch(`/api/report/${day}/details?month=${SELECTED_MONTH}`)
        .then(res => res.json())
        .then(details => {
            renderNVVH(details.nvvh);
            renderLossNotes(details.loss_notes);
        })
        .catch(err => {
            console.error('Load NVVH/LOSS failed:', err);
        });

    // 3) Load loss summary tables (daily, MTD, monthly comparison)
    fetch(`/api/report/${day}/loss-summary?month=${SELECTED_MONTH}`)
        .then(res => res.json())
        .then(data => {
            renderLossSummary(data);
        })
        .catch(err => {
            console.error('Load loss summary failed:', err);
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

function renderNVVH(nvvh) {
    if (!nvvh) return;

    const cas = ['ca1', 'ca2', 'ca3'];
    // PL1-5 mapping: 3 operators → PL1, PL3, PL5 (each covers adjacent PL too)
    const pl15_slots = [1, 3, 5]; // PL numbers that get names
    // PL6-7: 1 operator → both PL6 and PL7

    cas.forEach(ca => {
        // Clear all NVVH cells for this Ca (including Mixer)
        const mixerEl = document.getElementById(`nvvh-${ca}-mixer`);
        if (mixerEl) mixerEl.textContent = '';
        for (let i = 1; i <= 7; i++) {
            const el = document.getElementById(`nvvh-${ca}-pl${i}`);
            if (el) el.textContent = '';
        }

        // Mixer NVVH
        const mixerName = nvvh.mixer ? (nvvh.mixer[ca] || '') : '';
        if (mixerEl && mixerName) mixerEl.textContent = mixerName;

        // PL1-5: split names to PL1, PL3, PL5
        const names15 = nvvh.pl1_5 ? (nvvh.pl1_5[ca] || []) : [];
        names15.forEach((name, idx) => {
            if (idx < pl15_slots.length) {
                const el = document.getElementById(`nvvh-${ca}-pl${pl15_slots[idx]}`);
                if (el) el.textContent = name;
            }
        });

        // PL6-7: same operator for both
        const name67 = nvvh.pl6_7 ? (nvvh.pl6_7[ca] || '') : '';
        const el6 = document.getElementById(`nvvh-${ca}-pl6`);
        const el7 = document.getElementById(`nvvh-${ca}-pl7`);
        if (el6) el6.textContent = name67;
        if (el7) el7.textContent = '';  // only show name on PL6 row
    });
}

function renderLossNotes(lossNotes) {
    // Clear all note, time, and downtime cells (0=Mixer, 1-7=PL)
    ['ca1', 'ca2', 'ca3'].forEach(ca => {
        for (let i = 0; i <= 7; i++) {
            const el = document.getElementById(`note-${ca}-${i}`);
            if (el) el.textContent = '';
            const timeEl = document.getElementById(`time-${ca}-${i}`);
            if (timeEl) timeEl.textContent = '';
        }
    });
    for (let i = 0; i <= 7; i++) {
        const dtEl = document.getElementById(`dt-val-${i}`);
        if (dtEl) dtEl.textContent = '-';
    }

    if (!lossNotes) return;

    // Track daily total per machine (0=Mixer, 1-7=PL)
    const dailyTotals = {};
    for (let pl = 0; pl <= 7; pl++) dailyTotals[pl] = 0;

    // lossNotes = {"0": [...], "1": [...], ..., "7": [...]}
    for (let pl = 0; pl <= 7; pl++) {
        const entries = lossNotes[String(pl)] || [];
        if (entries.length === 0) continue;

        ['ca1', 'ca2', 'ca3'].forEach(ca => {
            const caEntries = [];
            let totalTime = 0;
            entries.forEach(loss => {
                if (loss[`${ca}_count`] > 0 || loss[`${ca}_time`] > 0) {
                    caEntries.push(fmtLoss(loss, ca));
                    totalTime += (loss[`${ca}_time`] || 0);
                }
            });

            if (caEntries.length > 0) {
                const el = document.getElementById(`note-${ca}-${pl}`);
                if (el) el.textContent = caEntries.join(' | ');
            }

            // Display per-CA time
            if (totalTime > 0) {
                const timeEl = document.getElementById(`time-${ca}-${pl}`);
                if (timeEl) timeEl.textContent = fmtTotalTime(totalTime);
            }

            dailyTotals[pl] += totalTime;
        });
    }

    // Display daily totals per machine
    for (let pl = 0; pl <= 7; pl++) {
        const dtEl = document.getElementById(`dt-val-${pl}`);
        if (dtEl) {
            dtEl.textContent = dailyTotals[pl] > 0 ? fmtTotalTime(dailyTotals[pl]) : '-';
        }
    }
}

function fmtLoss(loss, caKey) {
    const count = loss[`${caKey}_count`];
    const time = loss[`${caKey}_time`];
    let parts = [`Loss ${loss.code}: ${loss.desc}`];
    if (count > 0) parts.push(`${count} lần`);
    if (time > 0) parts.push(`${time}'`);
    return parts.join(', ');
}

function fmtTotalTime(minutes) {
    if (minutes <= 0) return '';
    const h = Math.floor(minutes / 60);
    const m = minutes % 60;
    if (h > 0 && m > 0) return `${h}h${m}'`;
    if (h > 0) return `${h}h`;
    return `${m}'`;
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


// ---- Loss Summary Tables ----

function renderLossSummary(data) {
    if (!data) return;

    const parts = SELECTED_MONTH.split('-');
    const monthNum = parseInt(parts[1]);
    const year = parts[0];

    // Table 1: Daily loss detail
    const titleDaily = document.getElementById('loss-daily-title');
    if (titleDaily) {
        titleDaily.innerHTML = `
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/>
            </svg>
            TỔNG KẾT LOSS TRONG NGÀY ${data.day}/${monthNum}/${year}`;
    }
    renderDailyLossDetail(data.daily_detail, data.daily);

    // Table 2: Month-to-date loss
    const titleMtd = document.getElementById('loss-mtd-title');
    if (titleMtd) {
        titleMtd.innerHTML = `
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <rect x="3" y="4" width="18" height="18" rx="2" ry="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/>
            </svg>
            TỔNG KẾT LOSS TỪ NGÀY 1 ĐẾN NGÀY ${data.day} — THÁNG ${monthNum}/${year}`;
    }
    setLossTableRow('lm', data.mtd);

    // Table 3: Monthly comparison
    const compareBody = document.getElementById('loss-compare-body');
    if (compareBody && data.monthly) {
        compareBody.innerHTML = '';
        const currentMonth = data.current_month;

        // Get sorted month keys
        const monthKeys = Object.keys(data.monthly).map(Number).sort((a, b) => a - b);

        monthKeys.forEach(m => {
            const mData = data.monthly[String(m)];
            const isCurrent = (m === currentMonth);
            const tr = document.createElement('tr');
            tr.className = `loss-month-row${isCurrent ? ' loss-month-current' : ''}`;

            // Label cell
            const tdLabel = document.createElement('td');
            tdLabel.className = 'loss-row-label';
            tdLabel.textContent = `Tháng ${m}/${year}`;
            if (isCurrent) tdLabel.textContent += ' ★';
            tr.appendChild(tdLabel);

            // Machine cells (0=Mixer, 1-7=PL)
            let total = 0;
            for (let pl = 0; pl <= 7; pl++) {
                const td = document.createElement('td');
                td.className = 'loss-val';
                const val = mData[String(pl)] || 0;
                td.textContent = val > 0 ? fmtTotalTime(val) : '-';
                total += val;
                tr.appendChild(td);
            }

            // Total cell
            const tdTotal = document.createElement('td');
            tdTotal.className = 'loss-val loss-total-val';
            tdTotal.textContent = total > 0 ? fmtTotalTime(total) : '-';
            tr.appendChild(tdTotal);

            compareBody.appendChild(tr);
        });
    }
}

function setLossTableRow(prefix, lossData) {
    if (!lossData) return;
    let total = 0;
    for (let pl = 0; pl <= 7; pl++) {
        const el = document.getElementById(`${prefix}-${pl}`);
        const val = lossData[String(pl)] || 0;
        if (el) el.textContent = val > 0 ? fmtTotalTime(val) : '-';
        total += val;
    }
    const totalEl = document.getElementById(`${prefix}-total`);
    if (totalEl) totalEl.textContent = total > 0 ? fmtTotalTime(total) : '-';
}

function renderDailyLossDetail(detail, dailyTotals) {
    const body = document.getElementById('loss-daily-body');
    if (!body) return;
    body.innerHTML = '';

    const machineNames = ['MIXER', 'PL1', 'PL2', 'PL3', 'PL4', 'PL5', 'PL6', 'PL7'];
    const machineClasses = ['ldt-mixer', '', '', '', '', '', 'ldt-pl67', 'ldt-pl67'];
    let grandTotal = 0;

    for (let pl = 0; pl <= 7; pl++) {
        const entries = (detail && detail[String(pl)]) ? detail[String(pl)] : [];
        const totalTime = (dailyTotals && dailyTotals[String(pl)]) ? dailyTotals[String(pl)] : 0;
        grandTotal += totalTime;

        const tr = document.createElement('tr');
        tr.className = `ldt-row ${machineClasses[pl]}`;

        // Machine name cell
        const tdMachine = document.createElement('td');
        tdMachine.className = 'ldt-machine-cell';
        tdMachine.textContent = machineNames[pl];
        tr.appendChild(tdMachine);

        // Detail cell
        const tdDetail = document.createElement('td');
        tdDetail.className = 'ldt-detail-cell';
        if (entries.length > 0) {
            const parts = entries.map(e => {
                let s = `Loss ${e.code}: ${e.desc}`;
                if (e.total_count > 0) s += `, ${e.total_count} lần`;
                if (e.total_time > 0) s += `, ${e.total_time}'`;
                return s;
            });
            tdDetail.textContent = parts.join(' | ');
        } else {
            tdDetail.textContent = '-';
            tdDetail.style.textAlign = 'center';
            tdDetail.style.color = '#9ca3af';
        }
        tr.appendChild(tdDetail);

        // Total time cell
        const tdTime = document.createElement('td');
        tdTime.className = 'ldt-time-cell';
        tdTime.textContent = totalTime > 0 ? fmtTotalTime(totalTime) : '-';
        tr.appendChild(tdTime);

        body.appendChild(tr);
    }

    // Grand total row
    const trTotal = document.createElement('tr');
    trTotal.className = 'ldt-row ldt-total-row';
    const tdTotalLabel = document.createElement('td');
    tdTotalLabel.className = 'ldt-machine-cell ldt-total-label';
    tdTotalLabel.textContent = 'TỔNG';
    tdTotalLabel.colSpan = 2;
    trTotal.appendChild(tdTotalLabel);
    const tdGrandTotal = document.createElement('td');
    tdGrandTotal.className = 'ldt-time-cell ldt-grand-total';
    tdGrandTotal.textContent = grandTotal > 0 ? fmtTotalTime(grandTotal) : '-';
    trTotal.appendChild(tdGrandTotal);
    body.appendChild(trTotal);
}
