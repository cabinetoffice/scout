import { NextApiRequest, NextApiResponse } from "next";
import { filterHeaderForAWSValues } from "@/utils/header";
import { mode } from "d3";

export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse
): Promise<void> {
  const { method, headers } = req;
  switch (method) {
    case "POST":
      try {
        // Extract the OIDC data from the request headers
        const oidcData = headers?.["x-amzn-oidc-data"]; // Safely access the header
        const formattedOidcData = Array.isArray(oidcData)
          ? oidcData.join(",") // Convert array to comma-separated string
          : oidcData || ""; // Ensure it's always a string

        const requestInit: RequestInit = {
          method: "POST",
          headers: {
            Authorization: `Bearer ${headers?.["x-amzn-oidc-data"]}`,
            ...filterHeaderForAWSValues(headers),
            "Content-Type": "application/json",
            "x-amzn-oidc-data": formattedOidcData,
          },
          credentials: "include",
        };

        console.log(
          `Sending request to:  ${process.env.BACKEND_HOST}/api/custom-query`
        );
        const response = await fetch(
          `${
            process.env.BACKEND_HOST
          }/api/custom-query?query=${encodeURIComponent(req.body.query)}`,
          requestInit
        );

        if (!response.ok) {
          console.error(await response.text());
          throw new Error("Failed to get response from Python backend");
        }
        res.status(200).send(await response.json());
      } catch (error) {
        let message;
        console.log(error);
        if (error instanceof Error) message = error.message;
        res.status(500).send({ error: message });
      }
      break;
    default:
      res.setHeader("Allow", ["POST"]);
      res.status(405).end(`Method ${method} Not Allowed`);
      break;
  }
}
