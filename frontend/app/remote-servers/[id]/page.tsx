'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';

export default function RemoteServerRedirectPage({ params }: { params: { id: string } }) {
  const router = useRouter();
  useEffect(() => {
    if (params?.id) {
      router.replace(`/remote-servers/${params.id}/dashboard`);
    }
  }, [params, router]);
  return null;
} 