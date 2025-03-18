
import { NextApiRequest, NextApiResponse } from 'next'
import { filterHeaderForAWSValues } from '@/utils/header'

export default async function handler(
    req: NextApiRequest,
    res: NextApiResponse
): Promise<void> {
    const {
        query,
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

                console.log(`Headers in the item.ts request:: ${JSON.stringify(headers, null, 2)}`);
                console.log(`OIDC item.ts Data: ${oidcData}`);
                console.log(`Data item.ts being sent: ${JSON.stringify(requestInit, null, 2)}`);

                const queryString = new URLSearchParams(query as any as URLSearchParams).toString();
                const response = await fetch(process.env.BACKEND_HOST + `/api/item?${queryString}`, requestInit);

                if (!response.ok) {
                    console.error(await response.text())
                    console.error(await response.json())
                    throw new Error('Failed to read items by attribute');
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
