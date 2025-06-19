'use client';

import React from 'react';
import { useRouter } from 'next/navigation';
import { useRemoteServer } from '@/lib/contexts/RemoteServerContext';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Loader2, RefreshCw, Trash2, Edit2, ExternalLink, Search } from 'lucide-react';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { formatDistanceToNow } from 'date-fns';
import { EditServerModal } from './EditServerModal';

export function RemoteServerList() {
  const router = useRouter();
  const {
    servers,
    currentServer,
    loading,
    switchServer,
    deleteServer,
    checkServerStatus,
    refreshServers,
  } = useRemoteServer();

  const [discoveryLoading, setDiscoveryLoading] = React.useState<{ [key: number]: boolean }>({});
  const [discoveredEndpoints, setDiscoveredEndpoints] = React.useState<{ [key: number]: number }>({});
  const [editingServer, setEditingServer] = React.useState<any>(null);
  const [editModalOpen, setEditModalOpen] = React.useState(false);

  const backendUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

  // Helper to get CSRF token and set cookie
  const getCsrfToken = async () => {
    const response = await fetch(`${backendUrl}/csrf/csrf-token`, {
      credentials: 'include', // so cookie is set
    });
    const data = await response.json();
    return data.csrf_token;
  };

  const runDiscovery = async (serverId: number) => {
    try {
      setDiscoveryLoading(prev => ({ ...prev, [serverId]: true }));
      // 1. Get CSRF token
      const csrfToken = await getCsrfToken();
      // 2. POST with CSRF token in header and credentials included
      const response = await fetch(`${backendUrl}/api/remote-servers/${serverId}/discover`, {
        method: 'POST',
        headers: {
          'X-CSRF-Token': csrfToken,
        },
        credentials: 'include',
      });
      if (!response.ok) throw new Error('Failed to run discovery');
      // 3. Fetch discovered endpoints count
      const countResponse = await fetch(`${backendUrl}/api/remote-servers/${serverId}/discovered-endpoints/count`);
      if (countResponse.ok) {
        const data = await countResponse.json();
        setDiscoveredEndpoints(prev => ({ ...prev, [serverId]: data.count }));
      }
    } catch (error) {
      console.error('Discovery failed:', error);
    } finally {
      setDiscoveryLoading(prev => ({ ...prev, [serverId]: false }));
    }
  };

  const handleEditServer = (server: any) => {
    setEditingServer(server);
    setEditModalOpen(true);
  };

  const handleEditSuccess = () => {
    setEditModalOpen(false);
    setEditingServer(null);
    refreshServers();
  };

  // Fetch discovered endpoints count for each server on component mount
  React.useEffect(() => {
    const fetchEndpointsCount = async () => {
      for (const server of servers) {
        try {
          const response = await fetch(`${backendUrl}/api/remote-servers/${server.id}/discovered-endpoints/count`);
          if (response.ok) {
            const data = await response.json();
            setDiscoveredEndpoints(prev => ({ ...prev, [server.id]: data.count }));
          }
        } catch (error) {
          console.error(`Failed to fetch endpoints count for server ${server.id}:`, error);
        }
      }
    };
    fetchEndpointsCount();
  }, [servers]);

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'online':
        return 'bg-green-500';
      case 'offline':
        return 'bg-red-500';
      case 'error':
        return 'bg-yellow-500';
      default:
        return 'bg-gray-500';
    }
  };

  return (
    <>
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>Remote Servers</CardTitle>
              <CardDescription>Manage your remote API servers</CardDescription>
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={() => refreshServers()}
              disabled={loading}
            >
              {loading ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <RefreshCw className="h-4 w-4" />
              )}
              <span className="ml-2">Refresh</span>
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead>Base URL</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Discovered Endpoints</TableHead>
                <TableHead>Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {servers.map((server) => (
                <TableRow
                  key={server.id}
                  className={currentServer?.id === server.id ? 'bg-muted' : ''}
                >
                  <TableCell className="font-medium">{server.name}</TableCell>
                  <TableCell>{server.base_url}</TableCell>
                  <TableCell>
                    <Badge
                      variant="secondary"
                      className={`${getStatusColor(server.status)} text-white`}
                    >
                      {server.status}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    {discoveredEndpoints[server.id] !== undefined ? (
                      <Badge variant="outline">
                        {discoveredEndpoints[server.id]} endpoints
                      </Badge>
                    ) : (
                      <span className="text-muted-foreground">Not checked</span>
                    )}
                  </TableCell>
                  <TableCell>
                    <div className="flex space-x-2">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => runDiscovery(server.id)}
                        disabled={discoveryLoading[server.id]}
                      >
                        {discoveryLoading[server.id] ? (
                          <Loader2 className="h-4 w-4 animate-spin" />
                        ) : (
                          <Search className="h-4 w-4" />
                        )}
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => window.open(`/remote-servers/${server.id}/dashboard`, '_blank')}
                      >
                        <ExternalLink className="h-4 w-4" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleEditServer(server)}
                      >
                        <Edit2 className="h-4 w-4" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => deleteServer(server.id)}
                        disabled={loading}
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
              {servers.length === 0 && (
                <TableRow>
                  <TableCell colSpan={5} className="text-center text-muted-foreground">
                    No remote servers found
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {editingServer && (
        <EditServerModal
          server={editingServer}
          open={editModalOpen}
          onOpenChange={setEditModalOpen}
          onSuccess={handleEditSuccess}
        />
      )}
    </>
  );
} 