"""明日方舟官服的开服检测：复用官方账号鉴权链路，只关心 `u8 /user/v1/getToken` 的结果。

鉴权链路（与官方客户端一致）：

1. `POST {account}/user/auth/v1/token_by_phone_password`：手机号密码换渠道 token。
2. `POST {account}/user/oauth2/v2/grant`：渠道 token 换一次性授权码。
3. `POST {u8}/user/v1/getToken`：授权码换游戏凭据；停服更新期间返回 `result: 1`。

第 1 步只在需要时执行：优先复用 `HYPERGRYPH_TOKEN`，其次复用缓存下来的渠道 token，
换取授权码失败才回退到重新登录，避免 30 秒一次的高频探测反复触发密码登录。
"""

import hashlib
import hmac
import json
import platform as host_platform
import urllib.parse
from dataclasses import dataclass
from typing import Any

import aiohttp
from nonebot.log import logger

from .config import plugin_config
from .storage import get_device_id

#: 官方网络配置的引导地址，账号服务与 u8 服务的地址都由它的响应派生。
NETWORK_CONFIG_URL = (
    "https://ak-conf.hypergryph.com/config/prod/official/network_config"
)
#: 取不到网络配置时使用的兜底地址。
DEFAULT_ACCOUNT_BASE = "https://as.hypergryph.com"
DEFAULT_U8_BASE = "https://as.hypergryph.com/u8"

PATH_PHONE_LOGIN = "/user/auth/v1/token_by_phone_password"
PATH_GRANT = "/user/oauth2/v2/grant"
PATH_U8_GET_TOKEN = "/user/v1/getToken"

APP_CODE = "7318def77669979d"
APP_ID = "1"
CHANNEL_ID = "1"
WORLD_ID = "1"
SUB_CHANNEL = "1"
PLATFORM = 2
DEVICE_TYPE = "2"
CAPTCHA_VERSION = "4.0"
#: u8 接口的签名密钥，取自官方客户端常量。
U8_SIGN_KEY = "91240f70c09a08a6bc72af1a5c8d4670"

ACCOUNT_USER_AGENT = "Mozilla/5.0"
GAME_USER_AGENT = "BestHTTP"
REQUEST_TIMEOUT = 15.0

#: `getToken` 的 result：1 表示仍在停机更新，0 表示正常签发游戏凭据。
RESULT_CLOSED = 1
RESULT_OK = 0


class ServerStatus:
    """探测结果。用字符串常量而不是 Enum，便于直接写进 JSON 与日志。"""

    OPEN = "open"
    CLOSED = "closed"
    UNKNOWN = "unknown"


class StatusCheckError(Exception):
    """探测失败：网络不可达、鉴权失败、风控要求验证或响应结构非预期。

    这类错误不代表服务器开服，调用方只记录日志、不改变已记录的状态。
    """


@dataclass(frozen=True)
class Endpoints:
    """账号服务与 u8 服务地址。"""

    account: str
    u8: str


def u8_sign(payload: dict[str, Any], key: str = U8_SIGN_KEY) -> str:
    """u8 请求签名：除 `sign` 外的字段按键排序拼成查询串，再用固定密钥做 HMAC-SHA1。"""
    query = urllib.parse.urlencode(
        sorted((name, value) for name, value in payload.items())
    )
    return hmac.new(
        key.encode("utf-8"), query.encode("utf-8"), hashlib.sha1
    ).hexdigest()


def classify_status(body: dict[str, Any]) -> str:
    """按 `getToken` 的响应判定服务器状态。"""
    result = body.get("result")
    if result == RESULT_CLOSED:
        return ServerStatus.CLOSED
    if result == RESULT_OK and body.get("token"):
        return ServerStatus.OPEN
    return ServerStatus.UNKNOWN


def _has_captcha(data: dict[str, Any]) -> bool:
    """判断响应是否要求人机验证。空 `captcha: {}` 与零值都视为「没有挑战」。"""
    if data.get("isCaptchaFailed"):
        return True
    return any(
        data.get(key) not in (None, "", 0, "0", [], {})
        for key in ("captcha", "captchaTips")
    )


