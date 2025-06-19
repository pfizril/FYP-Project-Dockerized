'use client';

import { RemoteServerDashboard } from '@/components/remote-servers/RemoteServerDashboard';

export default function RemoteServerDashboardPage({ params }: { params: any }) {
  const serverId = parseInt(params.id, 10);
  return <RemoteServerDashboard serverId={serverId} />;
} 