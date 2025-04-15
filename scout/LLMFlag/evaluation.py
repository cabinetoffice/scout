import os
import json
from abc import ABC, abstractmethod
from typing import List, Tuple, Dict, Any
from uuid import UUID

import boto3
import regex as re
from botocore.exceptions import ClientError
from langchain_core.vectorstores import VectorStore
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from scout.DataIngest.models.schemas import Chunk, ChunkBase, ChunkCreate, CriterionCreate, File, Project, ProjectCreate, ProjectUpdate, ResultCreate
from scout.LLMFlag.prompts import (
    CORE_SCOUT_PERSONA,
    DOCUMENT_EXTRACT_PROMPT,
    DOCUMENT_EXTRACTS_HEADER,
    SYSTEM_EVIDENCE_POINTS_PROMPT,
    SYSTEM_HYPOTHESIS_PROMPT,
    SYSTEM_QUESTION_PROMPT,
    USER_EVIDENCE_POINTS_PROMPT,
    USER_QUESTION_PROMPT,
    USER_REGENERATE_HYPOTHESIS_PROMPT,
)
from scout.LLMFlag.retriever import ReRankRetriever
from scout.utils.storage.storage_handler import BaseStorageHandler
from scout.utils.utils import logger


@retry(
    stop=stop_after_attempt(10),
    wait=wait_exponential(multiplier=1, min=4, max=10),
    retry=retry_if_exception_type((ClientError,)),
    before_sleep=lambda retry_state: logger.info(
        f"Retrying in {retry_state.next_action.sleep} seconds..."),
)
def api_call_with_retry(func, *args, **kwargs):
    try:
        return func(*args, **kwargs)
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code')
        if error_code == 'ThrottlingException':
            logger.warning(
                "Rate limit reached (ThrottlingException). Retrying...")
            raise
        elif error_code == 'ServiceUnavailable':
            logger.warning("Service unavailable. Retrying...")
            raise
        else:
            logger.error(f"AWS Bedrock API error occurred: {str(e)}")
            raise


