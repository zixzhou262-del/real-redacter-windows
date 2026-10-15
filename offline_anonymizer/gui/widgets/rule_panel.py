from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox,
    QGridLayout,
    QLabel,
    QPlainTextEdit,
    QVBoxLayout,
    QWidget,
)

from offline_anonymizer.services import ConfigService


RULE_LABELS = {
    "money": "金额",
    "percent": "百分比",
    "number": "数字",
}

SUPPORTED_RULE_KEYS = (*RULE_LABELS.keys(), "custom")


class RulePanelWidget(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("panelContent")
        self.checkboxes: dict[str, QCheckBox] = {}
        config_result = ConfigService().load_config()
        config = config_result.data.get("config", {})
        rules = config.get("rules", {})

        layout = QVBoxLayout(self)
        title = QLabel("脱敏规则")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)
        grid = QGridLayout()
        for index, (key, label) in enumerate(RULE_LABELS.items()):
            checkbox = QCheckBox(label)
            # The bundled default config supplies the normal defaults. Missing
            # keys must remain disabled here so an old or partial Windows
            # config can never silently enable an extra detector.
            checkbox.setTristate(False)
            checkbox.setChecked(bool(rules.get(key, False)))
            self.checkboxes[key] = checkbox
            grid.addWidget(checkbox, index // 2, index % 2)
        layout.addLayout(grid)
        custom_box = QCheckBox("自定义内容")
        custom_box.setTristate(False)
        custom_box.setChecked(bool(rules.get("custom", False)))
        self.checkboxes["custom"] = custom_box
        layout.addWidget(custom_box)

        layout.addWidget(QLabel("自定义脱敏内容（一行一个词）"))
        self.custom_keywords_edit = QPlainTextEdit()
        self.custom_keywords_edit.setObjectName("customKeywordsEdit")
        self.custom_keywords_edit.setPlaceholderText("例如：苹果\n内部项目代号")
        self.custom_keywords_edit.setPlainText(
            "\n".join(config.get("custom_keywords", []))
        )
        self.custom_keywords_edit.setFixedHeight(88)
        layout.addWidget(self.custom_keywords_edit)

    def rules(self) -> dict[str, bool]:
        return {
            key: self.checkboxes[key].isChecked()
            for key in SUPPORTED_RULE_KEYS
        }

    def custom_keywords(self) -> list[str]:
        return [
            line.strip()
            for line in self.custom_keywords_edit.toPlainText().splitlines()
            if line.strip()
        ]
