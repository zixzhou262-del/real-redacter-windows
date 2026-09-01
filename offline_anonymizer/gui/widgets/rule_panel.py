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
            checkbox.setChecked(bool(rules.get(key, True)))
            self.checkboxes[key] = checkbox
            grid.addWidget(checkbox, index // 2, index % 2)
        layout.addLayout(grid)
        custom_box = QCheckBox("自定义内容")
        custom_box.setChecked(bool(rules.get("custom", True)))
        self.checkboxes["custom"] = custom_box
        layout.addWidget(custom_box)

        layout.addWidget(QLabel("自定义脱敏内容（一行一个词）"))
        self.custom_keywords_edit = QPlainTextEdit()
        self.custom_keywords_edit.setPlaceholderText("例如：苹果\n内部项目代号")
        self.custom_keywords_edit.setPlainText(
            "\n".join(config.get("custom_keywords", []))
        )
        self.custom_keywords_edit.setFixedHeight(88)
        layout.addWidget(self.custom_keywords_edit)

    def rules(self) -> dict[str, bool]:
        return {key: checkbox.isChecked() for key, checkbox in self.checkboxes.items()}

    def custom_keywords(self) -> list[str]:
        return [
            line.strip()
            for line in self.custom_keywords_edit.toPlainText().splitlines()
            if line.strip()
        ]
