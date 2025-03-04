# Using AWS Bedrock Knowledge Base with Scout

This document explains how to use AWS Bedrock Knowledge Base with Scout for project evaluation without needing to upload documents to S3 buckets within Scout.

## Overview

Scout now supports evaluating documents directly from an AWS Bedrock Knowledge Base, which offers several advantages:

1. **Data residency**: Documents remain in your AWS account, ensuring compliance with data residency and security requirements
2. **Pre-processed content**: Leverage AWS's document preprocessing capabilities
3. **Automatic updates**: Documents updated in your Knowledge Base are automatically reflected in future evaluations
4. **Simplified infrastructure**: No need to maintain separate document storage systems

## Setting up AWS Bedrock Knowledge Base

### Prerequisites

- AWS account with permissions to use Bedrock Knowledge Bases
- AWS IAM role with appropriate permissions
- AWS CLI configured with proper credentials

### Creating a Knowledge Base

1. Go to the AWS Management Console and navigate to Amazon Bedrock
2. Select "Knowledge bases" from the left navigation menu
3. Click "Create knowledge base"
4. Follow the wizard to:
   - Provide a name and description
   - Choose an S3 bucket for your documents
   - Select a data source configuration
   - Choose an embedding model (e.g., Amazon Titan Embeddings)
   - Review and create

### Uploading Documents

1. Upload your project documents to the S3 bucket configured with your Knowledge Base
2. Ensure the documents are in formats supported by AWS Bedrock (PDF, DOCX, TXT, etc.)
3. Wait for the Knowledge Base to process your documents (this can take some time)

## Running the Scout Bedrock KB Evaluator

### Environment Setup

Update your `.env` file with the following AWS Bedrock-specific variables:

```
AWS_BEDROCK_MODEL_ID=your-model-id
AWS_BEDROCK_EMBEDDING_MODEL_ID=your-embedding-model-id
AWS_BEDROCK_KB_ID=your-kb-id
AWS_REGION=your-aws-region
```

### Script Configuration

Edit the `scripts/analyse_bedrock_kb.py` script to configure:

1. Project name: How this evaluation will appear in Scout
2. Gate review: The review gate to evaluate against (e.g., GATE_2, GATE_3)
3. Criteria CSV list: Paths to CSV files containing your criteria

### Running the Evaluation

```
cd scout
poetry install  # Ensure dependencies are installed
poetry run python scripts/analyse_bedrock_kb.py
```

### Viewing Results

Visit the Scout frontend to view evaluation results:

```
http://localhost:3000
```

## Hosting in AWS

The Scout Bedrock KB evaluator can be hosted in AWS to automate evaluations on a schedule or in response to events. Here are deployment options:

### AWS Lambda

For scheduled or event-driven evaluations:

1. Package the Scout code and dependencies:

   ```
   pip install -t package/ -r requirements.txt
   cp -r scout/ package/
   cp scripts/analyse_bedrock_kb.py package/
   cd package && zip -r ../lambda_function.zip .
   ```

2. Create a Lambda function:

   - Runtime: Python 3.10+
   - Memory: At least 1024MB
   - Timeout: At least 5 minutes
   - Environment variables: Configure all required environment variables
   - IAM Role: Include permissions for Bedrock, RDS (for PostgreSQL), and S3

3. Set up triggers:
   - CloudWatch Events for scheduled runs
   - S3 notifications when new documents are added to your bucket
   - EventBridge rule for Knowledge Base updates

### AWS ECS/Fargate

For longer-running evaluations:

1. Create a Dockerfile for the Scout application
2. Build and push the Docker image to ECR
3. Set up an ECS task definition:

   - Configure environment variables
   - Set appropriate CPU and memory allocations
   - Configure networking and security groups

4. Deploy as a Fargate task:
   - Set up a CloudWatch Events rule for scheduling
   - Configure ECS to run the task on a schedule or in response to events

### AWS Step Functions

For complex evaluation workflows:

1. Break down the evaluation process into smaller Lambda functions or ECS tasks
2. Create a Step Functions state machine to orchestrate the workflow:

   - Ingest criteria
   - Retrieve documents from Knowledge Base
   - Evaluate documents against criteria
   - Store results in PostgreSQL
   - Notify stakeholders of completion

3. Trigger the state machine through:
   - CloudWatch Events
   - API Gateway
   - EventBridge events

## Security Considerations

When hosting in AWS, consider the following security measures:

1. IAM roles with the least privilege necessary
2. VPC configuration to isolate database access
3. KMS encryption for sensitive environment variables
4. CloudTrail monitoring for all Bedrock and related API calls
5. AWS Secrets Manager for database credentials

## Cost Considerations

Be aware of costs associated with:

- AWS Bedrock Knowledge Base storage and API usage
- AWS Bedrock model inference
- Compute resources (Lambda, ECS, etc.)
- Database storage and IOPS
- S3 storage and requests

Monitor usage and consider implementing cost controls such as usage alarms and budget constraints.
