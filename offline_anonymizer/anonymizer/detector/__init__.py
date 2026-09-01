"""Rule-based sensitive information detectors."""

from offline_anonymizer.anonymizer.detector.base import Detection, Detector
from offline_anonymizer.anonymizer.detector.rules import (
    CompanyDetector,
    CustomKeywordDetector,
    CustomRegexDetector,
    DateDetector,
    EmailDetector,
    MoneyDetector,
    NameDetector,
    NumberDetector,
    PercentDetector,
    PhoneDetector,
    RuleDetector,
    default_detectors,
    custom_detectors,
)

__all__ = [
    "CompanyDetector",
    "CustomKeywordDetector",
    "CustomRegexDetector",
    "DateDetector",
    "Detection",
    "Detector",
    "EmailDetector",
    "MoneyDetector",
    "NameDetector",
    "NumberDetector",
    "PercentDetector",
    "PhoneDetector",
    "RuleDetector",
    "custom_detectors",
    "default_detectors",
]
