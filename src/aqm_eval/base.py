from pydantic import BaseModel


class AeBaseModel(BaseModel):
    model_config = {"frozen": True}
