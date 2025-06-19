import React from 'react';
import { RemoteServerSimpleDashboard } from './RemoteServerSimpleDashboard';
import { APIClient } from '@/lib/api-client';

interface RemoteServerDashboardProps {
  serverId: number;
  client?: APIClient;
}

export function RemoteServerDashboard({ serverId, client }: RemoteServerDashboardProps) {
  return <RemoteServerSimpleDashboard serverId={serverId} client={client} />;
} 