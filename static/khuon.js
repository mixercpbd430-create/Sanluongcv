/* ============================================
   THEO DÕI KHUÔN - JavaScript
   Renders daily & monthly mold tracking tables
   ============================================ */

let currentView = 'daily';     // 'daily' or 'monthly'
let currentPL = 'ALL';         // 'ALL' or 'PL1'..'PL7'
let hideZeroRows = true;       // Default: hide zero rows
let dailyData = null;          // From server (KHUON_DATA)
let monthlyData = null;        // Fetched via API

// ---- Initialize ----
document.addEventListener('DOMContentLoaded', () => {
    dailyData = typeof KHUON_DATA !== 'undefined' ? KHUON_DATA : {};
    // Set toggle checkboxes to default state
    const cb1 = document.getElementById('toggle-zero-khuon');
    const cb2 = document.getElementById('toggle-zero-khuon-monthly');
    if (cb1) cb1.checked = hideZeroRows;
    if (cb2) cb2.checked = hideZeroRows;
    // Apply hide class
    document.querySelectorAll('.khuon-table-wrap').forEach(wrap => {
        wrap.classList.toggle('hide-zero-rows', hideZeroRows);
    });
    renderStats();
    renderPLFilter();
    renderDailyTable();
});

// ---- Format ----
function fmtNum(num) {
    if (!num || num === 0) return '';
    return num.toLocaleString('vi-VN', { minimumFractionDigits: 1, maximumFractionDigits: 1 });
}

function fmtInt(num) {
    if (!num || num === 0) return '';
    return num.toLocaleString('vi-VN', { minimumFractionDigits: 0, maximumFractionDigits: 1 });
}

// ---- View Switching ----
function switchView(view) {
    currentView = view;

    document.querySelectorAll('.view-tab').forEach(t => {
        t.classList.toggle('active', t.dataset.view === view);
    });
    document.querySelectorAll('.view-section').forEach(s => {
        s.classList.toggle('active', s.id === `view-${view}`);
    });

    if (view === 'monthly' && !monthlyData) {
        loadMonthlyData();
    } else if (view === 'monthly') {
        renderMonthlyTable();
    }
}

// ---- PL Filter ----
function renderPLFilter() {
    const container = document.getElementById('pl-filter');
    if (!container) return;
    container.innerHTML = '';

    // "Tất cả" tab
    const allBtn = document.createElement('button');
    allBtn.className = 'pl-tab active';
    allBtn.dataset.pl = 'ALL';
    allBtn.onclick = () => selectPL('ALL');
    const totalMolds = Object.values(dailyData).reduce((s, arr) => s + arr.length, 0);
    allBtn.innerHTML = `Tất cả<span class="count-badge">${totalMolds}</span>`;
    container.appendChild(allBtn);

    // Individual PL tabs
    for (let i = 1; i <= 7; i++) {
        const plKey = `PL${i}`;
        const molds = dailyData[plKey] || [];
        const btn = document.createElement('button');
        btn.className = 'pl-tab';
        btn.dataset.pl = plKey;
        btn.onclick = () => selectPL(plKey);
        btn.innerHTML = `${plKey}<span class="count-badge">${molds.length}</span>`;
        container.appendChild(btn);
    }
}

function selectPL(pl) {
    currentPL = pl;
    document.querySelectorAll('.pl-tab').forEach(t => {
        t.classList.toggle('active', t.dataset.pl === pl);
    });
    renderStats();
    if (currentView === 'daily') {
        renderDailyTable();
    } else {
        renderMonthlyTable();
    }
}

// ---- Stats ----
function renderStats() {
    const molds = getFilteredMolds();
    const totalKhuon = molds.length;
    const activeKhuon = molds.filter(m => m.tong_thang > 0).length;
    const tongThang = molds.reduce((s, m) => s + m.tong_thang, 0);
    const tongAll = molds.reduce((s, m) => s + m.tong, 0);

    document.getElementById('stat-total-khuon').textContent = totalKhuon;
    document.getElementById('stat-active-khuon').textContent = activeKhuon;
    document.getElementById('stat-tong-thang').textContent = fmtNum(tongThang);
    document.getElementById('stat-tong-all').textContent = fmtNum(tongAll);
}

