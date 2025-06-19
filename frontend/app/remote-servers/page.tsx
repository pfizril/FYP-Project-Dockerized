'use client';

import React, { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { RemoteServerList } from '@/components/RemoteServerList';
import { RemoteServerForm } from '@/components/RemoteServerForm';
import { RemoteServerProvider } from '@/lib/contexts/RemoteServerContext';
import { useUser } from '@/lib/contexts/UserContext';
import { AppLayout } from '@/components/layout/app-layout';

export default function RemoteServersPage() {
  const { isAdmin, loading } = useUser();
  const router = useRouter();

  useEffect(() => {
    if (!loading && !isAdmin) {
      router.push('/');
    }
  }, [isAdmin, loading, router]);

  if (loading) {
    return null;
  }

  if (!isAdmin) {
    return null;
  }

  return (
    <AppLayout>
      <RemoteServerProvider>
        <div className="container mx-auto py-6 space-y-6">
          <div className="flex justify-between items-center">
            <h1 className="text-3xl font-bold">Remote Servers</h1>
            <RemoteServerForm />
          </div>
          <RemoteServerList />
        </div>
      </RemoteServerProvider>
    </AppLayout>
  );
} 