import { NextApiRequest, NextApiResponse } from 'next';
import { filterHeaderForAWSValues } from '@/utils/header'

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  const { method, headers } = req;

  try {
    // Extract the OIDC data from the request headers
    const oidcData = headers?.['x-amzn-oidc-data']; // Safely access the header
    const formattedOidcData = Array.isArray(oidcData) 
        ? oidcData.join(',')  // Convert array to comma-separated string
        : oidcData || '';      // Ensure it's always a string

    const requestInit: RequestInit = {
        method: 'GET',
        headers: {
            "Authorization": `Bearer ${headers?.['x-amzn-oidc-data']}`,
            ...filterHeaderForAWSValues(headers),
            'Content-Type': 'application/json',
            'x-amzn-oidc-data': formattedOidcData
        },
        credentials: "include"
    }

    const response = await fetch(process.env.BACKEND_HOST + '/api/admin/users', requestInit);

    if (!response.ok) {
      console.error(await response.text());
      throw new Error('Failed to fetch users from backend');
    }

    const users = await response.json();
    return res.status(200).json(users);
  } catch (error) {
    console.error('Error fetching or processing users:', error);
    return res.status(500).json({ error: 'Failed to fetch users' });
  }
}
