import { NextApiRequest, NextApiResponse } from 'next';
import { filterHeaderForAWSValues } from '@/utils/header';

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  const { method, headers } = req;

  try {
    // Extract the OIDC data from the request headers
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

    const response = await fetch(`${process.env.BACKEND_HOST}/api/summary`, requestInit);

    if (!response.ok) {
      const errorText = await response.text();
      console.error('Error response from backend:', errorText);
      throw new Error('Failed to fetch summary data');
    }

    const data = await response.json();
    return res.status(200).json(data);
  } catch (error) {
    console.error('Error in summary API route:', error);
    return res.status(500).json({ error: 'Failed to fetch summary data' });
  }
}