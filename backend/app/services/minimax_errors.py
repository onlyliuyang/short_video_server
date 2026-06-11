"""MiniMax API exceptions."""


class MiniMaxAPIError(RuntimeError):
    """Base MiniMax API error."""

    def __init__(self, status_code: int, status_msg: str, *, retryable: bool = True):
        self.status_code = status_code
        self.status_msg = status_msg
        self.retryable = retryable
        super().__init__(self.user_message)

    @property
    def user_message(self) -> str:
        if self.status_code == 1026:
            return (
                "视频描述文本未通过 MiniMax 内容安全审核，请修改创作方案后新建任务重试。"
                "（重试会使用相同文案，无法绕过审核）"
            )
        return f"MiniMax 错误 {self.status_code}: {self.status_msg}"


def raise_for_base_resp(base_resp: dict) -> None:
    code = base_resp.get("status_code", 0)
    if code == 0:
        return
    msg = base_resp.get("status_msg", "unknown")
    retryable = code not in (1026,)
    raise MiniMaxAPIError(code, msg, retryable=retryable)
