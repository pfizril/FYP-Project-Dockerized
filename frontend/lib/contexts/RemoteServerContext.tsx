'use client';

import React, { createContext, useContext, useState, useEffect } from 'react';
import { useToast } from '@/components/ui/use-toast';

interface RemoteServer {
  id: number;
  name: string;
  base_url: string;
  status: string;
  description?: string;
  created_at: string;
  last_checked?: string;
  retry_count: number;
  last_error?: string;
  updated_at: string;
  is_active: boolean;
  api_key?: string;
  health_check_url?: string;
  username?: string;
  password?: string;
  auth_type?: 'basic' | 'token';
  token_endpoint?: string;
  access_token?: string;
  token_expires_at?: string;
  created_by?: number;
}

interface RemoteServerContextType {
  servers: RemoteServer[];
  currentServer: RemoteServer | null;
  loading: boolean;
  error: string | null;
  addServer: (server: Omit<RemoteServer, 'id' | 'created_at' | 'updated_at'>) => Promise<void>;
  updateServer: (id: number, server: Partial<RemoteServer>) => Promise<void>;
  deleteServer: (id: number) => Promise<void>;
  switchServer: (id: number) => void;
  checkServerStatus: (id: number) => Promise<void>;
  refreshServers: () => Promise<void>;
}

const RemoteServerContext = createContext<RemoteServerContextType | undefined>(undefined);

