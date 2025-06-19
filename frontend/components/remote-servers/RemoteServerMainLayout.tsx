'use client';

import React from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useRemoteServer, RemoteServerProvider } from '@/lib/contexts/RemoteServerContext';
import { Activity, Database, BarChart2, LayoutGrid } from 'lucide-react';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { ThemeToggle } from '@/components/theme-toggle';
import { cn } from '@/lib/utils';
import { SidebarProvider, SidebarTrigger, useSidebar } from '@/components/ui/sidebar';

export default function RemoteServerMainLayout({
  children,
  params,
}: {
  children: React.ReactNode;
  params: any;
}) {
  const unwrappedParams = typeof params.then === "function" ? React.use(params) : params;
  return (
    <RemoteServerProvider>
      <SidebarProvider>
        <RemoteServerMainLayoutContent params={unwrappedParams}>{children}</RemoteServerMainLayoutContent>
      </SidebarProvider>
    </RemoteServerProvider>
  );
}

function RemoteServerMainLayoutContent({
  children,
  params,
}: {
  children: React.ReactNode;
  params: any;
}) {
  const unwrappedParams = typeof params.then === "function" ? React.use(params) : params;
  const router = useRouter();
  const { servers } = useRemoteServer();
  const server = servers.find(s => s.id === parseInt(unwrappedParams.id));
  const { state } = useSidebar();

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

  // Sidebar navigation items
  const navItems = [
    {
      title: 'Dashboard',
      href: `/remote-servers/${server.id}/dashboard`,
      icon: Activity,
    },
    {
      title: 'Endpoints',
      href: `/remote-servers/${server.id}/endpoints`,
      icon: Database,
    },
    {
      title: 'Analytics',
      href: `/remote-servers/${server.id}/analytics`,
      icon: BarChart2,
    },
  ];

  return (
    <div className="min-h-screen flex w-full bg-background">
      {/* Sidebar */}
      <aside
        className={cn(
          'bg-sidebar text-sidebar-foreground border-r border-border flex flex-col transition-all duration-200',
          state === 'collapsed' ? 'w-0 md:w-16' : 'w-64'
        )}
        data-state={state}
      >
        {/* Sidebar Header */}
        <div className="flex items-center gap-2 px-4 py-2 h-16 border-b border-border">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary text-primary-foreground">
            <LayoutGrid className="h-4 w-4" />
          </div>
          {state !== 'collapsed' && (
            <div className="grid flex-1 text-left text-sm leading-tight">
              <span className="truncate font-semibold">{server.name}</span>
              <span className="truncate text-xs text-muted-foreground">Remote Server</span>
            </div>
          )}
        </div>
        {/* Navigation Label */}
        {state !== 'collapsed' && (
          <div className="px-6 pt-6 pb-2">
            <span className="text-xs font-semibold text-muted-foreground tracking-widest uppercase">Navigation</span>
          </div>
        )}
        {/* Sidebar Menu */}
        <nav className="flex-1">
          <ul className={cn('space-y-1', state !== 'collapsed' ? 'px-2' : 'px-0')}> 
            {navItems.map((item) => (
              <li key={item.href}>
                <Link href={item.href} legacyBehavior>
                  <a
                    className={cn(
                      'flex items-center gap-3 px-4 py-2 rounded-lg transition-colors font-medium text-sm',
                      'hover:bg-accent hover:text-accent-foreground',
                      state === 'collapsed' && 'justify-center px-2'
                    )}
                  >
                    <item.icon className="h-5 w-5" />
                    {state !== 'collapsed' && <span>{item.title}</span>}
                  </a>
                </Link>
              </li>
            ))}
          </ul>
        </nav>
      </aside>
      {/* Main Content */}
      <div className="flex-1 flex flex-col">
        <header className="flex h-16 shrink-0 items-center gap-2 border-b px-8 bg-muted/10">
          <SidebarTrigger className="mr-2" />
          <h1 className="text-2xl font-bold tracking-tight text-foreground">{server.name} <span className="text-base font-normal text-muted-foreground ml-2">Remote Server Dashboard</span></h1>
        </header>
        <main className="flex-1 p-6 bg-muted/10 overflow-y-auto">{children}</main>
      </div>
    </div>
  );
} 