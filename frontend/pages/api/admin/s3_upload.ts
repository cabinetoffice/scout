import { NextApiRequest, NextApiResponse } from 'next';
import { filterHeaderForAWSValues } from '@/utils/header';
import { IncomingHttpHeaders } from 'http';

export const config = {
    api: {
        bodyParser: false,
    },
};

export default async function handler(
    req: NextApiRequest,
    res: NextApiResponse
): Promise<void> {
    const { method, headers } = req;

    if (method !== 'POST') {
        res.setHeader('Allow', ['POST']);
        res.status(405).end(`Method ${method} Not Allowed`);
        return;
    }

    try {
        // Extract the OIDC data from the request headers
        const oidcData = headers?.['x-amzn-oidc-data']; // Safely access the header
        const formattedOidcData = Array.isArray(oidcData)
            ? oidcData.join(',') // Convert array to comma-separated string
            : oidcData || ''; // Ensure it's always a string

        // Prepare headers for the backend request
        // Important: Forward the original Content-Type header for FormData
        const backendHeaders: HeadersInit = {
            Authorization: `Bearer ${headers?.['x-amzn-oidc-data']}`,
            ...filterHeaderForAWSValues(headers as IncomingHttpHeaders), // Cast headers
            'x-amzn-oidc-data': formattedOidcData,
            // Do NOT set Content-Type manually to application/json
            // Forward the original Content-Type from the client request
            ...(headers['content-type'] && { 'Content-Type': headers['content-type'] }),
        };

        const requestInit: RequestInit = {
            method: 'POST',
            headers: backendHeaders,
            body: req as any, // Pass the incoming request stream directly
            // @ts-ignore // Required for Node.js fetch to stream request body
            duplex: 'half',
            credentials: 'include',
        };

        console.log('Calling FastAPI s3 upload...');
        const backendUrl = `${process.env.BACKEND_HOST}/api/admin/upload`;
        const response = await fetch(backendUrl, requestInit);

        const responseBodyText = await response.text(); // Read body once

        if (!response.ok) {
            console.error(`Backend request failed with status: ${response.status}`);
            console.error('Backend response:', responseBodyText);
            // Attempt to parse as JSON for more detailed error, fallback to text
            try {
                const errorJson = JSON.parse(responseBodyText);
                 console.error('Backend JSON error:', errorJson);
                 throw new Error(errorJson.detail || 'Failed to upload files');
            } catch (e) {
                 throw new Error(`Failed to upload files. Status: ${response.status}`);
            }
        }

        // Assuming the backend responds with JSON on success
        try {
            const responseData = JSON.parse(responseBodyText);
            res.status(response.status).json(responseData);
        } catch (e) {
             console.error('Failed to parse successful backend response as JSON:', e);
             // If backend might send non-JSON success response, handle accordingly
             res.status(response.status).send(responseBodyText);
        }

    } catch (error) {
        console.error('Error in s3_upload handler:', error);
        const message = error instanceof Error ? error.message : 'An unknown error occurred';
        res.status(500).json({ error: `Failed to upload files: ${message}` });
    }
}
