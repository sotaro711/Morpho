from pydantic import BaseModel


class MeResponse(BaseModel):
    id: str
    email: str