class BaseEvaluator(ABC):
    def __init__(self):
        """Initialise the evaluator"""
        self.hypotheses = "None"

    @abstractmethod
    def evaluate_question(self, criteria_uuid: str) -> List[str]:
        """Get answers to a single question"""

    @abstractmethod
    def evaluate_questions(self, criteria_uuids: List[str]) -> List[str]:
        """Get answers to a list of questions"""

    @abstractmethod
    def _define_model(self):
        """Define the model that is the evaluator"""

    def semantic_search(self, query: str, k: int, filters: dict):
        # do retrieval
        search_kwargs = {"k": k, "filter": filters}
        retriever = ReRankRetriever(
            vectorstore=self.vector_store,
            search_type="similarity",
            search_kwargs=search_kwargs,
        )
        extracts = retriever.get_relevant_documents(query)

        # get files for metadata
        files = [
            self.storage_handler.read_item(object_id=UUID(
                extract.metadata["parent_doc_uuid"]), model=File)
            for extract in extracts
        ]

        # add extracts to prompt
        prompt = DOCUMENT_EXTRACTS_HEADER
        for idx, extract in enumerate(extracts):
            file = files[idx]
            if file is None:
                continue
            prompt += DOCUMENT_EXTRACT_PROMPT.format(
                file_name=getattr(file, "clean_name", file.name),
                source=getattr(file, "source", None),
                summary=getattr(file, "summary", None),
                date=getattr(file, "published_date", None),
                text=extract.page_content,
            )
        return prompt, extracts

    def _build_bedrock_request(self, messages: List[Dict]) -> Dict:
        """Builds a request body for the Bedrock API."""
        return {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 1000,
            "messages": messages,
        }
    
    def _invoke_bedrock_model(self, request_body: Dict) -> Dict:
        """Invokes the Bedrock model with the given request body and returns the response."""
        response = api_call_with_retry(
            self.llm.invoke_model,
            modelId=os.getenv("AWS_BEDROCK_MODEL_ID"),
            body=json.dumps(request_body)
        )
        return response

    def answer_question(
        self,
        question: str,
        evidence: str = None,
        k=3,
    ) -> Tuple:
        """Question answering logic for llms with error handling and retries"""

        try:
            # do q and a for each evidence point
            if evidence:
                evidence_list = [
                    item for item in evidence.split("_") if len(item) >= 5]
                evidence_responses_list = []
                for evidence_item in evidence_list:
                    extracts_prompt, extracts = self.semantic_search(
                        evidence_item, k=k, filters={
                            "project": str(self.project.id)}
                    )

                    # Create the message for Bedrock using Claude's expected format
                    evidence_messages = [
                        {
                            "role": "assistant",
                            "content": SYSTEM_EVIDENCE_POINTS_PROMPT
                        },
                        {
                            "role": "user",
                            "content": USER_EVIDENCE_POINTS_PROMPT.format(
                                question=question, extracts=extracts_prompt
                            )
                        }
                    ]
                    # Build the request for Bedrock.
                    request_body = self._build_bedrock_request(evidence_messages)

                    # Make the Bedrock API call
                    evidence_response = self._invoke_bedrock_model(request_body)

                    # Parse the response
                    response_body = json.loads(
                        evidence_response["body"].read().decode())
                    message_content = response_body["content"][0]["text"]

                    evidence_responses_list.append(message_content)
                evidence_answer_pairs = [
                    f"question: {q} answer: {a}" for q, a in zip(evidence_list, evidence_responses_list)
                ]
            else:
                evidence_answer_pairs = "None"

            # get an overall final answer using the answers to the earlier points
            extracts_prompt, extracts = self.semantic_search(
                question, k=k, filters={"project": str(self.project.id)})
            chunks = [extract['metadata']['uuid'] for extract in extracts]

            # Create the message for Bedrock using Claude's expected format
            question_messages = [
                {"role": "user", "content": SYSTEM_QUESTION_PROMPT + "\n\n" +
                    SYSTEM_HYPOTHESIS_PROMPT.format(hypotheses=self.hypotheses) + "\n\n" +
                    USER_QUESTION_PROMPT.format(
                        question=question,
                        extracts=extracts,
                        evidence_point_answers=evidence_answer_pairs,
                    )}
            ]
            # Build request and invoke model
            request_body = self._build_bedrock_request(question_messages)
            question_response = self._invoke_bedrock_model(request_body)
           
            # Parse the response
            response_body = json.loads(
                question_response["body"].read().decode())
            answer = response_body["content"][0]["text"]

            # Create a request for Bedrock using Claude's expected format
            hypo_messages = [
                {"role": "user", "content": CORE_SCOUT_PERSONA + "\n\n" +
                    USER_REGENERATE_HYPOTHESIS_PROMPT.format(
                        hypotheses=self.hypotheses,
                        questions_and_answers=question + answer,
                    ) + "\n\n" +
                    USER_QUESTION_PROMPT.format(
                        question=question,
                        extracts=extracts,
                        evidence_point_answers=evidence_answer_pairs,
                    )}
            ]
            # Build the request for Bedrock.
            hypo_request_body = self._build_bedrock_request(hypo_messages)

            # Make the Bedrock API call
            hypotheses_response = self._invoke_bedrock_model(hypo_request_body)

            # Parse the response
            hypo_response_body = json.loads(
                hypotheses_response["body"].read().decode())
            self.hypotheses = hypo_response_body["content"][0]["text"]

            return (answer, chunks)

        except Exception as e:
            logger.error(f"An error occurred: {str(e)}")
            raise


