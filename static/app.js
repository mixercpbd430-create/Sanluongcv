/* ============================================
   SẢN LƯỢNG HÀNG NGÀY - App Logic
   Chart.js + Dynamic Table + Line Selection
   + Month Filtering
   ============================================ */

// ---- Color palette for production lines ----
const LINE_COLORS = {
    PL1: { bg: 'rgba(99, 102, 241, 0.7)',  border: '#6366f1', rgb: '99, 102, 241' },
    PL2: { bg: 'rgba(6, 182, 212, 0.7)',   border: '#06b6d4',  rgb: '6, 182, 212' },
    PL3: { bg: 'rgba(16, 185, 129, 0.7)',  border: '#10b981', rgb: '16, 185, 129' },
    PL4: { bg: 'rgba(245, 158, 11, 0.7)',  border: '#f59e0b', rgb: '245, 158, 11' },
    PL5: { bg: 'rgba(244, 63, 94, 0.7)',   border: '#f43f5e',  rgb: '244, 63, 94' },
    PL6: { bg: 'rgba(14, 165, 233, 0.7)',  border: '#0ea5e9', rgb: '14, 165, 233' },
    PL7: { bg: 'rgba(236, 72, 153, 0.7)',  border: '#ec4899', rgb: '236, 72, 153' },
    MIXER: { bg: 'rgba(251, 146, 60, 0.7)', border: '#fb923c', rgb: '251, 146, 60' },
};

const SHIFT_COLORS = {
    ca1: { bg: 'rgba(99, 102, 241, 0.6)',  border: '#6366f1' },
    ca2: { bg: 'rgba(6, 182, 212, 0.6)',   border: '#06b6d4' },
    ca3: { bg: 'rgba(16, 185, 129, 0.6)',  border: '#10b981' },
};

let currentLine = 'ALL';
let chart = null;
let hideZeroDays = false;

// ---- Initialize ----
document.addEventListener('DOMContentLoaded', () => {
    updateLastUpdated();
    updateSubtitle();
    renderSummaryCards();
    renderTabs();
    renderChart();
    renderTable();
});

// ---- Utility ----
function formatNumber(num) {
    if (num === 0 || num === null || num === undefined) return '-';
    return num.toLocaleString('vi-VN', { minimumFractionDigits: 1, maximumFractionDigits: 1 });
}

function updateLastUpdated() {
    const now = new Date();
    const formatted = now.toLocaleString('vi-VN', {
        day: '2-digit', month: '2-digit', year: 'numeric',
        hour: '2-digit', minute: '2-digit'
    });
    document.getElementById('last-updated').textContent = formatted;
}

function updateSubtitle() {
    const sel = AVAILABLE_MONTHS.find(m => m.key === SELECTED_MONTH);
    const label = sel ? sel.label : '';
    document.getElementById('report-subtitle').textContent = label;
}

function getMonthLabel(monthKey) {
    const parts = monthKey.split('-');
    return `Tháng ${parseInt(parts[1])}/${parts[0]}`;
}

// ---- Month Switching ----
function changeMonth(monthKey) {
    // Navigate to the new month via query param - Flask will re-render
    window.location.href = `/?month=${monthKey}`;
}

// ---- Tabs ----
function renderTabs() {
    const tabsContainer = document.getElementById('line-tabs');
    tabsContainer.innerHTML = '';

    // "Tổng quan" tab
    const allTab = document.createElement('button');
    allTab.className = 'tab active';
    allTab.dataset.line = 'ALL';
    allTab.id = 'tab-all';
    allTab.textContent = 'Tổng quan';
    allTab.onclick = () => selectLine('ALL');
    tabsContainer.appendChild(allTab);

    // Individual line tabs
    Object.keys(RAW_DATA).forEach(ln => {
        const tab = document.createElement('button');
        tab.className = 'tab';
        tab.dataset.line = ln;
        tab.id = `tab-${ln}`;
        tab.textContent = ln;
        tab.onclick = () => selectLine(ln);
        tabsContainer.appendChild(tab);
    });
}