function getFilteredMolds() {
    if (currentPL === 'ALL') {
        let all = [];
        for (let i = 1; i <= 7; i++) {
            const plKey = `PL${i}`;
            (dailyData[plKey] || []).forEach(m => {
                all.push({ ...m, _pl: plKey });
            });
        }
        return all;
    }
    return (dailyData[currentPL] || []).map(m => ({ ...m, _pl: currentPL }));
}

// ---- Daily Table ----
function renderDailyTable() {
    const container = document.getElementById('daily-table-body');
    const footer = document.getElementById('daily-table-foot');
    const thead = document.getElementById('daily-table-head');
    if (!container) return;

    const molds = getFilteredMolds();
    const daysInMonth = 31;

    // Rebuild header (PL column only when ALL)
    let headerHTML = `
        <th class="sticky-col col-stt">STT</th>
        <th class="sticky-col col-seri">Seri Khuôn</th>
        <th class="sticky-col col-khuon">Khuôn</th>
    `;
    if (currentPL === 'ALL') {
        headerHTML += `<th class="col-day">PL</th>`;
    }
    for (let d = 1; d <= daysInMonth; d++) {
        headerHTML += `<th class="col-day">${d}</th>`;
    }
    headerHTML += `<th class="col-summary">Tổng<br>Tháng</th>`;
    headerHTML += `<th class="col-summary">Tồn<br>Trước</th>`;
    headerHTML += `<th class="col-summary">Tổng</th>`;
    thead.innerHTML = headerHTML;

    container.innerHTML = '';
    footer.innerHTML = '';

    if (molds.length === 0) {
        const colspan = currentPL === 'ALL' ? 38 : 37;
        container.innerHTML = `<tr><td colspan="${colspan}" style="text-align:center;padding:40px;color:var(--text-muted);">Không có dữ liệu khuôn</td></tr>`;
        return;
    }

    // Daily totals for footer
    const dayTotals = {};
    for (let d = 1; d <= daysInMonth; d++) dayTotals[d] = 0;
    let sumTongThang = 0, sumTonTruoc = 0, sumTong = 0;

    molds.forEach((m, idx) => {
        const isZero = m.tong_thang === 0;
        const tr = document.createElement('tr');
        if (isZero) tr.classList.add('row-zero');

        let cells = `
            <td class="sticky-col col-stt">${idx + 1}</td>
            <td class="sticky-col col-seri" title="${m.seri}">${m.seri}</td>
            <td class="sticky-col col-khuon">${m.thong_so}</td>
        `;

        if (currentPL === 'ALL') {
            cells += `<td class="col-pl">${m._pl}</td>`;
        }

        // Day columns
        for (let d = 1; d <= daysInMonth; d++) {
            const val = m.days[d] || 0;
            const cls = val > 0 ? 'has-value' : '';
            cells += `<td class="${cls}">${fmtInt(val)}</td>`;
            dayTotals[d] += val;
        }

        // Summary columns
        cells += `<td class="summary-val tong-thang">${fmtNum(m.tong_thang)}</td>`;
        cells += `<td class="summary-val ton-truoc">${fmtNum(m.ton_truoc)}</td>`;
        cells += `<td class="summary-val tong-all">${fmtNum(m.tong)}</td>`;

        sumTongThang += m.tong_thang;
        sumTonTruoc += m.ton_truoc;
        sumTong += m.tong;

        tr.innerHTML = cells;
        container.appendChild(tr);
    });

    // Footer totals
    const footTr = document.createElement('tr');
    let footCells = `
        <td class="sticky-col col-stt"></td>
        <td class="sticky-col col-seri" style="text-align:left;font-weight:800;">TỔNG CỘNG</td>
        <td class="sticky-col col-khuon"></td>
    `;

    if (currentPL === 'ALL') {
        footCells += `<td></td>`;
    }

    for (let d = 1; d <= daysInMonth; d++) {
        const val = dayTotals[d];
        const cls = val > 0 ? 'has-value' : '';
        footCells += `<td class="${cls}">${fmtNum(val)}</td>`;
    }

    footCells += `<td class="has-value" style="color:var(--accent-cyan);">${fmtNum(sumTongThang)}</td>`;
    footCells += `<td class="has-value" style="color:var(--accent-amber);">${fmtNum(sumTonTruoc)}</td>`;
    footCells += `<td class="has-value" style="color:var(--accent-rose);">${fmtNum(sumTong)}</td>`;

    footTr.innerHTML = footCells;
    footer.appendChild(footTr);
}

