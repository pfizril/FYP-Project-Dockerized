import React from 'react';
import { RemoteServerProvider } from '@/lib/contexts/RemoteServerContext';

export default function StandaloneDashboardLayout({ children }: { children: React.ReactNode }) {
  return (
    <RemoteServerProvider>
      <div className="dashboard-standalone">
        {/* Optional: Add a custom dashboard header or nav here */}
        <main>{children}</main>
      </div>
    </RemoteServerProvider>
  );
} 