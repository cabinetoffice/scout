import { NextApiRequest, NextApiResponse } from 'next';
import { filterHeaderForAWSValues } from '@/utils/header';

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method !== 'GET') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  try {
    const { headers, query } = req;
    const oidcData = headers?.['x-amzn-oidc-data'];
    const formattedOidcData = Array.isArray(oidcData) 
      ? oidcData.join(',')
      : oidcData || '';

    // Forward all query parameters
    const queryString = new URLSearchParams(query as Record<string, string>).toString();

    const requestInit: RequestInit = {
      method: 'GET',
      headers: {
        "Authorization": `Bearer ${headers?.['x-amzn-oidc-data']}`,
        ...filterHeaderForAWSValues(headers),
        'Content-Type': 'application/json',
        'x-amzn-oidc-data': formattedOidcData
      },
      credentials: "include"
    };

    const response = await fetch(
      `${process.env.BACKEND_HOST}/api/admin/audit-logs?${queryString}`,
      requestInit
    );

    if (!response.ok) {
      const errorText = await response.text();
      console.error('Error response from backend:', errorText);
      throw new Error('Failed to fetch audit logs');
    }

    const data = await response.json();
    return res.status(200).json(data);
  } catch (error) {
    console.error('Error in audit logs API route:', error);
    return res.status(500).json({ error: 'Failed to fetch audit logs' });
  }
}