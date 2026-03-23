import { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { Bar } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  CategoryScale, LinearScale, BarElement,
  Title, Tooltip, Legend,
} from 'chart.js';
import { useAuth } from '../contexts/AuthContext';
import api from '../api/client';
import type { DataResponse, LineInfo, UploadLogsResponse, UploadLogEntry } from '../types';
import './DashboardPage.css';

ChartJS.register(CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend);

const LINE_COLORS: Record<string, { bg: string; border: string }> = {
  PL1: { bg: 'rgba(99, 102, 241, 0.7)', border: '#6366f1' },
  PL2: { bg: 'rgba(6, 182, 212, 0.7)', border: '#06b6d4' },
  PL3: { bg: 'rgba(16, 185, 129, 0.7)', border: '#10b981' },
  PL4: { bg: 'rgba(245, 158, 11, 0.7)', border: '#f59e0b' },
  PL5: { bg: 'rgba(244, 63, 94, 0.7)', border: '#f43f5e' },
  PL6: { bg: 'rgba(14, 165, 233, 0.7)', border: '#0ea5e9' },
  PL7: { bg: 'rgba(236, 72, 153, 0.7)', border: '#ec4899' },
  MIXER: { bg: 'rgba(251, 146, 60, 0.7)', border: '#fb923c' },
};

const SHIFT_COLORS = {
  ca1: { bg: 'rgba(99, 102, 241, 0.6)', border: '#6366f1' },
  ca2: { bg: 'rgba(6, 182, 212, 0.6)', border: '#06b6d4' },
  ca3: { bg: 'rgba(16, 185, 129, 0.6)', border: '#10b981' },
};

function fmtNum(n: number): string {
  if (!n || n === 0) return '-';
  return n.toLocaleString('vi-VN', { minimumFractionDigits: 1, maximumFractionDigits: 1 });
}

