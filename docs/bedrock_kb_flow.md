# AWS Bedrock Knowledge Base Integration Flow

This document visualizes how Scout integrates with AWS Bedrock Knowledge Base for document retrieval and evaluation.

## Basic Architecture

```mermaid
flowchart TB
    subgraph "AWS Cloud"
        S3[(S3 Bucket)]
        KB[Bedrock Knowledge Base]
        BLM[Bedrock LLM]
        S3 --> KB
    end

    subgraph "Scout System"
        Script[analyse_bedrock_kb.py]
        DB[(PostgreSQL)]
        Frontend[Scout Frontend]
    end

    KB <--> Script
    BLM <--> Script
    Script --> DB
    DB <--> Frontend

    User[User] --> Frontend

    classDef aws fill:#FF9900,stroke:#232F3E,stroke-width:2px;
    classDef scout fill:#1CE783,stroke:#232F3E,stroke-width:2px;
    classDef user fill:#ADD8E6,stroke:#232F3E,stroke-width:2px;

    class S3,KB,BLM aws;
    class Script,DB,Frontend scout;
    class User user;
```

## Detailed Evaluation Process

```mermaid
sequenceDiagram
    participant User
    participant Script as analyse_bedrock_kb.py
    participant KB as AWS Bedrock KB
    participant LLM as AWS Bedrock LLM
    participant DB as PostgreSQL
    participant Frontend

    User->>Script: Run evaluation
    Script->>DB: Load criteria
    Script->>DB: Create project

    loop For Each Criterion
        Script->>KB: Semantic search query
        KB-->>Script: Retrieve relevant documents
        Script->>LLM: Generate evaluation with context
        LLM-->>Script: Return evaluation
        Script->>DB: Save result
    end

    Script->>LLM: Generate summary
    LLM-->>Script: Return summary
    Script->>DB: Update project with summary
    User->>Frontend: View results
    Frontend->>DB: Fetch evaluation results
    DB-->>Frontend: Return results
    Frontend-->>User: Display evaluation
```

## AWS Hosting Options

```mermaid
flowchart TB
    subgraph "AWS Hosting Options"
        Lambda[AWS Lambda]
        ECS[ECS/Fargate]
        Step[Step Functions]
    end

    subgraph "Triggers"
        Schedule[CloudWatch Schedule]
        Event[EventBridge Events]
        S3Event[S3 Notifications]
        API[API Gateway]
    end

    subgraph "AWS Services"
        KB[Bedrock Knowledge Base]
        BLM[Bedrock LLM]
        RDS[(Amazon RDS)]
        Secret[Secrets Manager]
    end

    Schedule --> Lambda
    Schedule --> ECS
    Schedule --> Step
    Event --> Lambda
    Event --> Step
    S3Event --> Lambda
    API --> Lambda
    API --> Step

    Lambda --> KB
    Lambda --> BLM
    Lambda --> RDS
    Lambda --> Secret

    ECS --> KB
    ECS --> BLM
    ECS --> RDS
    ECS --> Secret

    Step --> KB
    Step --> BLM
    Step --> RDS
    Step --> Secret

    classDef aws fill:#FF9900,stroke:#232F3E,stroke-width:2px;
    classDef trigger fill:#4CAF50,stroke:#232F3E,stroke-width:2px;

    class Lambda,ECS,Step,KB,BLM,RDS,Secret aws;
    class Schedule,Event,S3Event,API trigger;
```

## Custom Evaluator Architecture

```mermaid
classDiagram
    class BaseEvaluator {
        <<abstract>>
        +semantic_search(query, k, filters)
        +answer_question(question, evidence, k)
        +evaluate_question(criterion, k, save)
        +evaluate_questions(criteria, k, save)
        #_define_model()
    }

    class MainEvaluator {
        -vector_store
        -llm
        -storage_handler
        -project
        +generate_summary(question_answer_pairs)
    }

    class KBMainEvaluator {
        +semantic_search(query, k, filters) override
    }

    class BedrockKnowledgeBase {
        -kb_id
        -retriever_id
        -region_name
        -bedrock_runtime
        -bedrock_agent
        +retrieve(query, max_results)
        +query_with_llm(query, system_prompt)
    }

    BaseEvaluator <|-- MainEvaluator
    MainEvaluator <|-- KBMainEvaluator
    KBMainEvaluator --> BedrockKnowledgeBase : uses
```

## Document Flow in Scout with Bedrock KB

```mermaid
graph TD
    subgraph "AWS S3"
        S3Files[Project Documents]
    end

    subgraph "AWS Bedrock"
        KB[Knowledge Base]
    end

    subgraph "Scout System"
        Criteria[Criteria CSV Files]
        ScriptKB[analyse_bedrock_kb.py]
        DB[(PostgreSQL)]
        Results[Evaluation Results]
    end

    S3Files --> KB
    KB --> ScriptKB
    Criteria --> ScriptKB
    ScriptKB --> DB
    DB --> Results

    classDef aws fill:#FF9900,stroke:#232F3E,stroke-width:2px;
    classDef scout fill:#1CE783,stroke:#232F3E,stroke-width:2px;

    class S3Files,KB, aws;
    class Criteria,ScriptKB,DB,Results scout;
```