class MainEvaluator(BaseEvaluator):
    def __init__(
        self,
        project: ProjectCreate,
        vector_store: VectorStore,
        llm: Any,
        storage_handler: BaseStorageHandler,
    ):
        """Initialise the evaluator"""
        self.hypotheses = "None"
        self.vector_store = vector_store

        # Initialize Bedrock client if not provided
        if not hasattr(llm, 'invoke_model'):
            self.llm = boto3.client(
                service_name="bedrock-runtime",
                region_name=os.getenv("AWS_REGION")
            )
        else:
            self.llm = llm

        self.storage_handler = storage_handler
        self.project = project

        self._define_model()

    def evaluate_question(self, criterion: CriterionCreate, k: int = 3, save: bool = False) -> ResultCreate:
        """Get answers to a single question"""
        model_output = self.model(criterion=criterion)

        chunks_list = [
            self.storage_handler.read_item(uuid, Chunk) or ChunkBase(
                id=uuid,
                idx=0,
                text="Unknown",
                page_num=0,
                created_datetime="2024-01-01T00:00:00Z",
                updated_datetime="2024-01-01T00:00:00Z"
            )
            for uuid in model_output[2]
        ]
        result = ResultCreate(
            criterion=criterion,
            project=self.project,
            answer=model_output[0],
            full_text=model_output[1],
            chunks=chunks_list,
        )

        if save:
            result = self.storage_handler.write_item(result)

        return result

    def evaluate_questions(self, criteria: List[CriterionCreate], k: int = 3, save: bool = True) -> List[ResultCreate]:
        """Get answers to a list of questions"""
        results = []
        question_answer_pairs = []
        logger.info("Evaluating questions...")
        for idx, criterion in enumerate(criteria):
            result = self.evaluate_question(criterion, k, save)
            results.append(result)
            question_answer_pairs.append(
                (criterion.question, result.full_text))
            if idx % 5 == 0:
                logger.info(f"{idx} criteria complete")
        logger.info("Generating summary of answers...")
        # Generate summary of answers
        summary = self.generate_summary(question_answer_pairs)
        
        if isinstance(self.project, Project):
            self.project = ProjectUpdate(
                id=self.project.id,
                name=self.project.name,
                results_summary=summary,
                results=results
            )
        else:
            self.project.results_summary = summary
        self.storage_handler.update_item(self.project)
        return results

    def generate_summary(self, question_answer_pairs: List[tuple]) -> str:
        """Generate a summary of the answers using an LLM, with an input prompt containing instructions."""

        SUMMARIZE_RESPONSES_PROMPT = """You are a project delivery expert, you will be given question and answer pairs about a government project. Return a summary of the most important themes, you do not need to summarise all the questions, only return important, specific information. Be specific about project detail referred to. Return no more than 3 sentences. {qa_pairs}"""

        formatted_input = ", ".join(
            [f"Question: {qa[0]}\nAnswer: {qa[1]}" for qa in question_answer_pairs])
        
        
        logger.info(f"generate_summary formatted_input...{formatted_input}")
        
        # Create the message for Bedrock using Claude's expected format
        summary_messages = [
                {
                    "role": "user",
                    "content": SUMMARIZE_RESPONSES_PROMPT.format(qa_pairs=formatted_input)
                }
            ]

        # Build request and invoke model
        request_body = self._build_bedrock_request(summary_messages)
        response = self._invoke_bedrock_model(request_body)

        # Parse the response
        response_body = json.loads(response["body"].read().decode())
        return response_body["content"][0]["text"]

    def _define_model(self):
        """Define the model that is the evaluator"""

        def model(criterion: CriterionCreate, k: int = 3):
            full_text, chunks = self.answer_question(
                question=criterion.question,
                evidence=criterion.evidence,
                k=k,
            )

            # Find words within brackets and standalone words
            extracted_words = re.findall(
                r"\[(positive|neutral|negative)\]|\b(positive|neutral|negative)\b", full_text, re.IGNORECASE)

            if extracted_words:
                # Extract the last occurrence, regardless of format
                last_match = [
                    match for tup in extracted_words for match in tup if match]
                answer = last_match[-1].title()

                # Remove occurrences of words and brackets
                full_text = re.sub(
                    r"\[?(positive|neutral|negative)\]?", "", full_text, flags=re.IGNORECASE).strip()
            else:
                answer = "None"

            return (answer, full_text, chunks)

        self.model = model
        return model
