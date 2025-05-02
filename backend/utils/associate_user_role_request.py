from pydantic import BaseModel

class AssociateUserToRoleRequest(BaseModel):
    user_id: str
    role: str
