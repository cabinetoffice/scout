import { NextApiRequest, NextApiResponse } from 'next';
import { filterHeaderForAWSValues } from '@/utils/header';

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  const { method, headers, body } = req;

  if (method !== 'POST') {
    res.setHeader('Allow', ['POST']);
    res.status(405).end(`Method ${method} Not Allowed`);
    return;
  }

  try {
    const oidcData = headers?.['x-amzn-oidc-data'];
    const formattedOidcData = Array.isArray(oidcData) 
        ? oidcData.join(',')
        : oidcData || '';

    const requestInit: RequestInit = {
      method: 'POST',
      headers: {
        "Authorization": `Bearer ${headers?.['x-amzn-oidc-data']}`,
        ...filterHeaderForAWSValues(headers),
        'Content-Type': 'application/json',
        'x-amzn-oidc-data': formattedOidcData
      },
      body: body,
      credentials: "include"
    };

    const response = await fetch(process.env.BACKEND_HOST + '/api/admin/update_user', requestInit);

    if (!response.ok) {
      console.error(await response.text());
      throw new Error('Failed to update user role');
    }

    const result = await response.json();
    return res.status(200).json(result);
  } catch (error) {
    console.error('Error updating user role:', error);
    return res.status(500).json({ error: 'Failed to update user role' });
  }
}