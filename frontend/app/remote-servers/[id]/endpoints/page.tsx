'use client';

import React from 'react';
import { useRemoteServer } from '@/lib/contexts/RemoteServerContext';
import RemoteServerMainLayout from '@/components/remote-servers/RemoteServerMainLayout';
import { RemoteServerEndpointsTable } from '@/components/remote-servers/RemoteServerEndpointsTable';

export default function RemoteServerEndpointsPage({ params }: { params: { id: string } }) {
  const { servers } = useRemoteServer();
  const server = servers.find(s => s.id === parseInt(params.id));

  if (!server) {
    return null;
  }

  // Ensure api_key is always a string
  const safeServer = { ...server, api_key: server.api_key || "" };

  return (
    <div className="space-y-6">
      <RemoteServerEndpointsTable server={safeServer} />
    </div>
  );
} 