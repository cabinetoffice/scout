import { NextApiRequest, NextApiResponse } from 'next';
import { filterHeaderForAWSValues } from '@/utils/header';

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  const { method, headers, query } = req;

  try {
    // Extract the OIDC data from the request headers
    const oidcData = headers?.['x-amzn-oidc-data'];
    const formattedOidcData = Array.isArray(oidcData) 
      ? oidcData.join(',')
      : oidcData || '';

    const { page, page_size, status_filter } = query;
    
    const queryString = new URLSearchParams({
      ...(page && { page: page.toString() }),
      ...(page_size && { page_size: page_size.toString() }),
      ...(status_filter && { status_filter: status_filter.toString() })
    }).toString();

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

    const response = await fetch(`${process.env.BACKEND_HOST}/api/paginated_results?${queryString}`, requestInit);

    if (!response.ok) {
      console.error(await response.text());
      throw new Error('Failed to fetch paginated results');
    }

    const data = await response.json();
    return res.status(200).json(data);
  } catch (error) {
    console.error('Error fetching paginated results:', error);
    return res.status(500).json({ error: 'Failed to fetch paginated results' });
  }
}