"""Registry infrastructure adapted from the course template."""

import os, json
from pathlib import Path
from typing import Optional, Self, Any
from abc import ABC, abstractmethod

__all__ = ["Registry"]


class Registry(ABC):

    _instance = None
    _registry_type = None

    def __new__(cls, file_name : str, registry_type : str, file_type : Optional[str]='json', **kwargs) -> Self:
        
        if cls._instance is None:
            # init
            obj = super().__new__(cls)
            obj._map = dict()
            # read files
            path = Path(__file__).resolve().parents[2] / 'static_files'
            file = os.path.join(path, f'{file_name}.{file_type}')
            if file_name != '' and os.path.exists(file):
                # resolve content
                if file_type == 'json':
                    with open(file, 'r', encoding='utf-8') as f:
                        for k, v in json.load(f).items():
                            obj.register(k, v)
                else:
                    raise Exception('Currently only supports json raw file.')
            # finalize
            cls._instance = obj
            cls._registry_type = registry_type
        return cls._instance
    
    @abstractmethod
    def register(self, key : Any, value : Any) -> None:
        if self.exists(key):
            pass 
            # raise ValueError(f'duplicate key : {key}')
            
    def get(self, key: Any, **args) -> Any:
        try: 
            return self._map[key.upper()]
        except:
            raise KeyError(f'no entry for key : {key}.')

    def clear(self) -> None:
        self._map.clear()

    def erase(self, key : Any) -> None:
        if not self.exists(key):
            raise KeyError('Cannot find this key.')
        self._map.pop(key)
    
    def exists(self, key : Any) -> None:
        return key in self._map

    def display_registry(self) -> None:
        for k, v in self._map.items():
            print(f'Key : {k}, Value : {v}.')

    @classmethod
    def reset_registry(cls) -> None:
        cls._instance = None

    @property
    def registry_name(self):
        return self._registry_type
    
    @property
    def get_keys(self):
        return list(self._map.keys())
