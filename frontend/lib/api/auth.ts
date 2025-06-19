const API_URL = 'http://localhost:8000';

interface LoginResponse {
  access_token: string;
  token_type: string;
  csrf_token: string;
  api_key?: string;
}

interface User {
  user_id: number;
  user_name: string;
  user_email: string;
  user_role: string;
}

export const login = async (username: string, password: string): Promise<LoginResponse> => {
  const response = await fetch(`${API_URL}/auth/token`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded',
    },
    body: new URLSearchParams({
      username,
      password,
    }).toString(),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Login failed');
  }

  return response.json();
};

export const logout = async (): Promise<void> => {
  // Clear local storage
  localStorage.removeItem('token');
  localStorage.removeItem('apiKey');
  
  // Clear CSRF token cookie
  document.cookie = 'csrf_token=; Max-Age=0';
};

export const getCurrentUser = async (): Promise<User> => {
  const token = localStorage.getItem('token');
  const apiKey = localStorage.getItem('apiKey');

  if (!token) {
    throw new Error('No authentication token found');
  }

  const response = await fetch(`${API_URL}/auth/current-user`, {
    headers: {
      'Authorization': `Bearer ${token}`,
      'X-API-KEY': apiKey || '',
    },
  });

  if (!response.ok) {
    if (response.status === 401) {
      // Token is invalid or expired
      await logout();
    }
    throw new Error('Failed to fetch user data');
  }

  return response.json();
};

export const checkAuth = async (): Promise<boolean> => {
  try {
    const token = localStorage.getItem('token');
    if (!token) return false;

    const response = await fetch(`${API_URL}/auth/current-user`, {
      headers: {
        'Authorization': `Bearer ${token}`,
        'X-API-KEY': localStorage.getItem('apiKey') || '',
      },
    });

    return response.ok;
  } catch (error) {
    return false;
  }
};

export const refreshToken = async (): Promise<string> => {
  const token = localStorage.getItem('token');
  if (!token) {
    throw new Error('No refresh token available');
  }

  const response = await fetch(`${API_URL}/auth/refresh`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
    },
  });

  if (!response.ok) {
    throw new Error('Failed to refresh token');
  }

  const data = await response.json();
  localStorage.setItem('token', data.access_token);
  return data.access_token;
}; 