export function RemoteServerProvider({ children }: { children: React.ReactNode }) {
  const [servers, setServers] = useState<RemoteServer[]>([]);
  const [currentServer, setCurrentServer] = useState<RemoteServer | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { toast } = useToast();

  const fetchServers = async () => {
    try {
      setLoading(true);
      const token = localStorage.getItem('token');
      const apiKey = localStorage.getItem('apiKey');
      
      if (!token) {
        throw new Error('No authentication token found');
      }

      const backendUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      
      // Get CSRF token first
      const csrfResponse = await fetch(`${backendUrl}/csrf/csrf-token`, {
        credentials: 'include',
      });
      const csrfData = await csrfResponse.json();
      const csrfToken = csrfData.csrf_token;
      
      const response = await fetch(`${backendUrl}/remote-servers`, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'X-API-KEY': apiKey || '',
          'X-CSRF-Token': csrfToken,
        },
        credentials: 'include',
      });
      if (!response.ok) throw new Error('Failed to fetch servers');
      const data = await response.json();
      setServers(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch servers');
      toast({
        title: 'Error',
        description: 'Failed to fetch remote servers',
        variant: 'destructive',
      });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchServers();
  }, []);

  const addServer = async (server: Omit<RemoteServer, 'id' | 'created_at' | 'updated_at'>) => {
    try {
      setLoading(true);
      setError(null);
      const token = localStorage.getItem('token');
      const apiKey = localStorage.getItem('apiKey');
      
      if (!token) {
        throw new Error('No authentication token found');
      }

      console.log('Adding server with data:', server); // Debug log

      const backendUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      
      // Get CSRF token first
      const csrfResponse = await fetch(`${backendUrl}/csrf/csrf-token`, {
        credentials: 'include',
      });
      const csrfData = await csrfResponse.json();
      const csrfToken = csrfData.csrf_token;
      
      const response = await fetch(`${backendUrl}/remote-servers`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
          'X-API-KEY': apiKey || '',
          'X-CSRF-Token': csrfToken,
        },
        credentials: 'include',
        body: JSON.stringify(server),
      });

      console.log('Server response status:', response.status); // Debug log

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Failed to add server');
      }

      const newServer = await response.json();
      console.log('New server data:', newServer); // Debug log

      setServers(prev => [...prev, newServer]);
      toast({
        title: 'Success',
        description: 'Remote server added successfully',
      });
    } catch (err) {
      console.error('Error adding server:', err);
      const errorMessage = err instanceof Error ? err.message : 'Failed to add server';
      setError(errorMessage);
      toast({
        title: 'Error',
        description: errorMessage,
        variant: 'destructive',
      });
      throw err; // Re-throw to be handled by the form
    } finally {
      setLoading(false);
    }
  };

  const updateServer = async (id: number, server: Partial<RemoteServer>) => {
    try {
      setLoading(true);
      const token = localStorage.getItem('token');
      const apiKey = localStorage.getItem('apiKey');
      
      if (!token) {
        throw new Error('No authentication token found');
      }

      const backendUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      
      console.log('=== UPDATE SERVER DEBUG ===');
      console.log('Server ID:', id);
      console.log('Backend URL:', backendUrl);
      console.log('Token:', token ? 'Present' : 'Missing');
      console.log('API Key:', apiKey ? 'Present' : 'Missing');
      console.log('Request Data:', JSON.stringify(server, null, 2));
      
      // Get CSRF token first
      const csrfResponse = await fetch(`${backendUrl}/csrf/csrf-token`, {
        credentials: 'include',
      });
      const csrfData = await csrfResponse.json();
      const csrfToken = csrfData.csrf_token;
      
      console.log('CSRF Token:', csrfToken ? 'Present' : 'Missing');
      
      const response = await fetch(`${backendUrl}/remote-servers/${id}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
          'X-API-KEY': apiKey || '',
          'X-CSRF-Token': csrfToken,
        },
        credentials: 'include',
        body: JSON.stringify(server),
      });
      
      console.log('Response Status:', response.status);
      console.log('Response Headers:', Object.fromEntries(response.headers.entries()));
      
      const responseText = await response.text();
      console.log('Response Body:', responseText);
      
      if (!response.ok) {
        console.error('Update failed with status:', response.status);
        console.error('Response body:', responseText);
        throw new Error(`Failed to update server: ${response.status} - ${responseText}`);
      }
      
      const updatedServer = JSON.parse(responseText);
      console.log('Updated server data:', updatedServer);
      
      setServers(prev => prev.map(s => s.id === id ? updatedServer : s));
      if (currentServer?.id === id) {
        setCurrentServer(updatedServer);
      }
      toast({
        title: 'Success',
        description: 'Remote server updated successfully',
      });
    } catch (err) {
      console.error('Update server error:', err);
      setError(err instanceof Error ? err.message : 'Failed to update server');
      toast({
        title: 'Error',
        description: 'Failed to update remote server',
        variant: 'destructive',
      });
    } finally {
      setLoading(false);
    }
  };

  const deleteServer = async (id: number) => {
    try {
      setLoading(true);
      const token = localStorage.getItem('token');
      const apiKey = localStorage.getItem('apiKey');
      
      if (!token) {
        throw new Error('No authentication token found');
      }

      const backendUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      
      // Get CSRF token first
      const csrfResponse = await fetch(`${backendUrl}/csrf/csrf-token`, {
        credentials: 'include',
      });
      const csrfData = await csrfResponse.json();
      const csrfToken = csrfData.csrf_token;
      
      const response = await fetch(`${backendUrl}/remote-servers/${id}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${token}`,
          'X-API-KEY': apiKey || '',
          'X-CSRF-Token': csrfToken,
        },
        credentials: 'include',
      });
      if (!response.ok) throw new Error('Failed to delete server');
      setServers(prev => prev.filter(s => s.id !== id));
      if (currentServer?.id === id) {
        setCurrentServer(null);
      }
      toast({
        title: 'Success',
        description: 'Remote server deleted successfully',
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete server');
      toast({
        title: 'Error',
        description: 'Failed to delete remote server',
        variant: 'destructive',
      });
    } finally {
      setLoading(false);
    }
  };

  const switchServer = (id: number) => {
    const server = servers.find(s => s.id === id);
    if (server) {
      setCurrentServer(server);
      toast({
        title: 'Success',
        description: `Switched to server: ${server.name}`,
      });
    }
  };

  const checkServerStatus = async (id: number) => {
    try {
      setLoading(true);
      const token = localStorage.getItem('token');
      const apiKey = localStorage.getItem('apiKey');
      
      if (!token) {
        throw new Error('No authentication token found');
      }

      const backendUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      
      // Get CSRF token first
      const csrfResponse = await fetch(`${backendUrl}/csrf/csrf-token`, {
        credentials: 'include',
      });
      const csrfData = await csrfResponse.json();
      const csrfToken = csrfData.csrf_token;
      
      const response = await fetch(`${backendUrl}/remote-servers/${id}/check-status`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'X-API-KEY': apiKey || '',
          'X-CSRF-Token': csrfToken,
        },
        credentials: 'include',
      });
      if (!response.ok) throw new Error('Failed to check server status');
      const { status } = await response.json();
      setServers(prev => prev.map(s => s.id === id ? { ...s, status } : s));
      if (currentServer?.id === id) {
        setCurrentServer(prev => prev ? { ...prev, status } : null);
      }
      toast({
        title: 'Success',
        description: `Server status updated: ${status}`,
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to check server status');
      toast({
        title: 'Error',
        description: 'Failed to check server status',
        variant: 'destructive',
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <RemoteServerContext.Provider
      value={{
        servers,
        currentServer,
        loading,
        error,
        addServer,
        updateServer,
        deleteServer,
        switchServer,
        checkServerStatus,
        refreshServers: fetchServers,
      }}
    >
      {children}
    </RemoteServerContext.Provider>
  );
}

export function useRemoteServer() {
  const context = useContext(RemoteServerContext);
  if (context === undefined) {
    throw new Error('useRemoteServer must be used within a RemoteServerProvider');
  }
  return context;
} 