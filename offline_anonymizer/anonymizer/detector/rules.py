from __future__ import annotations

import re
from typing import Pattern

from offline_anonymizer.anonymizer.detector.base import Detection, Detector


class RuleDetector(Detector):
    token_type: str = "custom"
    priority: int = 0
    patterns: tuple[Pattern[str], ...] = ()

    def detect(self, text: str) -> list[Detection]:
        detections: list[Detection] = []
        for pattern in self.patterns:
            for match in pattern.finditer(text):
                value = match.group(0)
                if not value:
                    continue
                detections.append(
                    Detection(
                        type=self.token_type,
                        start=match.start(),
                        end=match.end(),
                        value=value,
                        priority=self.priority,
                        detector=self.__class__.__name__,
                    )
                )
        return detections


class MoneyDetector(RuleDetector):
    token_type = "money"
    priority = 100
    patterns = (
        re.compile(
            r"(?<![A-Za-z0-9_.])(?:人民币|RMB|￥|¥)\s*"
            r"\d{1,3}(?:,\d{3})+(?:\.\d+)?\s*(?:万元|亿元|元|万|亿)?"
        ),
        re.compile(
            r"(?<![A-Za-z0-9_.])(?:人民币|RMB|￥|¥)\s*"
            r"\d+(?:\.\d+)?\s*(?:万元|亿元|元|万|亿)?"
        ),
        re.compile(
            r"(?<![A-Za-z0-9_.])\d{1,3}(?:,\d{3})+(?:\.\d+)?"
            r"\s*(?:万元|亿元|元|万|亿)(?:人民币)?"
        ),
        re.compile(
            r"(?<![A-Za-z0-9_.])\d+(?:\.\d+)?"
            r"\s*(?:万元|亿元|元|万|亿)(?:人民币)?"
        ),
    )


class PercentDetector(RuleDetector):
    token_type = "percent"
    priority = 95
    patterns = (
        re.compile(r"(?<![A-Za-z0-9_.])\d+(?:\.\d+)?\s*(?:%|％)"),
        re.compile(r"百分之[\u4e00-\u9fff\d.]+"),
    )


class DateDetector(RuleDetector):
    token_type = "date"
    priority = 90
    patterns = (
        re.compile(r"(?<![A-Za-z0-9_])\d{4}-\d{1,2}-\d{1,2}(?![A-Za-z0-9_])"),
        re.compile(r"\d{4}年\d{1,2}月(?:\d{1,2}日)?"),
    )


class PhoneDetector(RuleDetector):
    token_type = "phone"
    priority = 80
    patterns = (re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)"),)


class EmailDetector(RuleDetector):
    token_type = "email"
    priority = 70
    patterns = (
        re.compile(
            r"(?<![A-Za-z0-9._%+-])"
            r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"
            r"(?![A-Za-z0-9._%+-])"
        ),
    )


class CustomKeywordDetector(Detector):
    token_type = "custom"
    priority = 65

    def __init__(self, keywords: list[str] | tuple[str, ...]) -> None:
        self.keywords = _dedupe_keywords(keywords)

    def detect(self, text: str) -> list[Detection]:
        detections: list[Detection] = []
        for keyword in self.keywords:
            start = 0
            while True:
                index = text.find(keyword, start)
                if index < 0:
                    break
                detections.append(
                    Detection(
                        type=self.token_type,
                        start=index,
                        end=index + len(keyword),
                        value=keyword,
                        priority=self.priority,
                        detector=self.__class__.__name__,
                        metadata={"rule": "keyword"},
                    )
                )
                start = index + len(keyword)
        return detections


class CustomRegexDetector(Detector):
    token_type = "custom"
    priority = 65

    def __init__(self, patterns: list[str] | tuple[str, ...]) -> None:
        self.patterns = [re.compile(pattern) for pattern in patterns if pattern.strip()]

    def detect(self, text: str) -> list[Detection]:
        detections: list[Detection] = []
        for pattern in self.patterns:
            for match in pattern.finditer(text):
                value = match.group(0)
                if not value:
                    continue
                detections.append(
                    Detection(
                        type=self.token_type,
                        start=match.start(),
                        end=match.end(),
                        value=value,
                        priority=self.priority,
                        detector=self.__class__.__name__,
                        metadata={"rule": "regex", "pattern": pattern.pattern},
                    )
                )
        return detections


