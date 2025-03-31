from pydantic import BaseModel

class AssociateUserToProjectRequest(BaseModel):
    user_id: str
    project_id: str
