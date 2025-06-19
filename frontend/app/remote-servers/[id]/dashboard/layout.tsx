import React from 'react';

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="dashboard-standalone">
      {/* Optional: Add a custom dashboard header or nav here */}
      <main>{children}</main>
    </div>
  );
} 