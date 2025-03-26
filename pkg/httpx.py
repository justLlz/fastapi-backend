from typing import Any, Dict, Optional, Union

import httpx
from fastapi import HTTPException, status
from loguru import logger


class HTTPXClient:
    """
    HTTP Client 基于 httpx 封装的工具类，支持 GET, POST, PUT, DELETE 请求。
    """

    def __init__(self, base_url: str, timeout: int = 10, headers: Optional[Dict[str, str]] = None):
        """
        初始化 HTTP Client
        :param base_url: API 基础 URL
        :param timeout: 请求超时时间，默认 10 秒
        :param headers: 公共请求头，默认无
        """
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.headers = headers or {'content-type': 'application/json'}

    async def _request(
            self,
            method: str,
            endpoint: str,
            params: Optional[Dict[str, Any]] = None,
            data: Optional[Union[Dict[str, Any], str]] = None,
            json: Optional[Dict[str, Any]] = None,
            headers: Optional[Dict[str, str]] = None,
            timeout: Optional[int] = None,
    ) -> httpx.Response:
        """
        统一的请求方法
        :param method: 请求方法 (GET, POST, PUT, DELETE)
        :param endpoint: 接口路径
        :param params: 查询参数
        :param data: 表单数据
        :param json: JSON 数据
        :param headers: 请求头
        :param timeout: 超时时间
        :return: httpx.Response
        """
        try:
            async with httpx.AsyncClient(base_url=self.base_url, timeout=timeout or self.timeout) as client:
                response = await client.request(
                    method=method.upper(),
                    url=endpoint.lstrip('/'),
                    params=params,
                    data=data,
                    json=json,
                    headers={**self.headers, **(headers or {})},
                )
                response.raise_for_status()
                return response
        except httpx.HTTPStatusError as exc:
            # 处理 HTTP 错误状态码（如 4xx，5xx）
            logger.error(f"HTTPxStatusError: {exc.response.status_code} - {exc.response.text}")
            raise HTTPException(status_code=exc.response.status_code, detail=exc.response.text)
        except httpx.RequestError as e:
            logger.error(f"HTTPxRequestError: {repr(e)}")
            # 处理请求错误，例如网络问题
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    async def get(self, endpoint: str, params: Optional[Dict[str, Any]] = None,
                  headers: Optional[Dict[str, str]] = None) -> Any:
        """
        GET 请求
        :param endpoint: 接口路径
        :param params: 查询参数
        :param headers: 请求头
        :return: JSON 数据
        """
        response = await self._request("GET", endpoint, params=params, headers=headers)
        return response.json()

    async def post(self, endpoint: str, json: Optional[Dict[str, Any]] = None,
                   data: Optional[Union[Dict[str, Any], str]] = None,
                   headers: Optional[Dict[str, str]] = None) -> Any:
        """
        POST 请求
        :param endpoint: 接口路径
        :param json: JSON 数据
        :param data: 表单数据
        :param headers: 请求头
        :return: JSON 数据
        """
        response = await self._request("POST", endpoint, json=json, data=data, headers=headers)
        return response.json()

    async def put(self, endpoint: str, json: Optional[Dict[str, Any]] = None,
                  data: Optional[Union[Dict[str, Any], str]] = None,
                  headers: Optional[Dict[str, str]] = None) -> Any:
        """
        PUT 请求
        :param endpoint: 接口路径
        :param json: JSON 数据
        :param data: 表单数据
        :param headers: 请求头
        :return: JSON 数据
        """
        response = await self._request("PUT", endpoint, json=json, data=data, headers=headers)
        return response.json()

    async def delete(self, endpoint: str, json: Optional[Dict[str, Any]] = None,
                     headers: Optional[Dict[str, str]] = None) -> Any:
        """
        DELETE 请求
        :param endpoint: 接口路径
        :param json: JSON 数据
        :param headers: 请求头
        :return: JSON 数据
        """
        response = await self._request("DELETE", endpoint, json=json, headers=headers)
        return response.json()
