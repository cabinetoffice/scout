import { NextApiRequest, NextApiResponse } from 'next';

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  // This route is actually not needed if ALB is handling authentication
  // Just redirect to the home page, and ALB will handle auth if needed
  res.redirect(302, '/');
}