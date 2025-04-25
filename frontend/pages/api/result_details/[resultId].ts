import { NextApiRequest, NextApiResponse } from 'next';
import { filterHeaderForAWSValues } from '@/utils/header';

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  const { method, headers, query } = req;
  const { resultId } = query;

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

    const response = await fetch(`${process.env.BACKEND_HOST}/api/result_details/${resultId}`, requestInit);

    if (!response.ok) {
      console.error(await response.text());
      throw new Error('Failed to fetch result details');
    }

    const data = await response.json();
    return res.status(200).json(data);
  } catch (error) {
    console.error('Error fetching result details:', error);
    return res.status(500).json({ error: 'Failed to fetch result details' });
  }
}