// ---- Monthly Table ----
function loadMonthlyData() {
    const loadingEl = document.getElementById('monthly-loading');
    if (loadingEl) loadingEl.style.display = 'flex';

    const year = SELECTED_MONTH.split('-')[0];
    fetch(`/api/khuon/yearly?year=${year}`)
        .then(r => r.json())
        .then(data => {
            monthlyData = data;
            if (loadingEl) loadingEl.style.display = 'none';
            renderMonthlyTable();
        })
        .catch(err => {
            console.error('Failed to load monthly data:', err);
            if (loadingEl) loadingEl.innerHTML = '<span style="color:var(--accent-rose);">Lỗi tải dữ liệu</span>';
        });
}

function renderMonthlyTable() {
    const container = document.getElementById('monthly-table-body');
    const footer = document.getElementById('monthly-table-foot');
    if (!container || !monthlyData) return;

    container.innerHTML = '';
    footer.innerHTML = '';

    // Filter by PL
    let molds = [];
    if (currentPL === 'ALL') {
        for (let i = 1; i <= 7; i++) {
            const plKey = `PL${i}`;
            (monthlyData[plKey] || []).forEach(m => {
                molds.push({ ...m, _pl: plKey });
            });
        }
    } else {
        (monthlyData[currentPL] || []).forEach(m => {
            molds.push({ ...m, _pl: currentPL });
        });
    }

    if (molds.length === 0) {
        container.innerHTML = `<tr><td colspan="17" style="text-align:center;padding:40px;color:var(--text-muted);">Không có dữ liệu</td></tr>`;
        return;
    }

    // Monthly totals
    const monthTotals = {};
    for (let m = 1; m <= 12; m++) monthTotals[m] = 0;
    let yearGrandTotal = 0;

    molds.forEach((m, idx) => {
        const isZero = m.year_total === 0;
        const tr = document.createElement('tr');
        if (isZero) tr.classList.add('row-zero');

        let cells = `
            <td class="sticky-col col-stt">${idx + 1}</td>
            <td class="sticky-col col-seri">${m.seri}</td>
            <td class="sticky-col col-khuon">${m.thong_so}</td>
            <td class="col-pl">${m._pl}</td>
        `;

        for (let mo = 1; mo <= 12; mo++) {
            const val = m.months[mo] || 0;
            const cls = val > 0 ? 'has-value' : '';
            cells += `<td class="${cls}">${fmtNum(val)}</td>`;
            monthTotals[mo] += val;
        }

        cells += `<td class="summary-val tong-all">${fmtNum(m.year_total)}</td>`;
        yearGrandTotal += m.year_total;

        tr.innerHTML = cells;
        container.appendChild(tr);
    });

    // Footer
    const footTr = document.createElement('tr');
    let footCells = `
        <td class="sticky-col col-stt"></td>
        <td class="sticky-col col-seri" style="text-align:left;font-weight:800;">TỔNG CỘNG</td>
        <td class="sticky-col col-khuon"></td>
        <td></td>
    `;
    for (let mo = 1; mo <= 12; mo++) {
        const val = monthTotals[mo];
        const cls = val > 0 ? 'has-value' : '';
        footCells += `<td class="${cls}">${fmtNum(val)}</td>`;
    }
    footCells += `<td class="has-value" style="color:var(--accent-rose);">${fmtNum(yearGrandTotal)}</td>`;
    footTr.innerHTML = footCells;
    footer.appendChild(footTr);
}

// ---- Toggle zero rows ----
function toggleZeroKhuon() {
    // Read from whichever checkbox triggered
    const cb1 = document.getElementById('toggle-zero-khuon');
    const cb2 = document.getElementById('toggle-zero-khuon-monthly');
    hideZeroRows = (cb1 && cb1.checked) || (cb2 && cb2.checked);
    // Sync both checkboxes
    if (cb1) cb1.checked = hideZeroRows;
    if (cb2) cb2.checked = hideZeroRows;
    // Toggle one class on containers → CSS hides all .row-zero instantly
    document.querySelectorAll('.khuon-table-wrap').forEach(wrap => {
        wrap.classList.toggle('hide-zero-rows', hideZeroRows);
    });
}
