from __future__ import annotations

from dataclasses import dataclass


CONFIG_ERROR = "CONFIG_ERROR"
FILE_ERROR = "FILE_ERROR"
PARSE_ERROR = "PARSE_ERROR"
ANONYMIZE_ERROR = "ANONYMIZE_ERROR"
RECOVERY_ERROR = "RECOVERY_ERROR"
EXPORT_ERROR = "EXPORT_ERROR"
BATCH_ERROR = "BATCH_ERROR"


@dataclass
class ServiceError(Exception):
    code: str
    message: str
    detail: str | None = None

    def __str__(self) -> str:
        return self.message


def classify_exception(exc: Exception, operation: str) -> ServiceError:
    detail = str(exc)
    lowered = detail.lower()

    if operation == "config":
        return ServiceError(CONFIG_ERROR, "配置读取或保存失败，请检查配置文件。", detail)
    if "input file does not exist" in lowered or "input path is not a file" in lowered:
        return ServiceError(FILE_ERROR, "文件不存在，请检查路径是否正确。", detail)
    if operation == "recover":
        return ServiceError(RECOVERY_ERROR, "恢复失败，请检查HTML和映射文件是否匹配。", detail)
    if operation == "export":
        return ServiceError(EXPORT_ERROR, "导出失败，请检查输出格式和目录权限。", detail)
    if operation == "batch":
        return ServiceError(BATCH_ERROR, "批量处理失败，请检查输入目录和输出目录。", detail)
    if "docx" in lowered or "parse" in lowered or "package" in lowered:
        return ServiceError(PARSE_ERROR, "文档解析失败，请检查文件格式或文件是否损坏。", detail)
    return ServiceError(ANONYMIZE_ERROR, "文档处理失败，请检查文件内容和配置。", detail)
