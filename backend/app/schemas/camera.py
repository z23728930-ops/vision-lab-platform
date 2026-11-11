from symtable import Class

from pydantic import BaseModel
from typing import Optional, List, Dict, Any, Union


# 单个相机参数的模型
class CameraParameter(BaseModel):
    name: str
    key: int  # OpenCV的属性ID, e.g., cv2.CAP_PROP_FRAME_WIDTH
    value: float
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    step: Optional[float] = None
    type: str = "slider"  # UI提示：可以是 'slider', 'dropdown', 'input'

# 用于更新参数的简化模型
class CameraParameterUpdate(BaseModel):
    key: int
    value: float

# 整个相机的参数配置
class CameraConfig(BaseModel):
    parameters: List[CameraParameterUpdate]

# 相机标定结果的模型
class CalibrationResult(BaseModel):
    camera_matrix: List[List[float]]
    distortion_coefficients: List[float]
    rmse: float # 重投影误差

class CameraConnectRequest(BaseModel):
    camera_source: Union[int, str] # 可以是整数ID或字符串URL