class CompanyDetector(Detector):
    token_type = "company"
    priority = 60
    _pattern = re.compile(
        r"[\u4e00-\u9fffA-Za-z0-9（）()·]{2,40}?"
        r"(?:股份有限公司|有限责任公司|有限公司|集团有限公司|集团|科技公司|公司|银行|事务所)"
    )
    _leading_noise = (
        "同时新增",
        "新增",
        "投资",
        "获得",
        "收入",
        "联系人",
        "客户",
        "于",
        "和",
        "与",
        "及",
    )

    def detect(self, text: str) -> list[Detection]:
        detections: list[Detection] = []
        for match in self._pattern.finditer(text):
            start = match.start()
            value = match.group(0)
            for prefix in self._leading_noise:
                if value.startswith(prefix) and len(value) > len(prefix) + 1:
                    start += len(prefix)
                    value = value[len(prefix) :]
                    break
            detections.append(
                Detection(
                    type=self.token_type,
                    start=start,
                    end=start + len(value),
                    value=value,
                    priority=self.priority,
                    detector=self.__class__.__name__,
                )
            )
        return detections


class NameDetector(Detector):
    token_type = "person"
    priority = 50
    _context_pattern = re.compile(
        r"(?:联系人|负责人|姓名|客户|借款人|法定代表人|经理)[:：]?\s*"
        r"([\u4e00-\u9fff]{2,4})"
    )
    _surname_pattern = re.compile(
        r"(?<![\u4e00-\u9fff])"
        r"([赵钱孙李周吴郑王冯陈褚卫蒋沈韩杨朱秦尤许何吕施张孔曹严华金魏陶姜谢邹喻柏水窦章云苏潘葛奚范彭郎鲁韦昌马苗凤花方俞任袁柳酆鲍史唐费廉岑薛雷贺倪汤滕殷罗毕郝邬安常乐于时傅皮卞齐康伍余元卜顾孟平黄和穆萧尹]{1}[\u4e00-\u9fff]{1,2})"
        r"(?![\u4e00-\u9fff])"
    )

    def detect(self, text: str) -> list[Detection]:
        detections: list[Detection] = []
        for match in self._context_pattern.finditer(text):
            value = match.group(1)
            start = match.start(1)
            detections.append(self._detection(start, start + len(value), value, "context"))
        for match in self._surname_pattern.finditer(text):
            value = match.group(1)
            detections.append(
                self._detection(match.start(1), match.end(1), value, "surname")
            )
        return detections

    def _detection(self, start: int, end: int, value: str, rule: str) -> Detection:
        return Detection(
            type=self.token_type,
            start=start,
            end=end,
            value=value,
            priority=self.priority,
            detector=self.__class__.__name__,
            metadata={"rule": rule},
        )


class NumberDetector(RuleDetector):
    token_type = "number"
    priority = 10
    patterns = (re.compile(r"(?<![A-Za-z0-9_.])\d+(?![A-Za-z0-9_.])"),)


def default_detectors() -> list[Detector]:
    return [
        MoneyDetector(),
        PercentDetector(),
        DateDetector(),
        PhoneDetector(),
        EmailDetector(),
        CompanyDetector(),
        NameDetector(),
        NumberDetector(),
    ]


def custom_detectors(
    keywords: list[str] | tuple[str, ...] | None = None,
    regex_patterns: list[str] | tuple[str, ...] | None = None,
) -> list[Detector]:
    detectors: list[Detector] = []
    if keywords:
        detectors.append(CustomKeywordDetector(list(keywords)))
    if regex_patterns:
        detectors.append(CustomRegexDetector(list(regex_patterns)))
    return detectors


def _dedupe_keywords(keywords: list[str] | tuple[str, ...]) -> list[str]:
    seen: set[str] = set()
    normalized: list[str] = []
    for keyword in keywords:
        item = keyword.strip()
        if not item or item in seen:
            continue
        seen.add(item)
        normalized.append(item)
    return sorted(normalized, key=len, reverse=True)
