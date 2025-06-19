// This file would contain your API service functions
// For now, we'll just return mock data

import axios from 'axios'

// Create an axios instance with default config
export const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: true, // This is important for handling cookies
})

// Add a request interceptor to include auth token
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token && config.headers) {
    config.headers.Authorization = `Bearer ${token}`
  }
  
  // Add CSRF token from cookies
  const getCookie = (name: string) => {
    if (typeof document === 'undefined') return null; // Server-side check
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop()?.split(';').shift();
    return null;
  };
  
  const csrfToken = getCookie('csrf_token');
  if (csrfToken && config.headers) {
    config.headers['X-CSRF-Token'] = csrfToken;
  }
  
  return config
})

// Add a response interceptor to handle errors
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Handle unauthorized access
      localStorage.removeItem('token')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

// Helper function to get auth headers
const getAuthHeaders = () => {
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
    'Content-Type': 'application/json',
    'X-API-KEY': apiKey || '',
    'Authorization': `Bearer ${token || ''}`,
    ...(csrfToken && { 'X-CSRF-Token': csrfToken }),
  };
};

// Helper function to handle API responses
const handleResponse = async (response: Response) => {
  if (!response.ok) {
    throw new Error(`API request failed: ${response.statusText}`);
  }
  return response.json();
};

// API client
const apiClient = {
  async get(endpoint: string) {
    const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}${endpoint}`, {
      headers: getAuthHeaders(),
    });
    return handleResponse(response);
  },

  async post(endpoint: string, data: any) {
    const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}${endpoint}`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify(data),
    });
    return handleResponse(response);
  },

  async put(endpoint: string, data: any) {
    const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}${endpoint}`, {
      method: 'PUT',
      headers: getAuthHeaders(),
      body: JSON.stringify(data),
    });
    return handleResponse(response);
  },

  async delete(endpoint: string) {
    const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}${endpoint}`, {
      method: 'DELETE',
      headers: getAuthHeaders(),
    });
    return handleResponse(response);
  },
};

export default apiClient;

export async function fetchOverviewMetrics() {
  // In a real app, this would be:
  // const response = await fetch('/analytics/overview-metrics', {
  //   headers: {
  //     'Authorization': `Bearer ${token}`,
  //     'X-API-KEY': apiKey
  //   }
  // });
  // return response.json();

  // For now, return mock data
  return {
    total_requests: 15782,
    failed_requests: 423,
    total_4xx: 387,
    total_5xx: 36,
    avg_response_time: 142.5,
  }
}

export async function fetchEndpoints() {
  // In a real app, this would fetch from your API
  // For now, return mock data
  return [
    {
      endpoint_id: 1,
      name: "User Authentication",
      url: "/auth/token",
      method: "POST",
      status: true,
      description: "User login endpoint",
    },
    {
      endpoint_id: 2,
      name: "Endpoint List",
      url: "/api-management/endpoints",
      method: "GET",
      status: true,
      description: "List all API endpoints",
    },
    {
      endpoint_id: 3,
      name: "Traffic Analysis",
      url: "/security/traffic-analysis",
      method: "GET",
      status: true,
      description: "Get traffic analysis data",
    },
    {
      endpoint_id: 4,
      name: "Vulnerability Scan",
      url: "/security/vulnerability-scan/comprehensive",
      method: "GET",
      status: false,
      description: "Run comprehensive vulnerability scan",
    },
    {
      endpoint_id: 5,
      name: "Analytics Overview",
      url: "/analytics/overview-metrics",
      method: "GET",
      status: true,
      description: "Get overview metrics",
    },
  ]
}

export async function fetchThreatIndicators() {
  // In a real app, this would fetch from your API
  // For now, return mock data
  return {
    sql_injection: 12,
    xss_attempts: 8,
    path_traversal: 5,
    unauthorized_access: 15,
    rate_limit_violations: 23,
    suspicious_ips: 7,
  }
}

// Security API client
export const security = {
  async getTrafficAnalysis() {
    const response = await apiClient.get('/security/traffic-analysis');
    return response;
  },

  async getThreatScores() {
    const response = await apiClient.get('/security/threat-score');
    return response;
  },

  async getVulnerabilityScan() {
    const response = await apiClient.get('/security/vulnerability-scan/comprehensive');
    return response;
  },

  async getThreatIndicators() {
    const response = await apiClient.get('/security/threat-indicators');
    return response;
  },

  async getOpenEndpoints() {
    const response = await apiClient.get('/security/vulnerability-scan/open-endpoints');
    return response;
  },

  async exportLogs() {
    const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/security/export-logs`, {
      headers: getAuthHeaders(),
    });
    if (!response.ok) {
      throw new Error('Failed to export logs');
    }
    return response.blob();
  }
};
