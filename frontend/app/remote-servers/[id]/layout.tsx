'use client';

import RemoteServerMainLayout from '@/components/remote-servers/RemoteServerMainLayout';

export default function Layout({ children, params }: { children: React.ReactNode, params: any }) {
  return <RemoteServerMainLayout params={params}>{children}</RemoteServerMainLayout>;
} 