import { NextApiRequest, NextApiResponse } from 'next';
import { filterHeaderForAWSValues } from '@/utils/header';

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  try {
    const { headers, method, body } = req;
    // Extract the OIDC data from the request headers
    const oidcData = headers?.['x-amzn-oidc-data'];
    const formattedOidcData = Array.isArray(oidcData) 
      ? oidcData.join(',')
      : oidcData || '';

    const requestInit: RequestInit = {
      method,
      headers: {
        "Authorization": `Bearer ${headers?.['x-amzn-oidc-data']}`,
        ...filterHeaderForAWSValues(headers),
        'Content-Type': 'application/json',
        'x-amzn-oidc-data': formattedOidcData
      },
      credentials: "include"
    };

    // Add body for POST, PUT methods
    if (method === 'POST' || method === 'PUT') {
      requestInit.body = JSON.stringify(body);
    }

    // Handle different endpoints based on the method and URL pattern
    let url = `${process.env.BACKEND_HOST}/api/chat-sessions`;
    
    // Add session ID to URL for PUT and DELETE methods
    if ((method === 'PUT' || method === 'DELETE') && req.query.sessionId) {
      url += `/${req.query.sessionId}`;
    }

    const response = await fetch(url, requestInit);

    if (!response.ok) {
      const errorText = await response.text();
      console.error('Error response from backend:', errorText);
      throw new Error(`Failed to ${method?.toLowerCase()} chat sessions`);
    }

    const data = await response.json();
    return res.status(200).json(data);
  } catch (error) {
    console.error('Error handling chat sessions:', error);
    return res.status(500).json({ 
      error: `Failed to handle chat sessions request: ${error.message}` 
    });
  }
}