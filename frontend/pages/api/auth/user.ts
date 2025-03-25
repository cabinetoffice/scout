import { NextApiRequest, NextApiResponse } from "next";

export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse
) {
  let user: string | string[] | undefined;
  console.log("user key", process.env.API_JWT_KEY);
  if (process.env.ENVIRONMENT == "local") user = process.env.API_JWT_KEY;
  else user = req.headers["x-amzn-oidc-data"];

  if (!user) {
    return res.status(401).json({ error: "Not authenticated" });
  }

  try {
    // Parse the JWT token (x-amzn-oidc-data is a JWT)
    const parts = (user as string).split(".");
    if (parts.length !== 3) {
      throw new Error("Invalid token format");
    }

    // Decode the payload (second part)
    const payload = Buffer.from(parts[1], "base64").toString();
    const userData = JSON.parse(payload);

    return res.status(200).json({
      id: userData.sub,
      email: userData.email,
      username: userData.username,
    });
  } catch (error) {
    console.error("Error parsing user data:", error);
    return res.status(500).json({ error: "Failed to parse user data" });
  }
}
