'use client';

import React from 'react';
import { useRemoteServer } from '@/lib/contexts/RemoteServerContext';
import { ModernDashboard } from '@/components/dashboard/modern-dashboard';
import RemoteServerMainLayout from '@/components/remote-servers/RemoteServerMainLayout';

export default function StandaloneRemoteServerDashboardPage({ params }: { params: { id: string } }) {
  const { servers } = useRemoteServer();
  const server = servers.find(s => s.id === parseInt(params.id));

  if (!server) {
    return null;
  }

  return (
    <RemoteServerMainLayout params={params}>
      <ModernDashboard
        baseUrl={server.base_url}
        apiKey={server.api_key}
        isRemoteServer={true}
        serverId={server.id}
      />
    </RemoteServerMainLayout>
  );
} 