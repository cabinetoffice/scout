import { NextApiRequest, NextApiResponse } from 'next'
import { filterHeaderForAWSValues } from '@/utils/header'

export default async function handler(
    req: NextApiRequest,
    res: NextApiResponse
): Promise<void> {
    const {
        method,
        headers
    } = req
    const { key } = req.query

    switch (method) {
        case 'GET':
            try {
                let keyPath: string;
                if (key === undefined) {
                    res.status(404);
                    break;
                }
                else if (typeof key == "string")
                    keyPath = key;
                else
                    keyPath = key.join("/");

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
                }

                const response = await fetch(`${process.env.BACKEND_HOST}/api/get_file_by_key/${keyPath}`, requestInit);
                
                if (!response.ok) {
                    throw new Error('Failed to get item by key');
                }

                // Forward the important headers from the backend response
                const contentType = response.headers.get('content-type');
                const contentDisposition = response.headers.get('content-disposition');
                const xFileType = response.headers.get('x-file-type');

                if (contentType) res.setHeader('Content-Type', contentType);
                if (contentDisposition) res.setHeader('Content-Disposition', contentDisposition);
                if (xFileType) res.setHeader('X-File-Type', xFileType);

                // Stream the response body
                res.status(200);
                const data = await response.arrayBuffer();
                res.send(Buffer.from(data));
            } catch (error) {
                let message;
                console.error(error);
                if (error instanceof Error) message = error.message;
                res.status(500).json({ error: message });
            }
            break;
        default:
            res.setHeader('Allow', ['GET']);
            res.status(405).end(`Method ${method} Not Allowed`);
            break;
    }
}