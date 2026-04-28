import os
import time
import threading
from typing import Dict, Tuple, Optional
import torch
from utils.logger import get_logger
from utils.utils import get_model_from_config

logger = get_logger()


class ModelManager:
    """
    模型管理器，用于缓存和复用已加载的模型
    避免重复加载相同的模型，提高处理效率
    """
    
    def __init__(self):
        self._models: Dict[str, Tuple[torch.nn.Module, object]] = {}  # model_key -> (model, config)
        self._lock = threading.RLock()
        self._model_load_times: Dict[str, float] = {}  # 记录模型加载时间，用于统计
    
    def _get_model_key(self, model_type: str, config_path: str, model_path: str, device: str, device_ids: list) -> str:
        """
        生成模型缓存键
        """
        # 使用模型类型、配置文件路径、模型文件路径和设备信息作为键
        device_str = f"{device}_{'-'.join(map(str, device_ids))}"
        return f"{model_type}_{config_path}_{model_path}_{device_str}"
    
    def get_model(self, model_type: str, config_path: str, model_path: str, device: str, device_ids: list) -> Tuple[torch.nn.Module, object]:
        """
        获取模型，如果已缓存则直接返回，否则加载并缓存
        """
        model_key = self._get_model_key(model_type, config_path, model_path, device, device_ids)
        
        with self._lock:
            if model_key in self._models:
                logger.info(f"使用缓存的模型: {model_key}")
                return self._models[model_key]
            
            # 模型未缓存，需要加载
            logger.info(f"加载新模型: {model_key}")
            start_time = time.time()
            
            try:
                model, config = get_model_from_config(model_type, config_path)
                
                # 加载模型权重
                if model_type in ["htdemucs", "apollo"]:
                    state_dict = torch.load(model_path, map_location=device, weights_only=False)
                    if "state" in state_dict:
                        state_dict = state_dict["state"]
                    if "state_dict" in state_dict:
                        state_dict = state_dict["state_dict"]
                else:
                    state_dict = torch.load(model_path, map_location=device, weights_only=True)
                
                model.load_state_dict(state_dict)
                
                # 多GPU支持
                if len(device_ids) > 1:
                    model = torch.nn.DataParallel(model, device_ids=device_ids)
                
                model = model.to(device)
                model.eval()
                
                # 缓存模型
                self._models[model_key] = (model, config)
                self._model_load_times[model_key] = time.time() - start_time
                
                logger.info(f"模型加载完成，耗时: {self._model_load_times[model_key]:.2f}秒")
                return model, config
                
            except Exception as e:
                logger.error(f"模型加载失败: {str(e)}")
                raise
    
    def clear_cache(self, model_key: Optional[str] = None):
        """
        清除模型缓存
        """
        with self._lock:
            if model_key:
                if model_key in self._models:
                    del self._models[model_key]
                    if model_key in self._model_load_times:
                        del self._model_load_times[model_key]
                    logger.info(f"清除模型缓存: {model_key}")
            else:
                # 清除所有缓存
                self._models.clear()
                self._model_load_times.clear()
                logger.info("清除所有模型缓存")
    
    def get_cache_info(self) -> Dict[str, float]:
        """
        获取缓存信息
        """
        with self._lock:
            return {
                "cached_models": len(self._models),
                "model_keys": list(self._models.keys()),
                "load_times": self._model_load_times.copy()
            }
    
    def is_model_cached(self, model_type: str, config_path: str, model_path: str, device: str, device_ids: list) -> bool:
        """
        检查模型是否已缓存
        """
        model_key = self._get_model_key(model_type, config_path, model_path, device, device_ids)
        with self._lock:
            return model_key in self._models


# 全局模型管理器实例
_model_manager = ModelManager()


def get_model_manager() -> ModelManager:
    """
    获取全局模型管理器实例
    """
    return _model_manager


def get_cached_model(model_type: str, config_path: str, model_path: str, device: str, device_ids: list) -> Tuple[torch.nn.Module, object]:
    """
    获取缓存的模型，如果不存在则加载并缓存
    """
    return _model_manager.get_model(model_type, config_path, model_path, device, device_ids)


def clear_model_cache(model_key: Optional[str] = None):
    """
    清除模型缓存
    """
    _model_manager.clear_cache(model_key)


def get_cache_info() -> Dict[str, float]:
    """
    获取缓存信息
    """
    return _model_manager.get_cache_info()