export default function DashboardPage() {
  const { user, logout } = useAuth();
  const [data, setData] = useState<DataResponse | null>(null);
  const [currentLine, setCurrentLine] = useState('ALL');
  const [hideZero, setHideZero] = useState(false);
  const [loading, setLoading] = useState(true);
  const [showUserMenu, setShowUserMenu] = useState(false);
  const [showModal, setShowModal] = useState<'password' | 'admin' | null>(null);
  const [newPass, setNewPass] = useState('');
  const [confirmPass, setConfirmPass] = useState('');
  const [modalMsg, setModalMsg] = useState<{ type: 'ok' | 'err'; text: string } | null>(null);
  const [adminUsers, setAdminUsers] = useState<any[]>([]);
  const [uploadLogs, setUploadLogs] = useState<UploadLogsResponse | null>(null);

  const selectedMonth = data?.selected_month || '';

  const fetchData = useCallback(async (month?: string) => {
    try {
      const res = await api.get<DataResponse>('/api/data', { params: { month } });
      setData(res.data);
    } catch (err) {
      console.error('Fetch data failed:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchUploadLogs = useCallback(async () => {
    if (user?.role !== 'admin') return;
    try {
      const res = await api.get<UploadLogsResponse>('/api/upload-logs');
      setUploadLogs(res.data);
    } catch (err) {
      console.error('Fetch upload logs failed:', err);
    }
  }, [user?.role]);

  useEffect(() => { fetchData(); }, [fetchData]);
  useEffect(() => { fetchUploadLogs(); }, [fetchUploadLogs]);

  const handleMonthChange = (month: string) => {
    setLoading(true);
    setCurrentLine('ALL');
    fetchData(month);
  };

  const lines = data?.lines || {};
  const lineNames = Object.keys(lines);
  const pelletLines = lineNames.filter((ln) => ln !== 'MIXER').sort();
  const pelletTotal = pelletLines.reduce((s, ln) => s + (lines[ln]?.summary.total || 0), 0);

  // --- Chart Data ---
  const getChartData = () => {
    if (currentLine === 'ALL') {
      const maxDays = Math.max(0, ...lineNames.map((ln) => lines[ln].days.length));
      return {
        labels: Array.from({ length: maxDays }, (_, i) => `Ngày ${i + 1}`),
        datasets: lineNames.map((ln) => {
          const c = LINE_COLORS[ln] || LINE_COLORS.PL1;
          return {
            label: ln, data: lines[ln].days.map((d) => d.total || 0),
            backgroundColor: c.bg, borderColor: c.border,
            borderWidth: 2, borderRadius: 4, borderSkipped: false as const,
          };
        }),
      };
    }
    const info = lines[currentLine];
    if (!info) return { labels: [], datasets: [] };
    return {
      labels: info.days.map((d) => `Ngày ${d.day}`),
      datasets: [
        { label: 'Ca 1', data: info.days.map((d) => d.ca1), backgroundColor: SHIFT_COLORS.ca1.bg, borderColor: SHIFT_COLORS.ca1.border, borderWidth: 2, borderRadius: 4, borderSkipped: false as const },
        { label: 'Ca 2', data: info.days.map((d) => d.ca2), backgroundColor: SHIFT_COLORS.ca2.bg, borderColor: SHIFT_COLORS.ca2.border, borderWidth: 2, borderRadius: 4, borderSkipped: false as const },
        { label: 'Ca 3', data: info.days.map((d) => d.ca3), backgroundColor: SHIFT_COLORS.ca3.bg, borderColor: SHIFT_COLORS.ca3.border, borderWidth: 2, borderRadius: 4, borderSkipped: false as const },
      ],
    };
  };

  const chartOptions: any = {
    responsive: true, maintainAspectRatio: false,
    interaction: { mode: 'index', intersect: false },
    plugins: {
      legend: { position: 'top' as const, labels: { color: '#94a3b8', font: { family: 'Inter', size: 12 }, usePointStyle: true, pointStyle: 'rectRounded' } },
      tooltip: { backgroundColor: 'rgba(17,24,39,0.95)', titleColor: '#f1f5f9', bodyColor: '#94a3b8', borderColor: 'rgba(255,255,255,0.1)', borderWidth: 1, padding: 12, cornerRadius: 8, callbacks: { label: (ctx: any) => ` ${ctx.dataset.label}: ${ctx.parsed.y.toLocaleString('vi-VN', { minimumFractionDigits: 1 })} tấn` } },
    },
    scales: {
      x: { stacked: currentLine === 'ALL', grid: { color: 'rgba(255,255,255,0.03)' }, ticks: { color: '#64748b', font: { size: 11 }, maxRotation: 45 } },
      y: { stacked: currentLine === 'ALL', grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#64748b', callback: (v: any) => v + ' T' }, title: { display: true, text: 'Sản lượng (Tấn)', color: '#64748b' } },
    },
    animation: { duration: 800, easing: 'easeOutQuart' as const },
  };

  // --- Modal actions ---
  const handleChangePassword = async () => {
    if (!newPass) { setModalMsg({ type: 'err', text: 'Mật khẩu không được để trống' }); return; }
    if (newPass !== confirmPass) { setModalMsg({ type: 'err', text: 'Mật khẩu xác nhận không khớp' }); return; }
    try {
      await api.post('/api/auth/change-password', { new_password: newPass });
      setModalMsg({ type: 'ok', text: '✅ Đổi mật khẩu thành công!' });
      setTimeout(() => setShowModal(null), 1500);
    } catch (err: any) {
      setModalMsg({ type: 'err', text: err.response?.data?.error || 'Lỗi' });
    }
  };

  const handleShowAdmin = async () => {
    try {
      const res = await api.get('/api/auth/users');
      setAdminUsers(res.data);
      setShowModal('admin');
    } catch { }
  };

  if (loading) {
    return (
      <div className="loading-container">
        <div className="loading-spinner" />
        <p>Đang tải dữ liệu...</p>
      </div>
    );
  }

  const monthLabel = data?.months.find((m) => m.key === selectedMonth)?.label || '';

  return (
    <div className="dashboard">
      <div className="bg-shapes">
        <div className="shape shape-1" />
        <div className="shape shape-2" />
        <div className="shape shape-3" />
      </div>

      <div className="container">
        {/* Header */}
        <header className="header">
          <div className="header-content">
            <div className="header-left">
              <div className="logo">
                <svg width="40" height="40" viewBox="0 0 40 40" fill="none">
                  <rect width="40" height="40" rx="10" fill="url(#logo-grad)" />
                  <path d="M12 28V16L20 12L28 16V28L20 24L12 28Z" fill="white" fillOpacity="0.9" />
                  <path d="M20 12V24" stroke="white" strokeWidth="1.5" strokeOpacity="0.5" />
                  <defs><linearGradient id="logo-grad" x1="0" y1="0" x2="40" y2="40"><stop stopColor="#6366f1" /><stop offset="1" stopColor="#8b5cf6" /></linearGradient></defs>
                </svg>
              </div>
              <div>
                <h1>Sản Lượng Sản Xuất</h1>
                <p className="subtitle">{monthLabel}</p>
              </div>
            </div>
            <div className="header-right">
              <div className="month-selector">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="3" y="4" width="18" height="18" rx="2" ry="2" /><line x1="16" y1="2" x2="16" y2="6" /><line x1="8" y1="2" x2="8" y2="6" /><line x1="3" y1="10" x2="21" y2="10" /></svg>
                <select value={selectedMonth} onChange={(e) => handleMonthChange(e.target.value)}>
                  {data?.months.map((m) => (
                    <option key={m.key} value={m.key}>{m.label}</option>
                  ))}
                </select>
              </div>
              <Link to={`/report?month=${selectedMonth}`} className="btn-refresh" style={{ textDecoration: 'none' }}>
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" /><polyline points="14 2 14 8 20 8" /><line x1="16" y1="13" x2="8" y2="13" /><line x1="16" y1="17" x2="8" y2="17" /></svg>
                Báo cáo ngày
              </Link>
              <div className="live-indicator"><span className="pulse" /><span>Dữ liệu trực tiếp</span></div>
              {/* User Menu */}
              <div className="user-menu" onClick={(e) => e.stopPropagation()}>
                <button className="user-btn" onClick={() => setShowUserMenu(!showUserMenu)}>
                  <span className="user-avatar">{user?.display_name?.[0] || '?'}</span>
                  <span className="user-name-text">{user?.display_name}</span>
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M6 9l6 6 6-6" /></svg>
                </button>
                {showUserMenu && (
                  <div className="user-dropdown show">
                    <button onClick={() => { setShowUserMenu(false); setModalMsg(null); setNewPass(''); setConfirmPass(''); setShowModal('password'); }}>🔑 Đổi mật khẩu</button>
                    {user?.role === 'admin' && <button onClick={() => { setShowUserMenu(false); handleShowAdmin(); }}>👥 Quản lý user</button>}
                    <hr />
                    <button onClick={logout}>🚪 Đăng xuất</button>
                  </div>
                )}
              </div>
            </div>
          </div>
        </header>

        {/* Admin Upload Status */}
        {user?.role === 'admin' && uploadLogs && (
          <section className="upload-status-section">
            <div className="upload-status-header">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" /><polyline points="17 8 12 3 7 8" /><line x1="12" y1="3" x2="12" y2="15" /></svg>
              <h3>Trạng Thái Upload Dữ Liệu</h3>
            </div>
            <div className="upload-status-grid">
              {['mixer', 'pellet feedmill', 'pellet mini'].map((source) => {
                const log = uploadLogs.latest.find((l) => l.username === source);
                const status = getUploadStatus(log);
                return (
                  <div key={source} className={`upload-status-card ${status.className}`}>
                    <div className="upload-card-top">
                      <span className={`upload-dot ${status.dotClass}`} />
                      <span className="upload-source-name">{log?.display_name || source}</span>
                    </div>
                    <div className="upload-card-time">
                      {log ? formatUploadTime(log.uploaded_at) : 'Chưa upload'}
                    </div>
                    <div className="upload-card-detail">
                      {log ? `${log.records_count} records` : '—'}
                    </div>
                  </div>
                );
              })}
            </div>
          </section>
        )}

        {/* Summary Cards */}
        <section className="summary-section">
          <div className="summary-grid">
            {lineNames.length === 0 ? (
              <div className="empty-state">Không có dữ liệu cho tháng này</div>
            ) : (
              <>
                <div className="summary-card animate-in" style={{ '--card-accent': 'linear-gradient(135deg,#10b981,#059669)' } as any}>
                  <div className="card-label">SALE</div>
                  <div className="card-value">{fmtNum(data?.monthly_sale_total || 0)}<span className="card-unit">tấn</span></div>
                  <div className="card-detail">Tổng xuất tháng</div>
                </div>
                {lines['MIXER'] && (
                  <div className={`summary-card animate-in ${currentLine === 'MIXER' ? 'active' : ''}`} style={{ '--card-accent': '#fb923c' } as any} onClick={() => setCurrentLine('MIXER')}>
                    <div className="card-label">MIXER</div>
                    <div className="card-value">{fmtNum(lines['MIXER'].summary.total)}<span className="card-unit">tấn</span></div>
                    <div className="card-detail">{lines['MIXER'].days.filter((d) => d.total > 0).length} ngày sản xuất</div>
                  </div>
                )}
                <div className={`summary-card animate-in ${currentLine === 'ALL' ? 'active' : ''}`} style={{ '--card-accent': 'linear-gradient(135deg,#6366f1,#8b5cf6)' } as any} onClick={() => setCurrentLine('ALL')}>
                  <div className="card-label">Tổng cộng</div>
                  <div className="card-value">{fmtNum(pelletTotal)}<span className="card-unit">tấn</span></div>
                  <div className="card-detail">{pelletLines.length} dây chuyền</div>
                </div>
                {pelletLines.map((ln) => (
                  <div key={ln} className={`summary-card animate-in ${currentLine === ln ? 'active' : ''}`} style={{ '--card-accent': LINE_COLORS[ln]?.border || '#94a3b8' } as any} onClick={() => setCurrentLine(ln)}>
                    <div className="card-label">{ln}</div>
                    <div className="card-value">{fmtNum(lines[ln].summary.total)}<span className="card-unit">tấn</span></div>
                    <div className="card-detail">{lines[ln].days.filter((d) => d.total > 0).length} ngày sản xuất</div>
                  </div>
                ))}
              </>
            )}
          </div>
        </section>

        {/* Line Tabs */}
        <section className="tabs-section">
          <div className="tabs">
            <button className={`tab ${currentLine === 'ALL' ? 'active' : ''}`} onClick={() => setCurrentLine('ALL')}>Tổng quan</button>
            {lineNames.map((ln) => (
              <button key={ln} className={`tab ${currentLine === ln ? 'active' : ''}`} onClick={() => setCurrentLine(ln)}>{ln}</button>
            ))}
          </div>
        </section>

        {/* Chart */}
        {lineNames.length > 0 && (
          <section className="chart-section">
            <div className="chart-card glass-card">
              <div className="chart-header">
                <h2>{currentLine === 'ALL' ? 'Biểu Đồ Sản Lượng Hàng Ngày - Tổng Quan' : `Biểu Đồ Sản Lượng Hàng Ngày - ${currentLine}`}</h2>
              </div>
              <div className="chart-wrapper">
                <Bar data={getChartData()} options={chartOptions} />
              </div>
            </div>
          </section>
        )}

        {/* Data Table */}
        {lineNames.length > 0 && (
          <section className="table-section">
            <div className="table-card glass-card">
              <div className="table-header">
                <h2>{currentLine === 'ALL' ? 'Chi Tiết Sản Lượng - Tổng Quan Các Dây Chuyền' : `Chi Tiết Sản Lượng - ${currentLine}`}</h2>
                <label className="toggle-label">
                  <input type="checkbox" checked={hideZero} onChange={(e) => setHideZero(e.target.checked)} />
                  <span className="toggle-slider" />
                  Ẩn ngày nghỉ
                </label>
              </div>
              <div className="table-responsive">
                {currentLine === 'ALL' ? (
                  <OverviewTable lines={lines} lineNames={lineNames} hideZero={hideZero} />
                ) : (
                  <LineTable info={lines[currentLine]} hideZero={hideZero} />
                )}
              </div>
            </div>
          </section>
        )}

        <footer className="footer">

          <p className="footer-sub">Cập nhật lần cuối: {new Date().toLocaleString('vi-VN')}</p>
        </footer>
      </div>

      {/* Modals */}
      {showModal === 'password' && (
        <div className="modal-overlay" onClick={() => setShowModal(null)}>
          <div className="modal-card" onClick={(e) => e.stopPropagation()}>
            <h2>🔑 Đổi Mật Khẩu</h2>
            {modalMsg && <div className={modalMsg.type === 'ok' ? 'msg-ok' : 'msg-err'}>{modalMsg.text}</div>}
            <label>Mật khẩu mới</label>
            <input type="password" value={newPass} onChange={(e) => setNewPass(e.target.value)} placeholder="Nhập mật khẩu mới..." autoFocus />
            <label>Xác nhận mật khẩu</label>
            <input type="password" value={confirmPass} onChange={(e) => setConfirmPass(e.target.value)} placeholder="Nhập lại mật khẩu mới..." />
            <div className="modal-actions">
              <button className="btn-modal-save" onClick={handleChangePassword}>Lưu</button>
              <button className="btn-modal-cancel" onClick={() => setShowModal(null)}>Hủy</button>
            </div>
          </div>
        </div>
      )}
      {showModal === 'admin' && (
        <div className="modal-overlay" onClick={() => setShowModal(null)}>
          <div className="modal-card" onClick={(e) => e.stopPropagation()}>
            <h2>👥 Quản Lý User</h2>
            <p style={{ color: '#94a3b8', fontSize: '0.85rem', marginBottom: 16 }}>Danh sách tài khoản và mật khẩu hiện tại:</p>
            {adminUsers.map((u: any, i: number) => (
              <div className="user-item" key={i}>
                <div>
                  <div className="u-name">{u.display_name}</div>
                  <div className="u-role">{u.role === 'admin' ? '👑 Admin' : '👤 User'} — {u.username}</div>
                </div>
                <div className="u-pass">{u.password}</div>
              </div>
            ))}
            <div className="modal-actions" style={{ marginTop: 16 }}>
              <button className="btn-modal-cancel" onClick={() => setShowModal(null)}>Đóng</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// Helpers for upload status
function getUploadStatus(log: UploadLogEntry | undefined) {
  if (!log) return { className: 'status-none', dotClass: 'dot-red' };
  const uploadDate = new Date(log.uploaded_at);
  const now = new Date();
  // Convert to Vietnam timezone for day comparison
  const vnUpload = new Date(uploadDate.getTime() + 7 * 60 * 60 * 1000);
  const vnNow = new Date(now.getTime() + 7 * 60 * 60 * 1000);
  const uploadDay = vnUpload.toISOString().slice(0, 10);
  const today = vnNow.toISOString().slice(0, 10);
  const yesterday = new Date(vnNow.getTime() - 86400000).toISOString().slice(0, 10);

  if (uploadDay === today) return { className: 'status-today', dotClass: 'dot-green' };
  if (uploadDay === yesterday) return { className: 'status-yesterday', dotClass: 'dot-yellow' };
  return { className: 'status-old', dotClass: 'dot-red' };
}

function formatUploadTime(isoStr: string) {
  const d = new Date(isoStr);
  return d.toLocaleString('vi-VN', { timeZone: 'Asia/Ho_Chi_Minh', hour: '2-digit', minute: '2-digit', second: '2-digit', day: '2-digit', month: '2-digit', year: 'numeric' });
}

// Sub-components
function LineTable({ info, hideZero }: { info: LineInfo; hideZero: boolean }) {
  if (!info) return null;
  return (
    <table>
      <thead><tr><th>Ngày</th><th>Ca 1 (Tấn)</th><th>Ca 2 (Tấn)</th><th>Ca 3 (Tấn)</th><th>Tổng (Tấn)</th></tr></thead>
      <tbody>
        {info.days.map((d) => {
          const isZero = d.total === 0;
          if (hideZero && isZero) return null;
          return (
            <tr key={d.day} className={isZero ? 'zero-day' : ''}>
              <td className="day-cell">{d.day}</td>
              <td className="value-cell">{fmtNum(d.ca1)}</td>
              <td className="value-cell">{fmtNum(d.ca2)}</td>
              <td className="value-cell">{fmtNum(d.ca3)}</td>
              <td className="value-cell total-cell">{fmtNum(d.total)}</td>
            </tr>
          );
        })}
      </tbody>
      <tfoot><tr>
        <td><strong>Tổng cộng</strong></td>
        <td className="value-cell">{fmtNum(info.summary.ca1)}</td>
        <td className="value-cell">{fmtNum(info.summary.ca2)}</td>
        <td className="value-cell">{fmtNum(info.summary.ca3)}</td>
        <td className="value-cell summary-total">{fmtNum(info.summary.total)}</td>
      </tr></tfoot>
    </table>
  );
}

function OverviewTable({ lines, lineNames, hideZero }: { lines: Record<string, LineInfo>; lineNames: string[]; hideZero: boolean }) {
  const pelletLinesForTotal = lineNames.filter((ln) => ln !== 'MIXER');
  const maxDays = Math.max(0, ...lineNames.map((ln) => lines[ln].days.length));

  return (
    <table>
      <thead><tr>
        <th>Ngày</th>
        {lineNames.map((ln) => <th key={ln}>{ln} (Tấn)</th>)}
        <th>Tổng (Tấn)</th>
      </tr></thead>
      <tbody>
        {Array.from({ length: maxDays }, (_, i) => {
          const dayNum = i + 1;
          let rowTotal = 0;
          const cells = lineNames.map((ln) => {
            const dayData = lines[ln].days.find((d) => d.day === dayNum);
            const val = dayData?.total || 0;
            if (pelletLinesForTotal.includes(ln)) rowTotal += val;
            return <td key={ln} className="value-cell">{fmtNum(val)}</td>;
          });
          if (hideZero && rowTotal === 0) return null;
          return (
            <tr key={dayNum} className={rowTotal === 0 ? 'zero-day' : ''}>
              <td className="day-cell">{dayNum}</td>
              {cells}
              <td className="value-cell total-cell">{fmtNum(rowTotal)}</td>
            </tr>
          );
        })}
      </tbody>
      <tfoot><tr>
        <td><strong>Tổng cộng</strong></td>
        {lineNames.map((ln) => <td key={ln} className="value-cell">{fmtNum(lines[ln].summary.total)}</td>)}
        <td className="value-cell summary-total">{fmtNum(pelletLinesForTotal.reduce((s, ln) => s + lines[ln].summary.total, 0))}</td>
      </tr></tfoot>
    </table>
  );
}
