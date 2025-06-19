'use client';

import React from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useRemoteServer, RemoteServerProvider } from '@/lib/contexts/RemoteServerContext';
import { Activity, Database, BarChart2 } from 'lucide-react';

export default function RemoteServerMainLayout({
  children,
  params,
}: {
  children: React.ReactNode;
  params: { id: string };
}) {
  return (
    <RemoteServerProvider>
      <RemoteServerMainLayoutContent params={params}>{children}</RemoteServerMainLayoutContent>
    </RemoteServerProvider>
  );
}

function RemoteServerMainLayoutContent({
  children,
  params,
}: {
  children: React.ReactNode;
  params: { id: string };
}) {
  const router = useRouter();
  const { servers } = useRemoteServer();
  const server = servers.find(s => s.id === parseInt(params.id));

  if (!server) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-center">
          <h2 className="text-2xl font-bold mb-2">Server Not Found</h2>
          <p className="text-muted-foreground mb-4">The requested server could not be found.</p>
          <button
            onClick={() => router.push('/remote-servers')}
            className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
          >
            Back to Servers
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen bg-background">
      {/* Sidebar */}
      <aside className="w-64 bg-[#181C23] border-r border-border flex flex-col">
        <div className="h-16 flex items-center justify-center border-b border-border">
          <span className="text-lg font-bold tracking-tight text-white">{server.name}</span>
        </div>
        <nav className="flex-1 py-6">
          <ul className="space-y-2">
            <li>
              <Link href={`/remote-servers/${server.id}/dashboard`} legacyBehavior>
                <a className="flex items-center px-6 py-2 text-white hover:bg-[#23272F] rounded transition-colors">
                  <Activity className="h-5 w-5 mr-3" /> Dashboard
                </a>
              </Link>
            </li>
            <li>
              <Link href={`/remote-servers/${server.id}/endpoints`} legacyBehavior>
                <a className="flex items-center px-6 py-2 text-white hover:bg-[#23272F] rounded transition-colors">
                  <Database className="h-5 w-5 mr-3" /> Endpoints
                </a>
              </Link>
            </li>
            <li>
              <Link href={`/remote-servers/${server.id}/analytics`} legacyBehavior>
                <a className="flex items-center px-6 py-2 text-white hover:bg-[#23272F] rounded transition-colors">
                  <BarChart2 className="h-5 w-5 mr-3" /> Analytics
                </a>
              </Link>
            </li>
          </ul>
        </nav>
      </aside>
      {/* Main Content */}
      <main className="flex-1 flex flex-col">
        <header className="h-16 flex items-center px-8 border-b border-border bg-background">
          <h1 className="text-2xl font-bold tracking-tight text-foreground">{server.name} <span className="text-base font-normal text-muted-foreground ml-2">Remote Server Dashboard</span></h1>
        </header>
        <div className="flex-1 p-8 overflow-y-auto">{children}</div>
      </main>
    </div>
  );
} 