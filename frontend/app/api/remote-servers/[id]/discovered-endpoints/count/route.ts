import { NextResponse } from 'next/server';

export async function GET(
  request: Request,
  { params }: { params: { id: string } }
) {
  const backendUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
  const response = await fetch(
    `${backendUrl}/api/remote-servers/${params.id}/discovered-endpoints/count`
  );
  const data = await response.json();
  return NextResponse.json(data);
} 