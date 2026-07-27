"""OCR Provider 接口与数据模型 —— 可插拔 OCR。

provider 可切换（local/cloud/mock），单测用 mock 保证确定性。真实 OCR 引擎选择可变，
故以命令模板（local）解耦具体引擎（如 paddleocr）。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from app.core.config import settings


@dataclass
class OcrTextBlock:
    text: str
    confidence: float
    bbox: list[int]
    order_index: int


@dataclass
class OcrResult:
    # success/unavailable/failed
    status: str
    blocks: list[OcrTextBlock] = field(default_factory=list)
    raw_json: dict = field(default_factory=dict)
    error_message: str = ""

    @property
    def text(self) -> str:
        """按 order_index 顺序拼接的纯文本。"""
        ordered = sorted(self.blocks, key=lambda b: b.order_index)
        return "\n".join(b.text for b in ordered if b.text)


class OcrProvider:
    def recognize(self, image_path: Path) -> OcrResult:
        raise NotImplementedError


class MockOcrProvider(OcrProvider):
    """确定性 mock：返回一条以图片文件名标记的块，用于单测与本地演示。"""

    def recognize(self, image_path: Path) -> OcrResult:
        return OcrResult(
            status="success",
            blocks=[
                OcrTextBlock(
                    text=f"MOCK OCR {Path(image_path).name}",
                    confidence=0.99,
                    bbox=[0, 0, 100, 20],
                    order_index=0,
                )
            ],
            raw_json={"provider": "mock"},
        )


def get_ocr_provider() -> OcrProvider:
    """按配置返回 OCR provider。未知 provider 退化为 local 命令 provider。"""
    provider = (settings.lanhu_ocr_provider or "local").lower()
    if provider == "mock":
        return MockOcrProvider()
    # 延迟导入避免循环依赖
    from app.services.lanhu_evidence.local_ocr_provider import LocalCommandOcrProvider

    return LocalCommandOcrProvider()
