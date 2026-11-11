from pydantic import BaseModel
from typing import Optional

# 登录成功后返回给客户端的Token
class Token(BaseModel):
    access_token: str
    token_type: str

# Token中编码的数据内容
class TokenData(BaseModel):
    username: Optional[str] = None