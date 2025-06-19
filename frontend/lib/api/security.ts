const API_URL = 'http://localhost:8000';

// Helper function to get auth headers with CSRF token
const getAuthHeaders = async () => {
  const token = localStorage.getItem('token');
  const apiKey = localStorage.getItem('apiKey');
  
  // Get CSRF token from cookies
  const getCookie = (name: string) => {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop()?.split(';').shift();
    return null;
  };
  
  const csrfToken = getCookie('csrf_token');
  
  return {
    'Authorization': `Bearer ${token || ''}`,
    'X-API-KEY': apiKey || '',
    'Content-Type': 'application/json',
    ...(csrfToken && { 'X-CSRF-Token': csrfToken }),
  };
};

interface TrafficAnalysis {
  total_requests: number;
  top_ips: Array<{ ip: string; request_count: number }>;
  suspicious_ips: string[];
  method_distribution: Record<string, number>;
  endpoint_hits: Record<string, number>;
  timestamp: string;
}

interface ThreatScore {
  ip: string;
  score: number;
  threat_type: string;
  details: string;
  timestamp: string;
}

interface VulnerabilityScan {
  total_scanned_endpoints: number;
  total_pages: number;
  current_page: number;
  page_size: number;
  scan_results: Array<{
    url: string;
    high_risk_alerts: Array<{ type: string; description: string }>;
    medium_risk_alerts: Array<{ type: string; description: string }>;
    low_risk_alerts: Array<{ type: string; description: string }>;
  }>;
  timestamp: string;
}

interface ThreatIndicators {
  sql_injection: number;
  xss_attempts: number;
  path_traversal: number;
  unauthorized_access: number;
  rate_limit_violations: number;
  suspicious_ips: number;
}

interface OpenEndpoint {
  endpoint: string;
  issue: string;
}

interface ThreatTrendData {
  timestamp: string;
  total_threats: number;
  sql_injection: number;
  xss_attempts: number;
  path_traversal: number;
  unauthorized_access: number;
  rate_limit_violations: number;
  other_threats: number;
}

interface ThreatTrends {
  timeframe: string;
  timeInterval: string;
  trend_data: ThreatTrendData[];
  total_threats: number;
  timestamp: string;
}

interface AttackedEndpoint {
  attack_id: number;
  endpoint: string;
  method: string;
  attack_type: string;
  client_ip: string;
  attack_count: number;
  first_seen: string;
  last_seen: string;
  recommended_fix: string;
  severity: string;
  is_resolved: boolean;
  resolution_notes: string | null;
  created_at: string;
  updated_at: string;
}

interface AttackedEndpointsResponse {
  total_attacks: number;
  total_pages: number;
  current_page: number;
  page_size: number;
  attacked_endpoints: AttackedEndpoint[];
  severity_distribution: Record<string, number>;
  attack_type_distribution: Record<string, number>;
  timestamp: string;
}

export const security = {
  getTrafficAnalysis: async (): Promise<TrafficAnalysis> => {
    const response = await fetch(`${API_URL}/security/traffic-analysis`, {
      headers: await getAuthHeaders(),
    });
    if (!response.ok) {
      throw new Error('Failed to fetch traffic analysis');
    }
    return response.json();
  },

  getThreatScores: async (): Promise<{ threat_scores: ThreatScore[] }> => {
    const response = await fetch(`${API_URL}/security/threat-score`, {
      headers: await getAuthHeaders(),
    });
    if (!response.ok) {
      throw new Error('Failed to fetch threat scores');
    }
    return response.json();
  },

  getVulnerabilityScan: async (page: number = 1, pageSize: number = 10): Promise<VulnerabilityScan> => {
    const response = await fetch(`${API_URL}/security/vulnerability-scan/comprehensive?page=${page}&page_size=${pageSize}`, {
      headers: await getAuthHeaders(),
    });
    if (!response.ok) {
      throw new Error('Failed to fetch vulnerability scan');
    }
    return response.json();
  },

  getThreatIndicators: async (): Promise<ThreatIndicators> => {
    const response = await fetch(`${API_URL}/security/threat-indicators`, {
      headers: await getAuthHeaders(),
    });
    if (!response.ok) {
      throw new Error('Failed to fetch threat indicators');
    }
    return response.json();
  },

  getThreatTrends: async (timeframe: string = "24h", interval: string = "1h"): Promise<ThreatTrends> => {
    const response = await fetch(`${API_URL}/security/threat-trends?timeframe=${timeframe}&interval=${interval}`, {
      headers: await getAuthHeaders(),
    });
    if (!response.ok) {
      throw new Error('Failed to fetch threat trends');
    }
    return response.json();
  },

  getOpenEndpoints: async (): Promise<{ open_endpoints: OpenEndpoint[] }> => {
    const response = await fetch(`${API_URL}/security/vulnerability-scan/open-endpoints`, {
      headers: await getAuthHeaders(),
    });
    if (!response.ok) {
      throw new Error('Failed to fetch open endpoints');
    }
    return response.json();
  },

  exportLogs: async (): Promise<Blob> => {
    const response = await fetch(`${API_URL}/security/export-logs`, {
      headers: await getAuthHeaders(),
    });
    if (!response.ok) {
      throw new Error('Failed to export logs');
    }
    return response.blob();
  },

  exportThreatLogs: async (): Promise<Blob> => {
    const response = await fetch(`${API_URL}/security/export-threat-logs`, {
      headers: await getAuthHeaders(),
    });
    if (!response.ok) {
      throw new Error('Failed to export threat logs');
    }
    return response.blob();
  },

  exportTrafficLogs: async (): Promise<Blob> => {
    const response = await fetch(`${API_URL}/security/export-traffic-logs`, {
      headers: await getAuthHeaders(),
    });
    if (!response.ok) {
      throw new Error('Failed to export traffic logs');
    }
    return response.blob();
  },

  getAttackedEndpoints: async (
    page: number = 1,
    pageSize: number = 10,
    severity?: string,
    attackType?: string,
    isResolved?: boolean,
    sortBy: string = "last_seen",
    sortOrder: string = "desc"
  ): Promise<AttackedEndpointsResponse> => {
    const params = new URLSearchParams({
      page: page.toString(),
      page_size: pageSize.toString(),
      sort_by: sortBy,
      sort_order: sortOrder,
    });
    
    if (severity) params.append('severity', severity);
    if (attackType) params.append('attack_type', attackType);
    if (isResolved !== undefined) params.append('is_resolved', isResolved.toString());

    const response = await fetch(`${API_URL}/security/attacked-endpoints?${params}`, {
      headers: await getAuthHeaders(),
    });
    if (!response.ok) {
      throw new Error('Failed to fetch attacked endpoints');
    }
    return response.json();
  },

  resolveAttackedEndpoint: async (attackId: number, resolutionNotes?: string): Promise<{ message: string; attack_id: number; timestamp: string }> => {
    const response = await fetch(`${API_URL}/security/attacked-endpoints/${attackId}/resolve`, {
      method: 'PUT',
      headers: await getAuthHeaders(),
      body: JSON.stringify({ resolution_notes: resolutionNotes }),
    });
    if (!response.ok) {
      throw new Error('Failed to resolve attacked endpoint');
    }
    return response.json();
  },

  getLogsByIp: async (ip: string) => {
    const response = await fetch(`${API_URL}/security/logs/by-ip?ip=${encodeURIComponent(ip)}`, {
      headers: await getAuthHeaders(),
    });
    if (!response.ok) {
      throw new Error('Failed to fetch logs for IP');
    }
    return response.json();
  },
} as const

export type SecurityAPI = typeof security 