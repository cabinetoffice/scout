Ingesting a project into production, step by step.

`<PROJECT_NAME>` refers to the name of the project you're ingesting.

1. Run `tofu apply` to get `bastion.pem` file created.
2. Run `ssh -v -N -i bastion.pem -L 5432:$(tofu output -raw rds_address):5432 ec2-user@$(tofu output -raw bastion_public_ip)` to create an SSH tunnel to the database. Leave this running.
3. Set up `.env` based on `.env.example`
4. Put your project's files under `.data/<PROJECT_NAME>`. The files must be directly in this directory (no subdirectories).
5. Create a vector store knowledge base for your project, along with an S3 bucket. See existing knowledge bases for settings.
6. Start the LibreOffice container: `docker compose up libreoffice`. You need working Docker for that.
7. If not yet done, setup the Python environment: `make install`
8. Start the Python console: `poetry run python`
9. Load your `.env` file:
```python
import dotenv
dotenv.load_dotenv()
```
10. Create a vector storage:
```python
import scout.Pipelines.utils
store = scout.Pipelines.utils.get_or_create_vector_store(".data/<PROJECT_NAME>/VectorStore")
```
11. Run the files' ingestion:
```python
import scout.Pipelines.ingest_project_data
scout.Pipelines.ingest_project_data.ingest_project_files("<PROJECT_NAME>", store)
```
12. Sync the knowledge base.

## Automation

Steps 9-12 are automated by a PoC script `scripts/ingest_project.py`.

Step 1 should be automated in Terraform or in the script.