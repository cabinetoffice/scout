import { NextApiRequest, NextApiResponse } from 'next';

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method === "GET") {
    const cognitoDomain = process.env.COGNITO_DOMAIN;
    const clientId = process.env.COGNITO_CLIENT_ID;
    const logoutUrl = process.env.LOGOUT_URL;
    
    // Redirect to Cognito logout endpoint
    const redirectUrl = `https://${cognitoDomain}/logout?client_id=${clientId}&logout_uri=${logoutUrl}/logout`;
    
    res.writeHead(302, { Location: redirectUrl });
    res.end();
  } else {
      res.status(405).json({ message: "Method Not Allowed" });
  }
}