// ---- Summary Cards ----
function renderSummaryCards() {
    const grid = document.getElementById('summary-grid');
    grid.innerHTML = '';

    const lineNames = Object.keys(RAW_DATA);

    if (lineNames.length === 0) {
        grid.innerHTML = '<div class="empty-state">Không có dữ liệu cho tháng này</div>';
        return;
    }

    // Separate MIXER and Pellet lines
    const hasMixer = lineNames.includes('MIXER');
    const pelletLines = lineNames.filter(ln => ln !== 'MIXER').sort();

    // 0. SALE card first — cumulative monthly total from manual inputs
    const saleTotal = (typeof MONTHLY_SALE_TOTAL !== 'undefined') ? MONTHLY_SALE_TOTAL : 0;
    const saleCard = createSummaryCard(
        'SALE',
        saleTotal,
        'Tổng xuất tháng',
        'linear-gradient(135deg, #10b981, #059669)',
        null  // not clickable for chart filter
    );
    grid.appendChild(saleCard);

    // 1. MIXER card (if available)
    if (hasMixer) {
        const mixerInfo = RAW_DATA['MIXER'];
        const mixerColor = LINE_COLORS['MIXER'] || { border: '#fb923c' };
        const mixerDays = mixerInfo.days.filter(d => d.total > 0).length;
        const mixerCard = createSummaryCard(
            'MIXER',
            mixerInfo.summary.total,
            `${mixerDays} ngày sản xuất`,
            mixerColor.border,
            'MIXER'
        );
        grid.appendChild(mixerCard);
    }

    // 2. TỔNG CỘNG card = sum of PL1-PL7 only (not MIXER)
    const pelletTotal = pelletLines.reduce((sum, ln) => sum + RAW_DATA[ln].summary.total, 0);
    const totalCard = createSummaryCard(
        'Tổng cộng',
        pelletTotal,
        `${pelletLines.length} dây chuyền`,
        'linear-gradient(135deg, #6366f1, #8b5cf6)',
        'ALL'
    );
    grid.appendChild(totalCard);

    // 3. Individual Pellet line cards (PL1, PL2, ..., PL7)
    pelletLines.forEach((ln) => {
        const info = RAW_DATA[ln];
        const color = LINE_COLORS[ln] || { border: '#94a3b8' };
        const workDays = info.days.filter(d => d.total > 0).length;
        const card = createSummaryCard(
            ln,
            info.summary.total,
            `${workDays} ngày sản xuất`,
            color.border,
            ln
        );
        grid.appendChild(card);
    });

    updateActiveCard();
}

function createSummaryCard(label, value, detail, accentColor, lineName) {
    const card = document.createElement('div');
    card.className = 'summary-card animate-in';
    card.style.setProperty('--card-accent', accentColor);
    if (lineName) {
        card.dataset.line = lineName;
        card.onclick = () => selectLine(lineName);
    }

    let detailHTML = '';
    if (detail) {
        detailHTML = `<div class="card-detail">${detail}</div>`;
    }

    card.innerHTML = `
        <div class="card-label">${label}</div>
        <div class="card-value">${formatNumber(value)}<span class="card-unit">tấn</span></div>
        ${detailHTML}
    `;
    return card;
}

function updateActiveCard() {
    document.querySelectorAll('.summary-card').forEach(card => {
        card.classList.toggle('active', card.dataset.line === currentLine);
    });
}

// ---- Line Selection ----
function selectLine(line) {
    currentLine = line;

    // Update tabs
    document.querySelectorAll('.tab').forEach(tab => {
        tab.classList.toggle('active', tab.dataset.line === line);
    });

    updateActiveCard();
    renderChart();
    renderTable();
}

// ---- Chart ----
function renderChart() {
    const ctx = document.getElementById('productionChart').getContext('2d');

    if (chart) {
        chart.destroy();
    }

    const lineNames = Object.keys(RAW_DATA);
    if (lineNames.length === 0) return;

    const titleEl = document.getElementById('chart-title');

    if (currentLine === 'ALL') {
        titleEl.textContent = 'Biểu Đồ Sản Lượng Hàng Ngày - Tổng Quan';
        renderOverviewChart(ctx);
    } else {
        titleEl.textContent = `Biểu Đồ Sản Lượng Hàng Ngày - ${currentLine}`;
        renderLineChart(ctx);
    }
}

function renderOverviewChart(ctx) {
    const lineNames = Object.keys(RAW_DATA);
    const maxDays = Math.max(...lineNames.map(ln => RAW_DATA[ln].days.length));
    const labels = Array.from({ length: maxDays }, (_, i) => `Ngày ${i + 1}`);

    const datasets = lineNames.map((ln) => {
        const colors = LINE_COLORS[ln] || LINE_COLORS.PL1;
        const data = RAW_DATA[ln].days.map(d => d.total || 0);
        return {
            label: ln,
            data: data,
            backgroundColor: colors.bg,
            borderColor: colors.border,
            borderWidth: 2,
            borderRadius: 4,
            borderSkipped: false,
        };
    });

    chart = new Chart(ctx, {
        type: 'bar',
        data: { labels, datasets },
        options: getChartOptions(true),
    });
}

