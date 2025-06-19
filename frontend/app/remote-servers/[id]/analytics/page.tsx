"use client";

import React from "react";
import { RemoteServerAnalyticsDashboard } from "@/components/remote-servers/RemoteServerAnalyticsDashboard";
import { useRemoteServer } from "@/lib/contexts/RemoteServerContext";

export default function RemoteServerAnalyticsPage({ params }: { params: { id: string } }) {
  const { servers } = useRemoteServer();
  const server = servers.find((s) => s.id === parseInt(params.id));

  if (!server) {
    return null;
  }

  return <RemoteServerAnalyticsDashboard serverId={server.id} />;
} 