import { NextApiRequest, NextApiResponse } from 'next'
import { filterHeaderForAWSValues } from '@/utils/header'

export default async function handler(
    req: NextApiRequest,
    res: NextApiResponse
): Promise<void> {
    const {
        query: { uuid },
        method,
        headers
    } = req
    switch (method) {
        case 'GET':
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

                console.log(`Headers in the uuid.ts request:: ${JSON.stringify(headers, null, 2)}`);
                console.log(`OIDC uuid.ts Data: ${oidcData}`);
                console.log(`Data uuid.ts being sent: ${JSON.stringify(requestInit, null, 2)}`);

                const response = await fetch(process.env.BACKEND_HOST + '/api/get_file/' + uuid, requestInit);
                if (!response.ok) {
                    throw new Error('Failed to get item by uuid');
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
                let message
                console.log(error)
                if (error instanceof Error) message = error.message
                res.status(500).send({ error: message })
            }
            break
        default:
            res.setHeader('Allow', ['GET'])
            res.status(405).end(`Method ${method} Not Allowed`)
            break
    }
}
