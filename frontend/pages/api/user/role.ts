import { NextApiRequest, NextApiResponse } from 'next';
import { filterHeaderForAWSValues } from '@/utils/header';

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  const { method, headers } = req;

  // Only allow GET requests
  if (method !== 'GET') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  try {
    const oidcData = headers?.['x-amzn-oidc-data'];
    const formattedOidcData = Array.isArray(oidcData) 
      ? oidcData.join(',')
      : oidcData || '';

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

    const response = await fetch(`${process.env.BACKEND_HOST}/api/user/role`, requestInit);

    if (!response.ok) {
      const errorText = await response.text();
      console.error('Error response from backend:', errorText);
      throw new Error(`Failed to fetch user role`);
    }

    const data = await response.json();
    return res.status(200).json(data);
  } catch (error) {
    console.error('Error handling user role request:', error);
    const errorMessage = error instanceof Error ? error.message : String(error);
    return res.status(500).json({ 
      error: `Failed to handle user role request: ${errorMessage}` 
    });
  }
}