import { NextApiRequest, NextApiResponse } from "next";
import { filterHeaderForAWSValues } from "@/utils/header";

export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse
): Promise<void> {
  const { method, headers, body } = req;

  switch (method) {
    case "POST":
      try {
        // Extract the OIDC data from the request headers
        const oidcData = headers?.["x-amzn-oidc-data"];
        const formattedOidcData = Array.isArray(oidcData)
          ? oidcData.join(",")
          : oidcData || "";

        const { query, chat_session_id, model_id } = body;

        const requestInit: RequestInit = {
          method: "POST",
          headers: {
            Authorization: `Bearer ${headers?.["x-amzn-oidc-data"]}`,
            ...filterHeaderForAWSValues(headers),
            "Content-Type": "application/json",
            "x-amzn-oidc-data": formattedOidcData,
          },
          credentials: "include",
          body: JSON.stringify({ query, chat_session_id, model_id }),
        };

        console.log(
          `Sending request to: ${process.env.BACKEND_HOST}/api/custom-query`
        );

        const response = await fetch(
          `${process.env.BACKEND_HOST}/api/custom-query`,
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
