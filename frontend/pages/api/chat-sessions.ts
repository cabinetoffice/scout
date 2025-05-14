import { NextApiRequest, NextApiResponse } from 'next';
import { filterHeaderForAWSValues } from '@/utils/header';

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  const { method, headers, body, query } = req;

  try {
    const oidcData = headers?.['x-amzn-oidc-data'];
    const formattedOidcData = Array.isArray(oidcData) 
      ? oidcData.join(',')
      : oidcData || '';

    const requestInit: RequestInit = {
      method: method,  // Use the actual method (GET/POST/PUT/DELETE)
      headers: {
        "Authorization": `Bearer ${headers?.['x-amzn-oidc-data']}`,
        ...filterHeaderForAWSValues(headers),
        'Content-Type': 'application/json',
        'x-amzn-oidc-data': formattedOidcData
      },
      credentials: "include"
    };

    // Add body for POST/PUT requests
    if (method === 'POST' || method === 'PUT') {
      requestInit.body = JSON.stringify(body);
    }

    let url = `${process.env.BACKEND_HOST}/api/chat-sessions`;
    
    // Add session ID to URL for PUT and DELETE methods
    if ((method === 'PUT' || method === 'DELETE') && query.sessionId) {
      url += `/${query.sessionId}`;
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
    const errorMessage = error instanceof Error ? error.message : String(error);
    return res.status(500).json({ 
      error: `Failed to handle chat sessions request: ${errorMessage}` 
    });
  }
}