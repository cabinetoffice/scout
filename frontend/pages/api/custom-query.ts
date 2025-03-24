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
        const { query } = req.body; // Accept query parameters from the request

        const data = {
          method: "POST",
          headers: {
            ...filterHeaderForAWSValues(headers), // Filter out cookies (not needed for backend requests)
            "Content-Type": "application/json", // Set Content-Type header
          },
          body: JSON.stringify({
            query: query,
            modelId: process.env.AWS_BEDROCK_MODEL_ID,
            knowledgeBaseId: process.env.AWS_BEDROCK_KNOWLEDGE_BASE_ID,
          }),
        };

        console.log(
          `Sending request to:  ${process.env.AWS_BEDROCK_LAMDA_URL}`
        );
        const response = await fetch(process.env.AWS_BEDROCK_LAMDA_URL!, data);

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
