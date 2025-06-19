'use client';

import { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';

interface User {
  username: string;
  id: number;
  role: string;
  user_name?: string;
  user_id?: number;
  user_role?: string;
  user_email?: string;
}

interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
}

export const useAuth = () => {
  const router = useRouter();
  const [authState, setAuthState] = useState<AuthState>({
    user: null,
    isAuthenticated: false,
    isLoading: true,
    error: null,
  });

  const checkAuth = useCallback(async () => {
    try {
      const token = localStorage.getItem('token');
      if (!token) {
        console.log('No token found');
        setAuthState({
          user: null,
          isAuthenticated: false,
          isLoading: false,
          error: null,
        });
        return;
      }

      console.log('Checking auth with token:', token);
      const response = await fetch('http://localhost:8000/auth/current-user', {
        headers: {
          'Authorization': `Bearer ${token}`,
          'X-API-KEY': localStorage.getItem('apiKey') || '',
        },
      });

      if (response.ok) {
        const userData = await response.json();
        console.log('Auth response:', userData);
        
        // Map backend user data to our frontend user model
        const userWithRole = {
          username: userData.user_name || userData.username,
          id: userData.user_id || userData.id,
          role: userData.user_role || userData.role || 'user',
          user_name: userData.user_name,
          user_id: userData.user_id,
          user_role: userData.user_role,
          user_email: userData.user_email
        };
        
        console.log('Processed user data:', userWithRole);
        
        setAuthState({
          user: userWithRole,
          isAuthenticated: true,
          isLoading: false,
          error: null,
        });
      } else {
        console.log('Auth check failed:', response.status);
        // Token is invalid or expired
        localStorage.removeItem('token');
        localStorage.removeItem('apiKey');
        document.cookie = 'csrf_token=; Max-Age=0';
        setAuthState({
          user: null,
          isAuthenticated: false,
          isLoading: false,
          error: 'Session expired',
        });
        router.push('/login');
      }
    } catch (error) {
      console.error('Auth check error:', error);
      setAuthState({
        user: null,
        isAuthenticated: false,
        isLoading: false,
        error: 'Failed to check authentication status',
      });
    }
  }, [router]);

  const login = async (username: string, password: string) => {
    try {
      setAuthState(prev => ({ ...prev, isLoading: true, error: null }));

      const response = await fetch('http://localhost:8000/auth/token', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: new URLSearchParams({
          username,
          password,
        }).toString(),
      });

      if (response.ok) {
        const data = await response.json();
        console.log('Login response:', data);
        
        localStorage.setItem('token', data.access_token);
        localStorage.setItem('apiKey', data.api_key || '');
        
        // Set CSRF token cookie with proper security attributes
        if (data.csrf_token) {
          document.cookie = `csrf_token=${data.csrf_token}; path=/; samesite=Strict; secure=${window.location.protocol === 'https:'}`;
        }

        // Fetch user data after successful login
        await checkAuth();
        router.push('/');
      } else {
        const errorData = await response.json();
        console.error('Login failed:', errorData);
        setAuthState(prev => ({
          ...prev,
          isLoading: false,
          error: errorData.detail || 'Login failed',
        }));
      }
    } catch (error) {
      console.error('Login error:', error);
      setAuthState(prev => ({
        ...prev,
        isLoading: false,
        error: 'An error occurred during login',
      }));
    }
  };

  const logout = useCallback(() => {
    localStorage.removeItem('token');
    localStorage.removeItem('apiKey');
    document.cookie = 'csrf_token=; Max-Age=0';
    setAuthState({
      user: null,
      isAuthenticated: false,
      isLoading: false,
      error: null,
    });
    router.push('/login');
  }, [router]);

  useEffect(() => {
    checkAuth();
  }, [checkAuth]);

  return {
    ...authState,
    login,
    logout,
    checkAuth,
  };
}; 