def _brief(data: dict[str, Any]) -> str:
    """截断响应内容用于日志，避免把整份响应打出来。"""
    return json.dumps(data, ensure_ascii=False)[:300]


class ArknightsAuthClient:
    """官方账号鉴权的异步实现，只用于判定服务器是否已开服。"""

    def __init__(self) -> None:
        self._session: aiohttp.ClientSession | None = None
        self._endpoints: Endpoints | None = None
        self._channel_token: str | None = None

    async def close(self) -> None:
        if self._session is not None and not self._session.closed:
            await self._session.close()
        self._session = None

    # --- 传输 ---------------------------------------------------------------

    def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            # trust_env=False：不读取 HTTP(S)_PROXY 环境变量，避免代理配置影响探测。
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT),
                trust_env=False,
            )
        return self._session

    async def _request(
        self,
        method: str,
        url: str,
        payload: dict[str, Any] | None,
        headers: dict[str, str],
    ) -> dict[str, Any]:
        try:
            async with self._get_session().request(
                method, url, json=payload, headers=headers
            ) as response:
                status = response.status
                text = await response.text()
        except TimeoutError as error:
            raise StatusCheckError(f"请求 {url} 超时") from error
        except aiohttp.ClientError as error:
            raise StatusCheckError(f"请求 {url} 失败：{error}") from error

        try:
            data = json.loads(text)
        except json.JSONDecodeError as error:
            raise StatusCheckError(
                f"{url} 返回了非 JSON 响应（HTTP {status}）：{text[:200]!r}"
            ) from error
        if not isinstance(data, dict):
            raise StatusCheckError(f"{url} 返回了非预期结构：{text[:200]!r}")
        return data

    async def _post(
        self, url: str, payload: dict[str, Any], headers: dict[str, str]
    ) -> dict[str, Any]:
        return await self._request("POST", url, payload, headers)

    # --- 请求构造 -----------------------------------------------------------

    @property
    def _sdk_headers(self) -> dict[str, str]:
        """账号服务要求的渠道头，缺任何一项都可能被判定为异常客户端。"""
        device_id = get_device_id()
        return {
            "X-AppCode": APP_CODE,
            "X-Captcha-Version": CAPTCHA_VERSION,
            "X-DeviceId": device_id[:32],
            "X-DeviceId2": device_id,
            "X-DeviceModel": host_platform.node() or "Windows",
            "X-DeviceType": DEVICE_TYPE,
            "X-OSVer": host_platform.version(),
            "Content-Type": "application/json",
        }

    # --- 端点 ---------------------------------------------------------------

    async def _get_endpoints(self) -> Endpoints:
        if self._endpoints is not None:
            return self._endpoints
        try:
            endpoints = await self._fetch_endpoints()
        except StatusCheckError as error:
            logger.warning(
                "获取官方网络配置失败（{}），本次改用默认端点 {}",
                error,
                DEFAULT_ACCOUNT_BASE,
            )
            return Endpoints(account=DEFAULT_ACCOUNT_BASE, u8=DEFAULT_U8_BASE)
        self._endpoints = endpoints
        return endpoints

    async def _fetch_endpoints(self) -> Endpoints:
        data = await self._request(
            "GET", NETWORK_CONFIG_URL, None, {"User-Agent": ACCOUNT_USER_AGENT}
        )
        content = data.get("content")
        if isinstance(content, str):
            try:
                content = json.loads(content)
            except json.JSONDecodeError as error:
                raise StatusCheckError(f"网络配置无法解析：{error}") from error
        if not isinstance(content, dict):
            raise StatusCheckError("网络配置结构无效")

        configs = content.get("configs")
        if not isinstance(configs, dict) or not configs:
            raise StatusCheckError("网络配置缺少 configs")
        entry = configs.get(content.get("funcVer")) or next(iter(configs.values()))
        network = entry.get("network") if isinstance(entry, dict) else None
        if not isinstance(network, dict):
            raise StatusCheckError("网络配置缺少 network")

        account = str(network.get("as") or "").rstrip("/")
        u8 = str(network.get("u8") or "").rstrip("/")
        if not account or not u8:
            raise StatusCheckError("网络配置缺少账号服务或 u8 服务地址")
        return Endpoints(account=account, u8=u8)

    # --- 鉴权步骤 -----------------------------------------------------------

    async def _request_phone_token(
        self, endpoints: Endpoints, phone: str, password: str
    ) -> str:
        data = await self._post(
            f"{endpoints.account}{PATH_PHONE_LOGIN}",
            {"phone": phone, "password": password},
            {**self._sdk_headers, "User-Agent": ACCOUNT_USER_AGENT},
        )
        if _has_captcha(data):
            raise StatusCheckError(
                "手机号密码登录被要求人机验证，无法自动登录；请改用 HYPERGRYPH_TOKEN"
            )
        payload = data.get("data")
        token = payload.get("token") if isinstance(payload, dict) else None
        if not token:
            raise StatusCheckError(f"手机号密码登录失败：{_brief(data)}")
        return str(token)

    async def _request_grant(self, endpoints: Endpoints, channel_token: str) -> str:
        data = await self._post(
            f"{endpoints.account}{PATH_GRANT}",
            {"appCode": APP_CODE, "token": channel_token, "type": 0},
            {**self._sdk_headers, "User-Agent": ACCOUNT_USER_AGENT},
        )
        if _has_captcha(data):
            raise StatusCheckError("换取授权码被要求人机验证，无法自动登录")
        payload = data.get("data")
        code = payload.get("code") if isinstance(payload, dict) else None
        if not code:
            raise StatusCheckError(f"授权码签发失败：{_brief(data)}")
        return str(code)

    async def _request_u8_token(
        self, endpoints: Endpoints, code: str
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "appId": APP_ID,
            "channelId": CHANNEL_ID,
            "extension": json.dumps(
                {"code": code, "type": 1, "isSuc": True}, separators=(",", ":")
            ),
            "worldId": WORLD_ID,
            "platform": PLATFORM,
            "subChannel": SUB_CHANNEL,
            "deviceId": get_device_id(),
            "deviceId2": "",
            "deviceId3": "",
        }
        payload["sign"] = u8_sign(payload)
        return await self._post(
            f"{endpoints.u8}{PATH_U8_GET_TOKEN}",
            payload,
            {"User-Agent": GAME_USER_AGENT, "Content-Type": "application/json"},
        )

    # --- 对外接口 -----------------------------------------------------------

    async def _login(self, endpoints: Endpoints) -> str:
        if not plugin_config.has_password_credentials:
            raise StatusCheckError(
                "未配置 HYPERGRYPH_TOKEN，也缺少 HYPERGRYPH_PHONE / HYPERGRYPH_PASSWORD"
            )
        self._channel_token = await self._request_phone_token(
            endpoints,
            plugin_config.hypergryph_phone or "",
            plugin_config.hypergryph_password or "",
        )
        return self._channel_token

    async def _channel_token_for_check(self, endpoints: Endpoints) -> str:
        if self._channel_token:
            return self._channel_token
        if plugin_config.hypergryph_token:
            self._channel_token = plugin_config.hypergryph_token
            return self._channel_token
        return await self._login(endpoints)

    async def check_status(self) -> str:
        """探测当前服务器状态，返回 :class:`ServerStatus` 中的常量。

        :raises StatusCheckError: 探测过程中的任何失败；此时状态不可判定。
        """
        endpoints = await self._get_endpoints()
        try:
            code = await self._request_grant(
                endpoints, await self._channel_token_for_check(endpoints)
            )
        except StatusCheckError as error:
            if not plugin_config.has_password_credentials:
                raise
            logger.warning("渠道 token 换取授权码失败（{}），改为重新登录后重试", error)
            self._channel_token = None
            code = await self._request_grant(endpoints, await self._login(endpoints))

        body = await self._request_u8_token(endpoints, code)
        status = classify_status(body)
        if status == ServerStatus.UNKNOWN:
            logger.debug("u8 getToken 返回非预期结果：{}", _brief(body))
        return status


client = ArknightsAuthClient()
