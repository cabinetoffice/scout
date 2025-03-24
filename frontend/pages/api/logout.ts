import type { NextApiRequest, NextApiResponse } from 'next';

export default function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method !== 'POST') {
    return res.status(405).json({ message: 'Method not allowed' });
  }

  // List of cookies to clear from the screenshot
  const cookiesToClear = [
    'AWSALB',
    'AWSALBAuthNonce',
    'AWSALBCORS',
    'AWSALBTG',
    'AWSALBTGCORS',
    'AWSELBAuthSessionCookie-0',
    'AWSELBAuthSessionCookie-1',
  ];

  // Clear all cookies
  const cookieClearingHeaders = cookiesToClear.map((cookieName) => {
    return `${cookieName}=; Path=/; Max-Age=0; Expires=Thu, 01 Jan 1970 00:00:00 GMT; Secure; SameSite=Strict`;
  });

  // Try clearing with domain as well
  const domainCookieClearingHeaders = cookiesToClear.map((cookieName) => {
    return `${cookieName}=; Path=/; Domain=${process.env.COOKIE_DOMAIN}; Max-Age=0; Expires=Thu, 01 Jan 1970 00:00:00 GMT; Secure; SameSite=Strict`;
  });

  // Set all the cookie-clearing headers
  res.setHeader('Set-Cookie', [...cookieClearingHeaders, ...domainCookieClearingHeaders]);

  return res.status(200).json({ message: 'Logged out successfully' });
}
