export interface UserInfo {
  id: number;
  username: string;
  role: string;
  display_name: string;
}

export interface LoginResponse {
  token: string;
  user: UserInfo;
}

export interface MonthOption {
  key: string;
  label: string;
}

export interface DayData {
  day: number;
  ca1: number;
  ca2: number;
  ca3: number;
  total: number;
  cam_bot?: number;
}

export interface SummaryData {
  ca1: number;
  ca2: number;
  ca3: number;
  total: number;
}

export interface LineInfo {
  name: string;
  month: number;
  year: number;
  month_key: string;
  category: string;
  days: DayData[];
  summary: SummaryData;
}

export interface DataResponse {
  months: MonthOption[];
  selected_month: string;
  lines: Record<string, LineInfo>;
  monthly_sale_total: number;
}

export interface ShiftData {
  ca1: number;
  ca2: number;
  ca3: number;
  total: number;
  cam_bot: number;
}

export interface PelletData {
  name: string;
  ca1: number;
  ca2: number;
  ca3: number;
  total: number;
}

export interface ReportResponse {
  day: number;
  month: string;
  mixer: ShiftData;
  pellets: PelletData[];
  total_pellet: ShiftData;
  sale: number | null;
  stock: number | null;
}

export interface UserListItem {
  username: string;
  password: string;
  role: string;
  display_name: string;
}

export interface UploadLogEntry {
  username: string;
  display_name: string;
  records_count: number;
  uploaded_at: string; // ISO datetime (UTC)
}

export interface UploadLogsResponse {
  latest: UploadLogEntry[];
  recent: UploadLogEntry[];
}

