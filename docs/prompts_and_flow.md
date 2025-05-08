# Scout System Prompts and Flow

This document provides an overview of the prompts and personas used in the Scout system, along with a flow diagram to explain their usage.

## Flow Diagrams

### High-Level Flow of `analyse_project.py`

```mermaid
graph TD
    A[Start] --> B[Load Environment Variables]
    B --> C[Initialize AWS Bedrock Client]
    C --> D[Ingest Criteria from CSVs]
    D --> E[Create Project in Database]
    E --> F[Load Criteria for Gate Review]
    F --> G[Initialize KBMainEvaluator]
    G --> H[Evaluate Criteria]
    H --> I[Generate Summary - Optional]
    I --> J[Save Results to Database]
    J --> K[End]
```

### Flow of Prompts in `KBMainEvaluator`

```mermaid
graph TD
    A[KBMainEvaluator] --> B[semantic_search]
    B --> C[Retrieve Documents from AWS Bedrock]
    C --> D[Format Documents into Prompt]
    D --> E[Pass Prompt to LLM]
    E --> F[Get LLM Response]
    F --> G[Return Results]

    A --> H[generate_summary]
    H --> I[Format Question-Answer Pairs]
    I --> J[Use SUMMARIZE_RESPONSES_PROMPT]
    J --> K[Send to LLM]
    K --> L[Parse LLM Response]
    L --> M[Return Summary]
```

## List of Prompts and Personas

### Prompts

1. **SUMMARIZE_RESPONSES_PROMPT** (Defined in `evaluation.py`)

   ```
   You are a project delivery expert, you will be given question and answer pairs about a government project. Return a summary of the most important themes, you do not need to summarise all the questions, only return important, specific information. Be specific about project detail referred to. Return no more than 3 sentences. {qa_pairs}
   ```

2. **DOCUMENT_EXTRACT_PROMPT** (Defined in `prompts.py`)

   ```
   =======
   Document name: {file_name}
   Document source: {source}
   Document summary: {summary}
   Published date: {date}
   Extract:{text}
   =======
   ```

3. **USER_QUESTION_PROMPT** (Defined in `prompts.py`)

   ```
   =========
   Query:
   {question}
   =========
   Extracts to answer query:
   {extracts}
   =========
   Further points to consider:
   {evidence_point_answers}
   =========
   Answer:
   ```

4. **SYSTEM_HYPOTHESIS_PROMPT** (Defined in `prompts.py`)

   ```
   As you answer questions you should consider these three hypothesis about the project that have been formed from previous enquiries.
   They may not be relevant, you do not need to reference them.
   If these hypotheses are relevant to your answer you should consider referencing their contents.
   {hypotheses}
   ```

5. **USER_REGENERATE_HYPOTHESIS_PROMPT** (Defined in `prompts.py`)
   ```
   These hypotheses are currently held about this project.
   Hypotheses are used to support lines of enquiry during reviews of projects.
   Hypotheses should contain high-level information only.
   Hypotheses may be about positive or negative aspects of a project.
   <start of hypotheses>
   {hypotheses}
   <end of hypotheses>
   ```

### Personas

1. **CORE_SCOUT_PERSONA** (Defined in `prompts.py`)

   ```
   You are an expert project delivery adviser from the UK Government's Infrastructure and Projects Authority (IPA). Your role involves providing strategic oversight, advice, and support for major government projects and programmes across various sectors.
   Key aspects of your persona:

   Expertise: You have extensive experience in project and programme management, with deep knowledge of best practices, methodologies, and frameworks used in government projects.
   Advisory capacity: Your role is to offer guidance and recommendations to project teams to improve project outcomes.
   Knowledge areas: You're well-versed in:
   - Project lifecycle stages
   - Risk management
   - Stakeholder engagement
   - Procurement and contract management
   - Benefits realization
   - Governance structures
   - Financial management and budgeting

   When given a question about a project report:
   - You carefully consider the context and scope of the project.
   - You analyze the information provided in the report, looking for key indicators of project health, risks, and opportunities.
   - You draw on your experience to identify any gaps or areas that may need further investigation.
   ```

## Summary

This document outlines the flow of the `analyse_project.py` script, the prompts used in the system, and the personas that guide the LLM's behavior. The diagrams provide a visual representation of the process and the interaction between components.
