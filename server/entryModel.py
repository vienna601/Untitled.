from pydantic import BaseModel

#entry format
class Entry(BaseModel):
    prompt: str        
    response: str     
    timestamp: int 