function renderLineChart(ctx) {
    const info = RAW_DATA[currentLine];
    if (!info) return;

    const labels = info.days.map(d => `Ngày ${d.day}`);

    const datasets = [
        {
            label: 'Ca 1',
            data: info.days.map(d => d.ca1),
            backgroundColor: SHIFT_COLORS.ca1.bg,
            borderColor: SHIFT_COLORS.ca1.border,
            borderWidth: 2,
            borderRadius: 4,
            borderSkipped: false,
        },
        {
            label: 'Ca 2',
            data: info.days.map(d => d.ca2),
            backgroundColor: SHIFT_COLORS.ca2.bg,
            borderColor: SHIFT_COLORS.ca2.border,
            borderWidth: 2,
            borderRadius: 4,
            borderSkipped: false,
        },
        {
            label: 'Ca 3',
            data: info.days.map(d => d.ca3),
            backgroundColor: SHIFT_COLORS.ca3.bg,
            borderColor: SHIFT_COLORS.ca3.border,
            borderWidth: 2,
            borderRadius: 4,
            borderSkipped: false,
        },
    ];

    chart = new Chart(ctx, {
        type: 'bar',
        data: { labels, datasets },
        options: getChartOptions(false),
    });
}

function getChartOptions(stacked) {
    return {
        responsive: true,
        maintainAspectRatio: false,
        interaction: {
            mode: 'index',
            intersect: false,
        },
        plugins: {
            legend: {
                position: 'top',
                align: 'end',
                labels: {
                    color: '#94a3b8',
                    font: { family: 'Inter', size: 12, weight: '500' },
                    padding: 16,
                    usePointStyle: true,
                    pointStyle: 'rectRounded',
                },
                onClick: (e, legendItem, legend) => {
                    const lineName = legendItem.text;
                    if (lineName && RAW_DATA[lineName]) {
                        selectLine(lineName);
                    }
                },
            },
            tooltip: {
                backgroundColor: 'rgba(17, 24, 39, 0.95)',
                titleColor: '#f1f5f9',
                bodyColor: '#94a3b8',
                borderColor: 'rgba(255, 255, 255, 0.1)',
                borderWidth: 1,
                padding: 12,
                cornerRadius: 8,
                titleFont: { family: 'Inter', size: 13, weight: '600' },
                bodyFont: { family: 'Inter', size: 12 },
                callbacks: {
                    label: (context) => {
                        const val = context.parsed.y;
                        return ` ${context.dataset.label}: ${val.toLocaleString('vi-VN', { minimumFractionDigits: 1 })} tấn`;
                    },
                },
            },
        },
        scales: {
            x: {
                stacked: stacked,
                grid: {
                    color: 'rgba(255, 255, 255, 0.03)',
                    drawBorder: false,
                },
                ticks: {
                    color: '#64748b',
                    font: { family: 'Inter', size: 11 },
                    maxRotation: 45,
                },
            },
            y: {
                stacked: stacked,
                grid: {
                    color: 'rgba(255, 255, 255, 0.05)',
                    drawBorder: false,
                },
                ticks: {
                    color: '#64748b',
                    font: { family: 'Inter', size: 11 },
                    callback: (val) => val + ' T',
                },
                title: {
                    display: true,
                    text: 'Sản lượng (Tấn)',
                    color: '#64748b',
                    font: { family: 'Inter', size: 12 },
                },
            },
        },
        animation: {
            duration: 800,
            easing: 'easeOutQuart',
        },
    };
}

// ---- Table ----
function renderTable() {
    const tbody = document.getElementById('table-body');
    const tfoot = document.getElementById('table-foot');
    const titleEl = document.getElementById('table-title');
    tbody.innerHTML = '';
    tfoot.innerHTML = '';

    const lineNames = Object.keys(RAW_DATA);
    if (lineNames.length === 0) return;

    if (currentLine === 'ALL') {
        titleEl.textContent = 'Chi Tiết Sản Lượng - Tổng Quan Các Dây Chuyền';
        renderOverviewTable(tbody, tfoot);
    } else {
        titleEl.textContent = `Chi Tiết Sản Lượng - ${currentLine}`;
        renderLineTable(tbody, tfoot);
    }
}

function renderLineTable(tbody, tfoot) {
    const info = RAW_DATA[currentLine];
    if (!info) return;

    const thead = document.querySelector('#data-table thead tr');
    thead.innerHTML = `
        <th>Ngày</th>
        <th>Ca 1 (Tấn)</th>
        <th>Ca 2 (Tấn)</th>
        <th>Ca 3 (Tấn)</th>
        <th>Tổng (Tấn)</th>
    `;

    info.days.forEach(d => {
        const isZero = d.total === 0;
        const tr = document.createElement('tr');
        if (isZero) {
            tr.classList.add('zero-day');
            if (hideZeroDays) tr.classList.add('hidden-zero');
        }
        tr.innerHTML = `
            <td class="day-cell">${d.day}</td>
            <td class="value-cell">${formatNumber(d.ca1)}</td>
            <td class="value-cell">${formatNumber(d.ca2)}</td>
            <td class="value-cell">${formatNumber(d.ca3)}</td>
            <td class="value-cell total-cell">${formatNumber(d.total)}</td>
        `;
        tbody.appendChild(tr);
    });

    const s = info.summary;
    const footRow = document.createElement('tr');
    footRow.innerHTML = `
        <td><strong>Tổng cộng</strong></td>
        <td class="value-cell">${formatNumber(s.ca1)}</td>
        <td class="value-cell">${formatNumber(s.ca2)}</td>
        <td class="value-cell">${formatNumber(s.ca3)}</td>
        <td class="value-cell summary-total">${formatNumber(s.total)}</td>
    `;
    tfoot.appendChild(footRow);
}

