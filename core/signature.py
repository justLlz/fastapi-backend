import hashlib
import hmac
import time
from typing import Dict
from utils.logger import logger


class HMACSigner:
    def __init__(self, secret_key: str, hash_algorithm: str = "sha256", timestamp_tolerance: int = 300):
        """
        初始化 HMAC 签名工具类
        :param secret_key: 用于签名的密钥
        :param hash_algorithm: 哈希算法，默认为 sha256
        :param timestamp_tolerance: 时间戳容忍误差（秒），默认 300 秒
        """
        self.secret_key = secret_key.encode("utf-8")
        self.hash_algorithm = hash_algorithm
        self.timestamp_tolerance = timestamp_tolerance

    def generate_signature(self, data: Dict[str, str]) -> str:
        """
        生成签名
        :param data: 需要签名的字典数据
        :return: 签名字符串
        """
        # 对数据进行排序，确保签名一致性
        sorted_items = sorted(data.items())
        message = "&".join(f"{k}={v}" for k, v in sorted_items).encode("utf-8")
        # 生成 HMAC 签名
        signature = hmac.new(self.secret_key, message, getattr(hashlib, self.hash_algorithm)).hexdigest()
        return signature

    def verify_signature(self, data: Dict[str, str], signature: str) -> bool:
        """
        验证签名
        :param data: 需要验证的字典数据
        :param signature: 待验证的签名字符串
        :return: 验签结果，True 表示验证通过
        """
        expected_signature = self.generate_signature(data)
        return hmac.compare_digest(expected_signature, signature)

    def is_timestamp_valid(self, request_time: int) -> bool:
        """
        验证时间戳是否有效
        :param request_time: 请求时间戳
        :return:
        """
        try:
            request_time = int(request_time)
            # 获取当前 UTC 时间戳
            current_time = int(time.time())
            if (current_time - request_time) > self.timestamp_tolerance:
                logger.warning(f"invalid timestamp, request_time: {request_time}, current_time: {current_time}")
                return False
        except ValueError:
            return False

        return True


if __name__ == '__main__':
    signer = HMACSigner("oWjbDf6vDOwJQEoAxDXoDulPLdaFKPpdVKu2psBaaT9yugovFN6bSL")
    signature_data = {"timestamp": int(time.time()), "nonce": "xxaaqq"}
    print(signature_data)

    signature_str = signer.generate_signature(signature_data)
    print(signature_str)

    if not signer.is_timestamp_valid(signature_data['timestamp']):
        print("时间戳无效")

    if not signer.verify_signature(signature_data, signature_str):
        print("签名验证失败")
