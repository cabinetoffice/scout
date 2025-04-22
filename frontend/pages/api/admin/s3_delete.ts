import { NextApiRequest, NextApiResponse } from 'next'
import { filterHeaderForAWSValues } from '@/utils/header'

export default async function handler(
    req: NextApiRequest,
    res: NextApiResponse
): Promise<void> {
    const {
        query: { key },
        method,
        headers
    } = req
    switch (method) {
        case 'GET':
            try {
                console.log('delete key');
                console.log(key);
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

                const response = await fetch(process.env.BACKEND_HOST + '/api/admin/delete?key=' + key, requestInit);
                if (!response.ok) {
                    throw new Error('Failed to delete files');
                }

                res.status(200).send(await response.json())
                
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