function renderOverviewTable(tbody, tfoot) {
    const lineNames = Object.keys(RAW_DATA);

    const thead = document.querySelector('#data-table thead tr');
    thead.innerHTML = `
        <th>Ngày</th>
        ${lineNames.map(ln => `<th>${ln} (Tấn)</th>`).join('')}
        <th>Tổng (Tấn)</th>
    `;

    const maxDays = Math.max(...lineNames.map(ln => RAW_DATA[ln].days.length));

    // Pellet lines only (exclude MIXER) for TỔNG column
    const pelletLinesForTotal = lineNames.filter(ln => ln !== 'MIXER');

    for (let dayIdx = 0; dayIdx < maxDays; dayIdx++) {
        const dayNum = dayIdx + 1;
        let rowTotal = 0;
        let cells = '';

        lineNames.forEach(ln => {
            const dayData = RAW_DATA[ln].days.find(d => d.day === dayNum);
            const val = dayData ? dayData.total : 0;
            // Only add to total if it's a pellet line (not MIXER)
            if (ln !== 'MIXER') {
                rowTotal += val;
            }
            cells += `<td class="value-cell">${formatNumber(val)}</td>`;
        });

        const isZero = rowTotal === 0;
        const tr = document.createElement('tr');
        if (isZero) {
            tr.classList.add('zero-day');
            if (hideZeroDays) tr.classList.add('hidden-zero');
        }
        tr.innerHTML = `
            <td class="day-cell">${dayNum}</td>
            ${cells}
            <td class="value-cell total-cell">${formatNumber(rowTotal)}</td>
        `;
        tbody.appendChild(tr);
    }

    let grandTotal = 0;
    let footCells = '';
    lineNames.forEach(ln => {
        const total = RAW_DATA[ln].summary.total;
        // Only add to grand total if it's a pellet line (not MIXER)
        if (ln !== 'MIXER') {
            grandTotal += total;
        }
        footCells += `<td class="value-cell">${formatNumber(total)}</td>`;
    });

    const footRow = document.createElement('tr');
    footRow.innerHTML = `
        <td><strong>Tổng cộng</strong></td>
        ${footCells}
        <td class="value-cell summary-total">${formatNumber(grandTotal)}</td>
    `;
    tfoot.appendChild(footRow);
}

// ---- Toggle zero days ----
function toggleZeroDays() {
    hideZeroDays = document.getElementById('toggle-zero').checked;
    document.querySelectorAll('.zero-day').forEach(row => {
        row.classList.toggle('hidden-zero', hideZeroDays);
    });
}

// ---- Refresh ----
function refreshData() {
    const btn = document.getElementById('btn-refresh');
    btn.classList.add('spinning');

    // Re-import only the selected month from Excel, then fetch fresh data
    fetch(`/api/refresh?month=${SELECTED_MONTH}`, { method: 'POST' })
        .then(() => fetch(`/api/data?month=${SELECTED_MONTH}`))
        .then(res => res.json())
        .then(data => {
            // Update global data
            Object.keys(RAW_DATA).forEach(key => delete RAW_DATA[key]);
            Object.keys(data.lines).forEach(key => {
                RAW_DATA[key] = data.lines[key];
            });

            // Update monthly sale total
            MONTHLY_SALE_TOTAL = data.monthly_sale_total || 0;

            // Update months dropdown
            const dropdown = document.getElementById('month-dropdown');
            dropdown.innerHTML = '';
            data.months.forEach(m => {
                const opt = document.createElement('option');
                opt.value = m.key;
                opt.textContent = m.label;
                if (m.key === data.selected_month) opt.selected = true;
                dropdown.appendChild(opt);
            });

            // Re-render
            currentLine = 'ALL';
            renderSummaryCards();
            renderTabs();
            renderChart();
            renderTable();
            updateLastUpdated();

            btn.classList.remove('spinning');
        })
        .catch(err => {
            console.error('Refresh failed:', err);
            btn.classList.remove('spinning');
        });
}
