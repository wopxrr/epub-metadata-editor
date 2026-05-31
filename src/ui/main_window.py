"""Main application window — Fitur 2: UI dasar PyQt6."""
import io
import json
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import Qt, QPoint
from PyQt6.QtGui import QPixmap, QPainter, QLinearGradient, QColor, QBrush
from PyQt6.QtWidgets import (
    QDialog,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QFormLayout,
    QLineEdit,
    QTextEdit,
    QLabel,
    QPushButton,
    QFileDialog,
    QMessageBox,
    QScrollArea,
    QFrame,
    QGraphicsDropShadowEffect,
    QApplication,
    QGroupBox,
    QSizePolicy,
    QSpacerItem,
    QToolBar,
    QComboBox,
    QListWidget,
    QListWidgetItem,
    QInputDialog,
)

import xml.etree.ElementTree as ET

import qtawesome as qta

from epub_handler import EpubHandler
from metadata import EpubMetadata
from ui.text_editor_dialog import TextEditorDialog


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("EPUB Metadata Editor")
        self.setMinimumSize(950, 680)
        self.resize(1050, 720)
        self.setAcceptDrops(True)

        self.handler = EpubHandler()
        self.current_path: Optional[str] = None
        self.changed = False

        self._build_ui()
        self._build_toolbar()
        self._build_menus()
        self._apply_stylesheet()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _create_placeholder_pixmap(self, size: int = 80) -> QPixmap:
        """Placeholder book icon when no cover is present."""
        return qta.icon("fa5s.book-open", color="#cbd5e1").pixmap(size, size)

    def _icon_pixmap(self, name: str, size: int = 14, color: str = "#4b5563") -> QPixmap:
        """Render a qtawesome icon as QPixmap."""
        return qta.icon(name, color=color).pixmap(size, size)

    # ------------------------------------------------------------------
    # UI construction — exact match to reference screenshot
    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        central = QWidget()
        central.setStyleSheet("""
            QWidget {
                background: qlineargradient(x1:0 y1:0, x2:1 y2:1,
                    stop:0 #e0f2fe, stop:0.5 #dbeafe, stop:1 #fce7f3);
            }
        """)
        self.setCentralWidget(central)
        
        # Main vertical layout for the whole screen
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(20, 15, 20, 20)
        main_layout.setSpacing(15)

        # Content area (Horizontal: Sidebar Left | Metadata Right)
        content = QHBoxLayout()
        content.setSpacing(25)

        # ==================== LEFT SIDEBAR (Cover + Actions) ====================
        sidebar_widget = QWidget()
        sidebar_widget.setObjectName("sidebarCard")
        sidebar_widget.setStyleSheet("""
            QWidget#sidebarCard {
                background: #ffffff;
                border-radius: 20px;
                border: 1px solid rgba(0,0,0,0.05);
            }
        """)
        # Soft shadow
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(30)
        shadow.setColor(QColor(0, 0, 0, 25))
        shadow.setOffset(0, 5)
        sidebar_widget.setGraphicsEffect(shadow)

        sidebar = QVBoxLayout(sidebar_widget)
        sidebar.setContentsMargins(12, 10, 12, 10)
        sidebar.setSpacing(6)
        sidebar.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Cover container (keeps cover + dimensions tightly together)
        cover_container = QWidget()
        cover_container.setStyleSheet("background: #ffffff;")
        cover_container.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        cover_layout = QVBoxLayout(cover_container)
        cover_layout.setContentsMargins(0, 0, 0, 0)
        cover_layout.setSpacing(2)

        self._cover_w = 160
        self._cover_h = 200
        self.cover_lbl = QLabel()
        self.cover_lbl.setFixedSize(self._cover_w, self._cover_h)
        self.cover_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._cover_empty_style = "border: 1px dashed #cbd5e1; border-radius: 12px; background: #f8fafc;"
        self._cover_image_style = "border-radius: 12px; background: transparent;"
        self.cover_lbl.setStyleSheet(self._cover_empty_style)
        self.cover_lbl.setPixmap(self._create_placeholder_pixmap(60))
        self.cover_lbl.setCursor(Qt.CursorShape.PointingHandCursor)
        self.cover_lbl.mousePressEvent = lambda ev: self._on_cover_clicked()
        cover_layout.addWidget(self.cover_lbl, alignment=Qt.AlignmentFlag.AlignCenter)

        # Store original cover bytes for preview & enhancement
        self._cover_bytes: Optional[bytes] = None
        self._cover_mimetype: str = ""

        # Cover dimensions
        self.cover_dim_lbl = QLabel("")
        self.cover_dim_lbl.setStyleSheet("color: #64748b; font-size: 11px; font-weight: 500;")
        self.cover_dim_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        cover_layout.addWidget(self.cover_dim_lbl)

        sidebar.addWidget(cover_container, alignment=Qt.AlignmentFlag.AlignCenter)

        # Change Cover
        btn_sidebar_style = (
            "QPushButton { background: white; color: #374151; border: 1px solid #e2e8f0; "
            "border-radius: 8px; padding: 6px; font-size: 12px; font-weight: 500; }"
            "QPushButton:hover { background: #f1f5f9; border-color: #94a3b8; }"
            "QPushButton:pressed { background: #e2e8f0; }"
            "QPushButton:disabled { background: #f1f5f9; color: #94a3b8; }"
        )
        self.change_cover_btn = QPushButton("Change Cover")
        self.change_cover_btn.setStyleSheet(btn_sidebar_style)
        self.change_cover_btn.clicked.connect(self._show_cover_options)
        sidebar.addWidget(self.change_cover_btn)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color: #e2e8f0;")
        sidebar.addWidget(sep)

        # Actions
        self.edit_toc_btn = QPushButton("  Edit TOC")
        self.edit_toc_btn.setIcon(qta.icon("fa5s.list", color="#374151"))
        self.edit_pagemap_btn = QPushButton("  Edit page-map")
        self.edit_pagemap_btn.setIcon(qta.icon("fa5s.map", color="#374151"))
        self.edit_opf_btn = QPushButton("  Edit OPF")
        self.edit_opf_btn.setIcon(qta.icon("fa5s.cube", color="#374151"))
        self.fix_issues_btn = QPushButton("  Fix Common Issues")
        self.fix_issues_btn.setIcon(qta.icon("fa5s.search", color="#374151"))

        for btn in (self.edit_toc_btn, self.edit_pagemap_btn, self.edit_opf_btn, self.fix_issues_btn):
            btn.setStyleSheet(btn_sidebar_style)
            btn.setEnabled(False)
            sidebar.addWidget(btn)

        self.fix_issues_btn.setToolTip("Check and fix common metadata problems")
        self.fix_issues_btn.clicked.connect(self._on_fix_issues)
        self.edit_toc_btn.clicked.connect(self._on_edit_toc)
        self.edit_pagemap_btn.clicked.connect(self._on_edit_pagemap)
        self.edit_opf_btn.clicked.connect(self._on_edit_opf)

        sidebar.addStretch()
        sidebar_widget.setFixedWidth(200)
        sidebar_widget.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Maximum)
        content.addWidget(sidebar_widget, alignment=Qt.AlignmentFlag.AlignTop)

        # ==================== RIGHT CONTENT (Metadata with Scroll) ====================
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent;")
        
        scroll_content = QWidget()
        scroll_content.setStyleSheet("background: transparent;")
        right_panel = QVBoxLayout(scroll_content)
        right_panel.setSpacing(15)
        right_panel.setContentsMargins(5, 5, 20, 5) # Extra right margin for scrollbar space

        input_style = (
            "QLineEdit, QComboBox, QTextEdit { background: rgba(255,255,255,0.92); "
            "border: 1px solid rgba(0,0,0,0.06); border-radius: 10px; padding: 6px 12px; "
            "font-size: 13px; color: #1f2937; }"
            "QLineEdit:focus, QComboBox:focus, QTextEdit:focus { border: 1px solid #60a5fa; background: white; }"
            "QComboBox::drop-down { subcontrol-origin: padding; subcontrol-position: top right; "
            "width: 24px; border: none; border-top-right-radius: 10px; border-bottom-right-radius: 10px; }"
            "QComboBox::down-arrow { image: none; border-left: 5px solid transparent; border-right: 5px solid transparent; "
            "border-top: 5px solid #64748b; width: 0; height: 0; }"
            "QComboBox::down-arrow:on { border-top: none; border-bottom: 5px solid #64748b; }"
        )
        label_style = "color: #4b5563; font-size: 12px; font-weight: 600; margin-left: 2px;"

        def make_labeled_widget(label_text, widget, icon_name=None):
            box = QVBoxLayout()
            box.setSpacing(6)
            if icon_name:
                header = QHBoxLayout()
                header.setSpacing(4)
                icon_lbl = QLabel()
                icon_lbl.setPixmap(self._icon_pixmap(icon_name, 13))
                icon_lbl.setStyleSheet("margin-left: 2px;")
                header.addWidget(icon_lbl)
                text_lbl = QLabel(label_text)
                text_lbl.setStyleSheet(label_style)
                header.addWidget(text_lbl)
                header.addStretch()
                box.addLayout(header)
            else:
                lbl = QLabel(label_text)
                lbl.setStyleSheet(label_style)
                box.addWidget(lbl)
            box.addWidget(widget)
            return box

        # Top Section: Title, Creators, Series
        top_fields = QVBoxLayout()
        top_fields.setSpacing(12)

        # Title & Title Sort
        title_row = QHBoxLayout()
        self.ed_title = QLineEdit()
        self.ed_title.setStyleSheet(input_style)
        self.ed_title.setMinimumHeight(34)
        title_row.addLayout(make_labeled_widget("BOOK TITLE", self.ed_title, "fa5s.book"), 3)

        self.ed_title_sort = QLineEdit()
        self.ed_title_sort.setStyleSheet(input_style)
        self.ed_title_sort.setMinimumHeight(34)
        title_row.addLayout(make_labeled_widget("TITLE SORT", self.ed_title_sort, "fa5s.font"), 2)
        top_fields.addLayout(title_row)

        # Creators & Author Sort
        creator_row = QHBoxLayout()
        self.ed_creators = QLineEdit()
        self.ed_creators.setStyleSheet(input_style)
        self.ed_creators.setMinimumHeight(34)
        creator_row.addLayout(make_labeled_widget("CREATORS / AUTHORS", self.ed_creators, "fa5s.user"), 3)

        self.ed_author_sort = QLineEdit()
        self.ed_author_sort.setStyleSheet(input_style)
        self.ed_author_sort.setMinimumHeight(34)
        creator_row.addLayout(make_labeled_widget("AUTHOR SORT", self.ed_author_sort, "fa5s.font"), 2)
        top_fields.addLayout(creator_row)

        # Series & Series Index
        series_row = QHBoxLayout()
        self.ed_series = QLineEdit()
        self.ed_series.setStyleSheet(input_style)
        self.ed_series.setMinimumHeight(34)
        series_row.addLayout(make_labeled_widget("SERIES", self.ed_series, "fa5s.layer-group"), 3)

        self.ed_series_index = QLineEdit()
        self.ed_series_index.setStyleSheet(input_style)
        self.ed_series_index.setMinimumHeight(34)
        series_row.addLayout(make_labeled_widget("SERIES INDEX", self.ed_series_index, "fa5s.hashtag"), 2)
        top_fields.addLayout(series_row)

        right_panel.addLayout(top_fields)

        # Middle: Description
        self.ed_description = QTextEdit()
        self.ed_description.setStyleSheet(input_style)
        self.ed_description.setMinimumHeight(120)
        self.ed_description.setPlaceholderText("Enter book description...")
        right_panel.addLayout(make_labeled_widget("DESCRIPTION", self.ed_description, "fa5s.align-left"))

        # Bottom Grid: All other info in 2 columns
        bottom_grid = QGridLayout()
        bottom_grid.setSpacing(15)
        bottom_grid.setContentsMargins(0, 5, 0, 0)
        bottom_grid.setColumnStretch(0, 1)
        bottom_grid.setColumnStretch(1, 1)

        self.ed_language = QComboBox()
        self.ed_language.setEditable(True)
        self.ed_language.setStyleSheet(input_style)
        self.ed_language.setMinimumHeight(34)
        self._lang_map = {
            "ab": "ab — Abkhaz (аҧсуа бызшәа)", "aa": "aa — Afar (Afaraf)", "af": "af — Afrikaans",
            "ak": "ak — Akan", "sq": "sq — Albanian (Shqip)", "am": "am — Amharic (አማርኛ)",
            "ar": "ar — Arabic (العربية)", "an": "an — Aragonese (Aragonés)", "hy": "hy — Armenian (Հայերեն)",
            "as": "as — Assamese (অসমীয়া)", "av": "av — Avaric (авар мацӀ)", "ae": "ae — Avestan",
            "ay": "ay — Aymara (Aymar aru)", "az": "az — Azerbaijani (Azərbaycan dili)",
            "bm": "bm — Bambara (Bamanankan)", "ba": "ba — Bashkir (башҡорт теле)",
            "eu": "eu — Basque (Euskara)", "be": "be — Belarusian (Беларуская)",
            "bn": "bn — Bengali (বাংলা)", "bh": "bh — Bihari", "bi": "bi — Bislama",
            "bs": "bs — Bosnian (Bosanski)", "br": "br — Breton (Brezhoneg)", "bg": "bg — Bulgarian (Български)",
            "my": "my — Burmese (ဗမာစာ)", "ca": "ca — Catalan (Català)", "ch": "ch — Chamorro",
            "ce": "ce — Chechen (нохчийн мотт)", "ny": "ny — Chichewa", "zh": "zh — Chinese (中文)",
            "cv": "cv — Chuvash (чӑваш чӗлхи)", "kw": "kw — Cornish (Kernewek)", "co": "co — Corsican (Corsu)",
            "cr": "cr — Cree", "hr": "hr — Croatian (Hrvatski)", "cs": "cs — Czech (Čeština)",
            "da": "da — Danish (Dansk)", "dv": "dv — Divehi (ދިވެހިބަސް)", "nl": "nl — Dutch (Nederlands)",
            "dz": "dz — Dzongkha (རྫོང་ཁ)", "en": "en — English", "eo": "eo — Esperanto",
            "et": "et — Estonian (Eesti)", "ee": "ee — Ewe (Eʋegbe)", "fo": "fo — Faroese (Føroyskt)",
            "fj": "fj — Fijian (Vosa Vakaviti)", "fi": "fi — Finnish (Suomi)", "fr": "fr — French (Français)",
            "ff": "ff — Fula (Fulfulde)", "gl": "gl — Galician (Galego)", "ka": "ka — Georgian (ქართული)",
            "de": "de — German (Deutsch)", "el": "el — Greek (Ελληνικά)", "gn": "gn — Guaraní (Avañe'ẽ)",
            "gu": "gu — Gujarati (ગુજરાતી)", "ht": "ht — Haitian (Kreyòl ayisyen)", "ha": "ha — Hausa (هَوُسَ)",
            "he": "he — Hebrew (עברית)", "hz": "hz — Herero", "hi": "hi — Hindi (हिन्दी)",
            "ho": "ho — Hiri Motu", "hu": "hu — Hungarian (Magyar)", "is": "is — Icelandic (Íslenska)",
            "io": "io — Ido", "ig": "ig — Igbo (Asụsụ Igbo)", "id": "id — Indonesian (Bahasa Indonesia)",
            "ia": "ia — Interlingua", "ie": "ie — Interlingue", "iu": "iu — Inuktitut",
            "ik": "ik — Inupiaq", "ga": "ga — Irish (Gaeilge)", "it": "it — Italian (Italiano)",
            "ja": "ja — Japanese (日本語)", "jv": "jv — Javanese (Basa Jawa)", "kl": "kl — Kalaallisut",
            "kn": "kn — Kannada (ಕನ್ನಡ)", "kr": "kr — Kanuri", "ks": "ks — Kashmiri (कश्मीरी / كشميري)",
            "kk": "kk — Kazakh (Қазақ тілі)", "km": "km — Khmer (ខ្មែរ)", "ki": "ki — Kikuyu", "rw": "rw — Kinyarwanda",
            "ky": "ky — Kyrgyz (Кыргызча)", "kv": "kv — Komi (коми кыв)", "kg": "kg — Kongo", "ko": "ko — Korean (한국어)",
            "ku": "ku — Kurdish (Kurdî / كوردی)", "kj": "kj — Kwanyama", "la": "la — Latin (Latine)",
            "lb": "lb — Luxembourgish (Lëtzebuergesch)", "lg": "lg — Luganda", "li": "li — Limburgish (Limburgs)",
            "ln": "ln — Lingala", "lo": "lo — Lao (ພາສາລາວ)", "lt": "lt — Lithuanian (Lietuvių)",
            "lu": "lu — Luba-Katanga", "lv": "lv — Latvian (Latviešu)", "gv": "gv — Manx (Gaelg)",
            "mk": "mk — Macedonian (Македонски)", "mg": "mg — Malagasy", "ms": "ms — Malay (Bahasa Melayu)",
            "ml": "ml — Malayalam (മലയാളം)", "mt": "mt — Maltese (Malti)", "mi": "mi — Māori", "mr": "mr — Marathi (मराठी)",
            "mh": "mh — Marshallese", "mn": "mn — Mongolian (Монгол хэл)", "na": "na — Nauru (Dorerin Naoero)",
            "nv": "nv — Navajo (Diné bizaad)", "nd": "nd — Northern Ndebele", "ne": "ne — Nepali (नेपाली)",
            "ng": "ng — Ndonga", "nb": "nb — Norwegian Bokmål (Norsk bokmål)", "nn": "nn — Norwegian Nynorsk (Norsk nynorsk)",
            "no": "no — Norwegian (Norsk)", "ii": "ii — Nuosu (ꆈꌠ꒿ / 四川彝语)", "nr": "nr — Southern Ndebele",
            "oc": "oc — Occitan (Occitan)", "oj": "oj — Ojibwe (ᐊᓂᔑᓈᐯᒧᐎᓐ)", "cu": "cu — Old Church Slavonic",
            "om": "om — Oromo (Afaan Oromoo)", "or": "or — Oriya (ଓଡ଼ିଆ)", "os": "os — Ossetian (Ирон æвзаг)",
            "pa": "pa — Panjabi (ਪੰਜਾਬੀ / پنجابی)", "pi": "pi — Pāli", "fa": "fa — Persian (فارسی)",
            "pl": "pl — Polish (Polski)", "ps": "ps — Pashto (پښتو)", "pt": "pt — Portuguese (Português)",
            "qu": "qu — Quechua (Runa Simi)", "rm": "rm — Romansh (Rumantsch)", "rn": "rn — Kirundi", "ro": "ro — Romanian (Română)",
            "ru": "ru — Russian (Русский)", "sa": "sa — Sanskrit (संस्कृतम्)", "sc": "sc — Sardinian (Sardu)",
            "sd": "sd — Sindhi (سنڌي)", "se": "se — Northern Sami (Davvisámegiella)", "sm": "sm — Samoan (Gagana fa'a Sāmoa)",
            "sg": "sg — Sango", "sr": "sr — Serbian (Српски)", "gd": "gd — Scottish Gaelic (Gàidhlig)",
            "sn": "sn — Shona (ChiShona)", "si": "si — Sinhala (සිංහල)", "sk": "sk — Slovak (Slovenčina)",
            "sl": "sl — Slovenian (Slovenščina)", "so": "so — Somali (Soomaali)", "st": "st — Southern Sotho (Sesotho)",
            "es": "es — Spanish (Español)", "su": "su — Sundanese (Basa Sunda)", "sw": "sw — Swahili (Kiswahili)",
            "ss": "ss — Swati", "sv": "sv — Swedish (Svenska)", "ta": "ta — Tamil (தமிழ்)", "te": "te — Telugu (తెలుగు)",
            "tg": "tg — Tajik (Тоҷикӣ)", "th": "th — Thai (ไทย)", "ti": "ti — Tigrinya (ትግርኛ)", "bo": "bo — Tibetan (བོད་སྐད་)",
            "tk": "tk — Turkmen (Türkmençe)", "tl": "tl — Tagalog (Wikang Tagalog)", "tn": "tn — Tswana", "to": "to — Tonga",
            "tr": "tr — Turkish (Türkçe)", "ts": "ts — Tsonga", "tt": "tt — Tatar (Татар теле)", "tw": "tw — Twi",
            "ty": "ty — Tahitian (Reo Tahiti)", "ug": "ug — Uyghur (ئۇيغۇرچە)", "uk": "uk — Ukrainian (Українська)",
            "ur": "ur — Urdu (اردو)", "uz": "uz — Uzbek (Oʻzbek)", "ve": "ve — Venda", "vi": "vi — Vietnamese (Tiếng Việt)",
            "vo": "vo — Volapük", "wa": "wa — Walloon (Walon)", "cy": "cy — Welsh (Cymraeg)", "wo": "wo — Wolof",
            "fy": "fy — Western Frisian (Frysk)", "xh": "xh — Xhosa (isiXhosa)", "yi": "yi — Yiddish (ייִדיש)",
            "yo": "yo — Yoruba (Yorùbá)", "za": "za — Zhuang (Vahcuengh / 壮语)", "zu": "zu — Zulu (isiZulu)",
        }
        self.ed_language.addItems(sorted(self._lang_map.values(), key=lambda x: x.lower()))
        self.ed_language.setCurrentIndex(-1)
        # Prevent accidental value change when scrolling over the combo inside a scroll area
        self.ed_language.installEventFilter(self)

        self.ed_publisher = QLineEdit()
        self.ed_date = QLineEdit()
        self.ed_subjects = QLineEdit()
        self.ed_subjects.setPlaceholderText("Fantasy; Magic; Classics")
        self.ed_version = QLineEdit()
        self.ed_version.setReadOnly(True)
        self.ed_rating = QLineEdit()
        self.ed_rating.setPlaceholderText("e.g. 8.0")
        self.ed_modification_date = QLineEdit()
        self.ed_modification_date.setPlaceholderText("YYYY-MM-DD or ISO 8601")

        # Identifier editor
        self.identifier_editor = self._build_identifier_editor()
        right_panel.addWidget(self.identifier_editor)

        fields = [
            ("LANGUAGE", self.ed_language, "fa5s.globe"),
            ("PUBLISHER", self.ed_publisher, "fa5s.building"),
            ("DATE", self.ed_date, "fa5s.calendar"),
            ("SUBJECTS", self.ed_subjects, "fa5s.tags"),
            ("EPUB VERSION", self.ed_version, "fa5s.info-circle"),
            ("RATING", self.ed_rating, "fa5s.star"),
            ("MODIFIED", self.ed_modification_date, "fa5s.clock"),
        ]

        for i, (lab, wid, ico) in enumerate(fields):
            if isinstance(wid, QLineEdit):
                wid.setStyleSheet(input_style)
                wid.setMinimumHeight(34)
            vbox = make_labeled_widget(lab, wid, ico)
            if i == len(fields) - 1 and len(fields) % 2 == 1:
                bottom_grid.addLayout(vbox, i // 2, 0, 1, 2)
            else:
                bottom_grid.addLayout(vbox, i // 2, i % 2)

        right_panel.addLayout(bottom_grid)
        
        scroll.setWidget(scroll_content)
        content.addWidget(scroll, 1)

        main_layout.addLayout(content)

        # Save sidebar ref for accent
        self.right_widget = sidebar_widget 

        self._set_fields_enabled(False)
        self._connect_change_signals()
        self.statusBar().showMessage("Ready")

    def _build_toolbar(self) -> None:
        toolbar = QToolBar("Main Toolbar")
        toolbar.setMovable(False)
        toolbar.setStyleSheet("""
            QToolBar {
                background: qlineargradient(x1:0 y1:0, x2:1 y2:0,
                    stop:0 #e0f2fe, stop:0.5 #dbeafe, stop:1 #fce7f3);
                border-bottom: 1px solid rgba(0,0,0,0.05);
                padding: 8px 16px;
                spacing: 12px;
            }
        """)
        self.addToolBar(toolbar)

        self.open_btn = QPushButton("  Open EPUB")
        self.open_btn.setIcon(qta.icon("fa5s.folder-open", color="white"))
        self.open_btn.setToolTip("Open an EPUB file (Ctrl+O)")
        self.open_btn.setStyleSheet(
            "QPushButton { background: #60a5fa; color: white; border: none; "
            "border-radius: 10px; padding: 8px 18px; font-size: 13px; font-weight: 500; }"
            "QPushButton:hover { background: #3b82f6; }"
        )
        self.open_btn.clicked.connect(self._on_open)
        toolbar.addWidget(self.open_btn)

        self.import_json_btn = QPushButton("  Import JSON")
        self.import_json_btn.setIcon(qta.icon("fa5s.file-import", color="white"))
        self.import_json_btn.setToolTip("Import metadata from a JSON file (AI result)")
        self.import_json_btn.setStyleSheet(
            "QPushButton { background: #8b5cf6; color: white; border: none; "
            "border-radius: 10px; padding: 8px 18px; font-size: 13px; font-weight: 500; }"
            "QPushButton:hover { background: #7c3aed; }"
        )
        self.import_json_btn.clicked.connect(self._on_import_json)
        toolbar.addWidget(self.import_json_btn)

        self.paste_json_btn = QPushButton("  Paste JSON")
        self.paste_json_btn.setIcon(qta.icon("fa5s.paste", color="white"))
        self.paste_json_btn.setToolTip("Paste metadata JSON text directly")
        self.paste_json_btn.setStyleSheet(
            "QPushButton { background: #a78bfa; color: white; border: none; "
            "border-radius: 10px; padding: 8px 18px; font-size: 13px; font-weight: 500; }"
            "QPushButton:hover { background: #8b5cf6; }"
        )
        self.paste_json_btn.clicked.connect(self._on_paste_json)
        toolbar.addWidget(self.paste_json_btn)

        self.file_bar = QLineEdit()
        self.file_bar.setPlaceholderText("No file loaded")
        self.file_bar.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.file_bar.setMinimumWidth(160)
        self.file_bar.setStyleSheet(
            "QLineEdit {"
            "  background: rgba(255,255,255,0.7);"
            "  border: 1px solid rgba(0,0,0,0.08);"
            "  border-radius: 10px;"
            "  padding: 6px 12px;"
            "  color: #374151;"
            "  font-size: 13px;"
            "}"
            "QLineEdit:focus {"
            "  border: 1px solid #60a5fa;"
            "  background: rgba(255,255,255,0.9);"
            "}"
        )
        self.file_bar.editingFinished.connect(self._on_rename_file)
        toolbar.addWidget(self.file_bar)

        spacer = QWidget()
        spacer.setFixedWidth(12)
        toolbar.addWidget(spacer)

        # View in Reader button
        self.preview_btn = QPushButton("  View in Reader")
        self.preview_btn.setIcon(qta.icon("fa5s.book-reader", color="#374151"))
        self.preview_btn.setStyleSheet(
            "QPushButton { background: white; color: #374151; border: 1px solid #e2e8f0; "
            "border-radius: 10px; padding: 8px 16px; font-size: 13px; font-weight: 500; }"
            "QPushButton:hover { background: #f8fafc; }"
        )
        self.preview_btn.setEnabled(False)
        self.preview_btn.setToolTip("Open EPUB in system default reader")
        self.preview_btn.clicked.connect(self._on_open_epub_externally)
        toolbar.addWidget(self.preview_btn)

        # Clean Metadata button
        self.clean_meta_btn = QPushButton("  Clean")
        self.clean_meta_btn.setIcon(qta.icon("fa5s.eraser", color="#374151"))
        self.clean_meta_btn.setStyleSheet(
            "QPushButton { background: white; color: #374151; border: 1px solid #e2e8f0; "
            "border-radius: 10px; padding: 8px 16px; font-size: 13px; font-weight: 500; }"
            "QPushButton:hover { background: #f8fafc; }"
        )
        self.clean_meta_btn.setEnabled(False)
        self.clean_meta_btn.setToolTip("Clear all metadata to start fresh")
        self.clean_meta_btn.clicked.connect(self._on_clean_metadata)
        toolbar.addWidget(self.clean_meta_btn)

        self.save_btn = QPushButton("  Save")
        self.save_btn.setIcon(qta.icon("fa5s.save", color="white"))
        self.save_btn.setToolTip("Save changes (Ctrl+S)")
        self.save_btn.setEnabled(False)
        self.save_btn.setStyleSheet(
            "QPushButton { background: #4ade80; color: white; border: none; "
            "border-radius: 10px; padding: 8px 18px; font-size: 13px; font-weight: 500; }"
            "QPushButton:hover { background: #22c55e; }"
            "QPushButton:disabled { background: #bbf7d0; color: #6b7280; }"
        )
        self.save_btn.clicked.connect(self._on_save)
        toolbar.addWidget(self.save_btn)

    def _build_menus(self) -> None:
        menubar = self.menuBar()
        file_menu = menubar.addMenu("&File")

        open_action = file_menu.addAction("&Open…")
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self._on_open)

        file_menu.addSeparator()

        save_action = file_menu.addAction("&Save")
        save_action.setShortcut("Ctrl+S")
        save_action.triggered.connect(self._on_save)

        file_menu.addSeparator()

        quit_action = file_menu.addAction("E&xit")
        quit_action.setShortcut("Ctrl+Q")
        quit_action.triggered.connect(self.close)

    def _apply_stylesheet(self) -> None:
        """Apply a modern gradient stylesheet to the entire application."""
        self.setStyleSheet("""
            QMainWindow {
                background: qlineargradient(x1:0 y1:0, x2:1 y2:1,
                    stop:0 #e0f2fe, stop:0.5 #dbeafe, stop:1 #fce7f3);
            }
            QMenuBar {
                background: transparent;
                color: #374151;
            }
            QMenuBar::item:selected {
                background: rgba(96, 165, 250, 0.15);
                border-radius: 6px;
            }
            QMenu {
                background-color: #ffffff;
                border: 1px solid #e2e8f0;
                border-radius: 10px;
                padding: 4px;
            }
            QMenu::item:selected {
                background-color: #60a5fa;
                color: white;
                border-radius: 6px;
            }
            QStatusBar {
                background: rgba(255,255,255,0.7);
                color: #475569;
                border-top: 1px solid rgba(0,0,0,0.04);
                font-size: 12px;
                padding: 2px 8px;
            }
            QScrollBar:vertical {
                background: transparent;
                width: 6px;
                margin: 0;
            }
            QScrollBar::handle:vertical {
                background: rgba(148,163,184,0.35);
                min-height: 30px;
                border-radius: 3px;
            }
            QScrollBar::handle:vertical:hover {
                background: rgba(100,116,139,0.55);
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: none;
            }
            QScrollBar:horizontal {
                background: transparent;
                height: 6px;
                margin: 0;
            }
            QScrollBar::handle:horizontal {
                background: rgba(148,163,184,0.35);
                min-width: 30px;
                border-radius: 3px;
            }
            QScrollBar::handle:horizontal:hover {
                background: rgba(100,116,139,0.55);
            }
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                width: 0px;
            }
            QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
                background: none;
            }
        """)

    def _make_line(self) -> QLineEdit:
        le = QLineEdit()
        return le

    def _connect_change_signals(self) -> None:
        """Connect every editable widget to _mark_changed."""
        for w in (
            self.ed_title,
            self.ed_title_sort,
            self.ed_creators,
            self.ed_author_sort,
            self.ed_series,
            self.ed_series_index,
            self.ed_publisher,
            self.ed_date,
            self.ed_subjects,
            self.ed_rating,
            self.ed_modification_date,
            self.ed_description,
        ):
            if isinstance(w, QLineEdit):
                w.textChanged.connect(self._mark_changed)
            elif isinstance(w, QTextEdit):
                w.textChanged.connect(self._mark_changed)
        self.ed_language.currentTextChanged.connect(self._mark_changed)

    def _build_identifier_editor(self) -> QWidget:
        """Build a widget for managing multiple identifiers with type selection."""
        container = QWidget()
        container.setObjectName("identifierEditor")
        layout = QVBoxLayout(container)
        layout.setSpacing(6)
        layout.setContentsMargins(0, 0, 0, 0)

        # Header with label and add button
        header_widget = QWidget()
        header_widget.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        header = QHBoxLayout(header_widget)
        header.setSpacing(8)
        header.setContentsMargins(0, 0, 0, 0)
        icon_lbl = QLabel()
        icon_lbl.setPixmap(self._icon_pixmap("fa5s.fingerprint", 13, "#212529"))
        header.addWidget(icon_lbl)
        lbl = QLabel("Identifiers")
        lbl.setStyleSheet("font-weight: 600; color: #212529; font-size: 13px;")
        header.addWidget(lbl)
        add_btn = QPushButton("+")
        add_btn.setFixedSize(24, 24)
        add_btn.setStyleSheet("""
            QPushButton {
                background-color: #4a90d9;
                color: white;
                border: none;
                border-radius: 12px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover { background-color: #3b7bc4; }
        """)
        add_btn.setToolTip("Add a new identifier")
        add_btn.clicked.connect(lambda: self._add_identifier_row())
        header.addWidget(add_btn)
        layout.addWidget(header_widget)

        # Rows container
        self._identifier_rows_layout = QVBoxLayout()
        self._identifier_rows_layout.setSpacing(4)
        layout.addLayout(self._identifier_rows_layout)
        layout.addStretch()

        return container

    def _add_identifier_row(self, id_type: str = "", value: str = "") -> None:
        """Add one identifier row with type combo + value lineedit + delete button."""
        row_widget = QWidget()
        row_layout = QHBoxLayout(row_widget)
        row_layout.setSpacing(6)
        row_layout.setContentsMargins(0, 0, 0, 0)

        type_combo = QComboBox()
        type_combo.addItems(["ISBN-10", "ISBN-13", "UUID", "ASIN", "DOI", "Other"])
        type_combo.setCurrentText(id_type if id_type else self._guess_identifier_type(value))
        type_combo.setFixedWidth(90)
        type_combo.setStyleSheet("""
            QComboBox {
                background-color: #ffffff;
                border: 1px solid #ced4da;
                border-radius: 6px;
                padding: 4px 6px;
                font-size: 12px;
                min-height: 20px;
            }
            QComboBox::drop-down { width: 20px; }
        """)
        row_layout.addWidget(type_combo)

        val_edit = QLineEdit(value)
        val_edit.setStyleSheet("""
            QLineEdit {
                background-color: #ffffff;
                border: 1px solid #ced4da;
                border-radius: 6px;
                padding: 4px 8px;
                font-size: 13px;
                min-height: 20px;
            }
            QLineEdit:focus { border: 1px solid #4a90d9; }
        """)
        val_edit.setPlaceholderText("Enter identifier value...")
        row_layout.addWidget(val_edit, 1)

        del_btn = QPushButton("×")
        del_btn.setFixedSize(24, 24)
        del_btn.setStyleSheet("""
            QPushButton {
                background-color: #f1f3f5;
                color: #868e96;
                border: 1px solid #dee2e6;
                border-radius: 12px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover { background-color: #ffe0e0; color: #e03131; border-color: #ffa8a8; }
        """)
        del_btn.setToolTip("Remove this identifier")
        del_btn.clicked.connect(lambda: self._remove_identifier_row(row_widget))
        row_layout.addWidget(del_btn)

        self._identifier_rows_layout.addWidget(row_widget)
        val_edit.textChanged.connect(self._mark_changed)

    def _remove_identifier_row(self, row_widget: QWidget) -> None:
        """Remove a single identifier row."""
        self._identifier_rows_layout.removeWidget(row_widget)
        row_widget.deleteLater()
        self._mark_changed()

    def _guess_identifier_type(self, value: str) -> str:
        """Auto-detect identifier type from its value."""
        v = value.strip().replace("-", "").upper()
        if not v:
            return "Other"
        # UUID pattern
        import re
        if re.match(r"^[0-9A-F]{8}-[0-9A-F]{4}-[0-9A-F]{4}-[0-9A-F]{4}-[0-9A-F]{12}$", value.strip(), re.I):
            return "UUID"
        # ISBN-13: starts with 978 or 979, 13 digits
        if len(v) == 13 and v.startswith(("978", "979")) and v.isdigit():
            return "ISBN-13"
        # ISBN-10: 10 digits, last can be X
        if len(v) == 10 and (v.isdigit() or (v[:9].isdigit() and v[9] == "X")):
            return "ISBN-10"
        # ASIN: Amazon, usually 10 alphanumeric
        if len(v) == 10 and v.isalnum():
            return "ASIN"
        # DOI: starts with 10.
        if value.strip().lower().startswith("10."):
            return "DOI"
        return "Other"

    def _clear_identifier_rows(self) -> None:
        """Remove all identifier rows."""
        while self._identifier_rows_layout.count():
            item = self._identifier_rows_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _populate_identifier_rows(self, identifiers: list[str]) -> None:
        """Populate identifier editor from a list of raw identifier strings."""
        self._clear_identifier_rows()
        for val in identifiers:
            if val.strip():
                self._add_identifier_row(value=val.strip())
        if not identifiers:
            self._add_identifier_row()

    def _collect_identifiers(self) -> list[str]:
        """Gather identifiers from the editor rows."""
        results = []
        for i in range(self._identifier_rows_layout.count()):
            item = self._identifier_rows_layout.itemAt(i)
            if item is None:
                continue
            row_widget = item.widget()
            if row_widget is None:
                continue
            # Find combo and lineedit inside the row
            combo = None
            edit = None
            for child in row_widget.findChildren(QComboBox):
                combo = child
                break
            for child in row_widget.findChildren(QLineEdit):
                edit = child
                break
            if edit is not None:
                val = edit.text().strip()
                if val:
                    results.append(val)
        return results

    def _set_identifier_editor_enabled(self, enabled: bool) -> None:
        """Enable or disable all identifier rows."""
        for i in range(self._identifier_rows_layout.count()):
            item = self._identifier_rows_layout.itemAt(i)
            if item is None:
                continue
            row_widget = item.widget()
            if row_widget is None:
                continue
            for child in row_widget.findChildren((QComboBox, QLineEdit, QPushButton)):
                child.setEnabled(enabled)

    def _set_fields_enabled(self, enabled: bool) -> None:
        self.ed_language.setEnabled(enabled)
        if hasattr(self, "import_json_btn"):
            self.import_json_btn.setEnabled(enabled)
        if hasattr(self, "paste_json_btn"):
            self.paste_json_btn.setEnabled(enabled)
        if hasattr(self, "clean_meta_btn"):
            self.clean_meta_btn.setEnabled(enabled)
        for w in (
            self.ed_title,
            self.ed_title_sort,
            self.ed_creators,
            self.ed_author_sort,
            self.ed_series,
            self.ed_series_index,
            self.ed_publisher,
            self.ed_date,
            self.ed_subjects,
            self.ed_version,
            self.ed_rating,
            self.ed_modification_date,
            self.ed_description,
        ):
            w.setEnabled(enabled)
        self._set_identifier_editor_enabled(enabled)

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------
    def _on_open(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Open EPUB", "", "EPUB files (*.epub);;All files (*)"
        )
        if path:
            self._load_epub(path)

    def _apply_json_data(self, data: dict) -> None:
        """Parse a JSON dict and populate the metadata form."""
        new_meta = self.handler.metadata.copy()

        if "title" in data: new_meta.title = str(data["title"])
        if "title_sort" in data: new_meta.title_sort = str(data["title_sort"])
        if "creators" in data:
            c = data["creators"]
            new_meta.creators = c if isinstance(c, list) else [str(c)]
        if "author_sort" in data: new_meta.author_sort = str(data["author_sort"])
        if "series" in data: new_meta.series = str(data["series"])
        if "series_index" in data: new_meta.series_index = str(data["series_index"])
        if "description" in data: new_meta.description = str(data["description"])
        if "language" in data: new_meta.language = str(data["language"])
        if "publisher" in data: new_meta.publisher = str(data["publisher"])
        if "date" in data: new_meta.date = str(data["date"])
        if "subjects" in data:
            s = data["subjects"]
            new_meta.subjects = s if isinstance(s, list) else [str(s)]

        if "identifiers" in data:
            ids = data["identifiers"]
            if isinstance(ids, dict):
                new_meta.identifiers = [str(v) for v in ids.values() if v]
            elif isinstance(ids, list):
                new_meta.identifiers = [str(v) for v in ids]

        if "rating" in data: new_meta.rating = str(data["rating"])
        if "modification_date" in data: new_meta.modification_date = str(data["modification_date"])

        self._populate_fields(new_meta)
        self._mark_changed()
        self.statusBar().showMessage("Metadata imported from JSON successfully! ✨")

    def _on_import_json(self) -> None:
        """Import metadata from a JSON file."""
        if not self.current_path:
            QMessageBox.warning(self, "No EPUB Open", "Please open an EPUB file first.")
            return

        path, _ = QFileDialog.getOpenFileName(
            self, "Import JSON Metadata", "", "JSON files (*.json);;All files (*)"
        )
        if not path:
            return

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self._apply_json_data(data)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to import JSON: {str(e)}")

    def _on_paste_json(self) -> None:
        """Open a dialog to paste JSON text directly."""
        if not self.current_path:
            QMessageBox.warning(self, "No EPUB Open", "Please open an EPUB file first.")
            return

        dlg = QDialog(self)
        dlg.setWindowTitle("Paste JSON Metadata")
        dlg.setMinimumSize(500, 400)
        layout = QVBoxLayout(dlg)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)

        info = QLabel("Paste the JSON metadata from AI below, then click Import.")
        info.setStyleSheet("color: #4b5563; font-size: 13px;")
        layout.addWidget(info)

        text_edit = QTextEdit()
        text_edit.setPlaceholderText('{\n  "title": "...",\n  "creators": [...],\n  ...\n}')
        text_edit.setStyleSheet(
            "QTextEdit { background: white; border: 1px solid #ced4da; "
            "border-radius: 8px; padding: 8px; font-family: monospace; font-size: 13px; }"
        )
        layout.addWidget(text_edit)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        import_btn = QPushButton("Import")
        import_btn.setStyleSheet(
            "QPushButton { background: #8b5cf6; color: white; border: none; "
            "border-radius: 8px; padding: 8px 20px; font-weight: 500; }"
            "QPushButton:hover { background: #7c3aed; }"
        )
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setStyleSheet(
            "QPushButton { background: #f1f3f5; color: #495057; border: 1px solid #dee2e6; "
            "border-radius: 8px; padding: 8px 20px; font-weight: 500; }"
            "QPushButton:hover { background: #e9ecef; }"
        )
        btn_row.addWidget(cancel_btn)
        btn_row.addWidget(import_btn)
        layout.addLayout(btn_row)

        cancel_btn.clicked.connect(dlg.reject)

        def do_import():
            raw = text_edit.toPlainText().strip()
            if not raw:
                QMessageBox.warning(dlg, "Empty", "Please paste JSON text first.")
                return
            try:
                data = json.loads(raw)
                self._apply_json_data(data)
                dlg.accept()
            except json.JSONDecodeError as e:
                QMessageBox.critical(dlg, "Invalid JSON", f"Failed to parse JSON:\n{str(e)}")
            except Exception as e:
                QMessageBox.critical(dlg, "Error", f"Failed to import JSON:\n{str(e)}")

        import_btn.clicked.connect(do_import)
        dlg.exec()

    def _on_clean_metadata(self) -> None:
        """Clear all metadata fields to start fresh."""
        if not self.current_path:
            QMessageBox.warning(self, "No EPUB Open", "Please open an EPUB file first.")
            return

        reply = QMessageBox.question(
            self,
            "Clean Metadata",
            "This will clear ALL metadata fields (Title, Authors, Description, etc.)\n"
            "so you can fill them in from scratch.\n\n"
            "Are you sure?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        # Reset metadata model to empty defaults
        self.handler.metadata = EpubMetadata()
        self._populate_fields(self.handler.metadata)
        self._mark_changed()
        self.statusBar().showMessage("Metadata cleared — fill in fresh data and Save 🧹")

    def _load_epub(self, path: str) -> None:
        if self.changed:
            reply = QMessageBox.question(
                self,
                "Unsaved changes",
                "You have unsaved changes. Save before opening a new file?",
                QMessageBox.StandardButton.Yes
                | QMessageBox.StandardButton.No
                | QMessageBox.StandardButton.Cancel,
            )
            if reply == QMessageBox.StandardButton.Yes:
                self._on_save()
            elif reply == QMessageBox.StandardButton.Cancel:
                return

        try:
            self.handler.open_epub(path)
            self.current_path = path
        except Exception as exc:
            QMessageBox.critical(
                self,
                "Error opening EPUB",
                f"Failed to open:\n{path}\n\n{exc}",
            )
            self.statusBar().showMessage("Error opening file")
            return

        meta = self.handler.get_metadata()
        self._populate_fields(meta)
        self._load_cover_image()

        self.file_bar.setText(Path(path).name)
        self._set_fields_enabled(True)
        self.change_cover_btn.setEnabled(True)
        self.edit_toc_btn.setEnabled(self.handler.toc_path is not None)
        self.edit_pagemap_btn.setEnabled(self.handler.page_map_path is not None)
        self.edit_opf_btn.setEnabled(self.handler.opf_path_in_zip is not None)
        self.fix_issues_btn.setEnabled(True)
        self.preview_btn.setEnabled(True)
        self._reset_changed()
        self.statusBar().showMessage(
            f"EPUB {meta.version or '?'}  |  {Path(path).name}"
        )

    def _on_rename_file(self) -> None:
        """Rename the EPUB file on disk when user edits the filename bar."""
        if self.current_path is None:
            return
        new_name = self.file_bar.text().strip()
        if not new_name or new_name == Path(self.current_path).name:
            self.file_bar.setText(Path(self.current_path).name)
            return
        if not new_name.lower().endswith(".epub"):
            QMessageBox.warning(self, "Rename", "File name must end with .epub")
            self.file_bar.setText(Path(self.current_path).name)
            return
        parent = Path(self.current_path).parent
        new_p = parent / new_name
        if not parent.exists():
            QMessageBox.warning(self, "Rename", f"Directory does not exist:\n{parent}")
            self.file_bar.setText(Path(self.current_path).name)
            return
        if new_p.exists() and str(new_p) != self.current_path:
            reply = QMessageBox.question(
                self, "Rename", f"File already exists:\n{new_p.name}\n\nOverwrite?"
            )
            if reply != QMessageBox.StandardButton.Yes:
                self.file_bar.setText(Path(self.current_path).name)
                return
        # Prompt if unsaved changes
        if self.changed:
            reply = QMessageBox.question(
                self,
                "Unsaved changes",
                "You have unsaved changes. Save before renaming?",
                QMessageBox.StandardButton.Yes
                | QMessageBox.StandardButton.No
                | QMessageBox.StandardButton.Cancel,
            )
            if reply == QMessageBox.StandardButton.Yes:
                self._on_save()
            elif reply == QMessageBox.StandardButton.Cancel:
                self.file_bar.setText(Path(self.current_path).name)
                return
        try:
            self.handler.close()
            import os
            new_path = str(new_p)
            os.replace(self.current_path, new_path)
            self.handler.open_epub(new_path)
            self.current_path = new_path
            meta = self.handler.get_metadata()
            self._populate_fields(meta)
            self._load_cover_image()
            self.file_bar.setText(Path(new_path).name)
            self._reset_changed()
            self.statusBar().showMessage(f"Renamed to {Path(new_path).name}", 3000)
        except Exception as exc:
            QMessageBox.critical(self, "Rename failed", f"Could not rename file:\n{exc}")
            self.file_bar.setText(Path(self.current_path).name)
            try:
                self.handler.open_epub(self.current_path)
                self._load_cover_image()
            except Exception:
                pass

    def _populate_fields(self, meta: EpubMetadata) -> None:
        self.ed_title.setText(meta.title)
        self.ed_title_sort.setText(meta.title_sort)
        self.ed_creators.setText("; ".join(meta.creators))
        self.ed_author_sort.setText(meta.author_sort)
        self.ed_series.setText(meta.series)
        self.ed_series_index.setText(meta.series_index)
        # Language: show full label if known, else raw code
        lang_disp = self._lang_map.get(meta.language, meta.language)
        self.ed_language.setCurrentText(lang_disp)
        self._populate_identifier_rows(meta.identifiers)
        self.ed_publisher.setText(meta.publisher)
        self.ed_date.setText(meta.date)
        self.ed_subjects.setText("; ".join(meta.subjects))
        self.ed_version.setText(meta.version)
        self.ed_rating.setText(meta.rating)
        self.ed_modification_date.setText(meta.modification_date)
        self.ed_description.setPlainText(meta.description)

    def _load_cover_image(self) -> None:
        """Fetch cover bytes from handler and display in the cover label."""
        img_bytes, mimetype = self.handler.get_cover_image_bytes()
        self._cover_bytes = img_bytes
        self._cover_mimetype = mimetype or ""
        if img_bytes is None:
            self.cover_lbl.setText("")
            self.cover_lbl.setPixmap(self._create_placeholder_pixmap(56))
            self.cover_lbl.setStyleSheet(self._cover_empty_style)
            self.cover_dim_lbl.setText("")
            return

        pixmap = QPixmap()
        ok = pixmap.loadFromData(img_bytes)
        if ok and not pixmap.isNull():
            # Scale to fit the fixed label size while keeping aspect ratio
            scaled = pixmap.scaled(
                self._cover_w,
                self._cover_h,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self.cover_lbl.setPixmap(scaled)
            self.cover_lbl.setStyleSheet(self._cover_image_style)
            self.cover_lbl.setText("")
            self.cover_dim_lbl.setText(f"{pixmap.width()} x {pixmap.height()}")
            accent = self._extract_dominant_color(pixmap)
            self._apply_cover_accent(accent)
        else:
            self.cover_lbl.setText("")
            self.cover_lbl.setPixmap(self._create_placeholder_pixmap(56))
            self.cover_lbl.setStyleSheet(self._cover_empty_style)
            self.cover_dim_lbl.setText("")
            self._apply_cover_accent(QColor("#60a5fa"))

    def _on_cover_clicked(self) -> None:
        """Show a popup with the cover at native resolution."""
        if self._cover_bytes is None:
            return
        self._show_cover_preview(self._cover_bytes)

    def _show_cover_preview(self, image_bytes: bytes) -> None:
        """Display a dialog with the cover at native or scaled-down size."""
        pixmap = QPixmap()
        if not pixmap.loadFromData(image_bytes) or pixmap.isNull():
            return

        dlg = QDialog(self)
        dlg.setWindowTitle("Cover Preview")
        dlg.setStyleSheet("background: #1e293b;")
        layout = QVBoxLayout(dlg)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        # Scale down if too large for screen, but keep crisp
        screen = QApplication.primaryScreen().availableGeometry()
        max_w = int(screen.width() * 0.7)
        max_h = int(screen.height() * 0.7)
        if pixmap.width() > max_w or pixmap.height() > max_h:
            pixmap = pixmap.scaled(max_w, max_h, Qt.AspectRatioMode.KeepAspectRatio,
                                   Qt.TransformationMode.SmoothTransformation)

        img_lbl = QLabel()
        img_lbl.setPixmap(pixmap)
        img_lbl.setStyleSheet("border-radius: 8px; background: transparent;")
        layout.addWidget(img_lbl, alignment=Qt.AlignmentFlag.AlignCenter)

        info = QLabel(f"{pixmap.width()} x {pixmap.height()} px")
        info.setStyleSheet("color: #94a3b8; font-size: 12px;")
        info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(info)

        close_btn = QPushButton("Close")
        close_btn.setStyleSheet(
            "QPushButton { background: #334155; color: #e2e8f0; border: none; "
            "border-radius: 8px; padding: 8px 24px; font-size: 13px; }"
            "QPushButton:hover { background: #475569; }"
        )
        close_btn.clicked.connect(dlg.accept)
        layout.addWidget(close_btn, alignment=Qt.AlignmentFlag.AlignCenter)

        dlg.exec()

    def _extract_dominant_color(self, pixmap: QPixmap) -> QColor:
        """Extract a soft pastel dominant color from the cover image."""
        image = pixmap.toImage()
        if image.isNull():
            return QColor("#60a5fa")
        w, h = image.width(), image.height()
        samples = [
            image.pixel(w // 2, h // 2),
            image.pixel(w // 4, h // 4),
            image.pixel(3 * w // 4, h // 4),
            image.pixel(w // 4, 3 * h // 4),
            image.pixel(3 * w // 4, 3 * h // 4),
        ]
        total_r = total_g = total_b = 0
        for px in samples:
            c = QColor(px)
            total_r += c.red()
            total_g += c.green()
            total_b += c.blue()
        n = len(samples)
        r = (total_r // n + 255) // 2
        g = (total_g // n + 255) // 2
        b = (total_b // n + 255) // 2
        return QColor(r, g, b)

    def _apply_cover_accent(self, color: QColor) -> None:
        """Apply extracted cover color to sidebar border accent and field focus."""
        c = color.name()
        # Update sidebar
        self.right_widget.setStyleSheet(f"""
            QWidget#sidebarCard {{
                background: rgba(255,255,255,0.95);
                border-radius: 20px;
                border: 2px solid {c};
            }}
        """)
        # Update fields focus color
        input_style_with_accent = (
            "QLineEdit, QComboBox, QTextEdit { background: rgba(255,255,255,0.92); "
            "border: 1px solid rgba(0,0,0,0.06); border-radius: 10px; padding: 6px 12px; "
            "font-size: 13px; color: #1f2937; }"
            f"QLineEdit:focus, QComboBox:focus, QTextEdit:focus {{ border: 2px solid {c}; background: white; }}"
        )
        for w in (self.ed_title, self.ed_title_sort, self.ed_creators, self.ed_author_sort,
                 self.ed_series, self.ed_series_index,
                 self.ed_description, self.ed_language,
                 self.ed_publisher, self.ed_date, self.ed_subjects):
            w.setStyleSheet(input_style_with_accent)

    def _on_fix_issues(self) -> None:
        """Scan metadata for common issues and offer fixes."""
        issues = []
        meta = self._collect_metadata_from_ui()
        
        if not meta.title.strip():
            issues.append(("Missing Title", "The book has no title set."))
        if not meta.creators:
            issues.append(("Missing Author", "No authors or creators are listed."))
        if not meta.language.strip() or meta.language == "unknown":
            issues.append(("Invalid Language", "Language code is missing or set to 'unknown'."))
        
        if not issues:
            QMessageBox.information(self, "Fix Issues", "No common issues found! Your metadata looks good.")
            return
            
        msg = "The following issues were found:\n\n"
        for title, desc in issues:
            msg += f"• {title}: {desc}\n"
        msg += "\nWould you like to auto-fix minor issues (e.g. set language to 'en' if missing)?"
        
        reply = QMessageBox.question(self, "Fix Issues", msg, QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            # Simple auto-fixes
            if not meta.language.strip() or meta.language == "unknown":
                # Default to English as it's the most common fallback
                self.ed_language.setEditText("en")
            
            self.statusBar().showMessage("Minor issues fixed. Please review and save.", 5000)

    def _on_open_epub_externally(self) -> None:
        """Open the current EPUB file in the system's default reader application."""
        if self.current_path is None:
            return
        import os
        import platform
        system = platform.system()
        try:
            if system == "Windows":
                os.startfile(self.current_path)
            elif system == "Darwin":
                import subprocess
                subprocess.run(["open", self.current_path], check=True)
            else:
                import subprocess
                subprocess.run(["xdg-open", self.current_path], check=True)
            self.statusBar().showMessage(f"Opened {Path(self.current_path).name}", 3000)
        except Exception as exc:
            QMessageBox.critical(self, "Error", f"Could not open EPUB:\n{exc}")

    def _show_cover_options(self) -> None:
        """Show a dialog with cover options: upload, URL, or remove."""
        if not self.current_path:
            QMessageBox.warning(self, "No EPUB Open", "Please open an EPUB file first.")
            return

        dlg = QDialog(self)
        dlg.setWindowTitle("Change Cover")
        dlg.setFixedWidth(320)
        layout = QVBoxLayout(dlg)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)

        info = QLabel("Choose how to change the cover image:")
        info.setStyleSheet("color: #4b5563; font-size: 13px;")
        layout.addWidget(info)

        btn_style = (
            "QPushButton { background: white; color: #374151; border: 1px solid #e2e8f0; "
            "border-radius: 10px; padding: 10px; font-size: 13px; font-weight: 500; }"
            "QPushButton:hover { background: #f8fafc; border-color: #cbd5e1; }"
        )
        danger_style = (
            "QPushButton { background: #fff1f2; color: #be123c; border: 1px solid #fecdd3; "
            "border-radius: 10px; padding: 10px; font-size: 13px; font-weight: 500; }"
            "QPushButton:hover { background: #ffe4e6; border-color: #fda4af; }"
        )

        upload_btn = QPushButton("  Upload from File")
        upload_btn.setIcon(qta.icon("fa5s.upload", color="#374151"))
        upload_btn.setStyleSheet(btn_style)
        upload_btn.clicked.connect(lambda: (dlg.accept(), self._on_upload_cover()))
        layout.addWidget(upload_btn)

        url_btn = QPushButton("  Download from URL")
        url_btn.setIcon(qta.icon("fa5s.link", color="#374151"))
        url_btn.setStyleSheet(btn_style)
        url_btn.clicked.connect(lambda: (dlg.accept(), self._on_download_cover()))
        layout.addWidget(url_btn)

        # Only show enhance if we have a current cover
        if self._cover_bytes is not None:
            enhance_btn = QPushButton("  Enhance Quality")
            enhance_btn.setIcon(qta.icon("fa5s.magic", color="#0f766e"))
            enhance_style = (
                "QPushButton { background: #f0fdfa; color: #0f766e; border: 1px solid #ccfbf1; "
                "border-radius: 10px; padding: 10px; font-size: 13px; font-weight: 500; }"
                "QPushButton:hover { background: #ccfbf1; border-color: #99f6e4; }"
            )
            enhance_btn.setStyleSheet(enhance_style)
            enhance_btn.setToolTip("Upscale and sharpen the current cover")
            enhance_btn.clicked.connect(lambda: (dlg.accept(), self._on_enhance_cover()))
            layout.addWidget(enhance_btn)

        remove_btn = QPushButton("  Remove Cover")
        remove_btn.setIcon(qta.icon("fa5s.trash", color="#be123c"))
        remove_btn.setStyleSheet(danger_style)
        remove_btn.clicked.connect(lambda: (dlg.accept(), self._on_remove_cover()))
        layout.addWidget(remove_btn)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setStyleSheet(
            "QPushButton { background: transparent; color: #64748b; border: none; font-size: 12px; }"
        )
        cancel_btn.clicked.connect(dlg.reject)
        layout.addWidget(cancel_btn, alignment=Qt.AlignmentFlag.AlignCenter)

        dlg.exec()

    def _on_upload_cover(self) -> None:
        """Let the user pick a new image file and replace the cover inside the EPUB."""
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select new cover image",
            "",
            "Images (*.png *.jpg *.jpeg *.webp *.gif *.bmp)",
        )
        if not path:
            return

        try:
            with open(path, "rb") as f:
                image_bytes = f.read()
        except Exception as exc:
            QMessageBox.critical(self, "Error", f"Could not read image:\n{exc}")
            return

        ext = Path(path).suffix.lower()
        mimetype_map = {
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".webp": "image/webp",
            ".gif": "image/gif",
            ".bmp": "image/bmp",
        }
        mimetype = mimetype_map.get(ext, "image/jpeg")
        filename = f"cover{ext}"

        # Auto-enhance if cover is too small
        enhanced_bytes = self._maybe_auto_enhance(image_bytes)
        if enhanced_bytes is not None:
            image_bytes = enhanced_bytes
            if ext == ".png":
                filename = "cover.jpg"
                mimetype = "image/jpeg"

        try:
            self.handler.set_cover_image(image_bytes, filename, mimetype)
        except Exception as exc:
            QMessageBox.critical(self, "Error", f"Failed to update cover:\n{exc}")
            return

        self._load_cover_image()
        self._mark_changed()
        self.statusBar().showMessage("Cover updated — Save to persist", 3000)

    def _on_download_cover(self) -> None:
        """Download a cover image from a URL and apply it."""
        url, ok = QInputDialog.getText(self, "Download Cover", "Enter image URL:")
        if not ok or not url.strip():
            return

        url = url.strip()
        self.statusBar().showMessage("Downloading cover image...")

        try:
            import urllib.request
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=20) as response:
                image_bytes = response.read()
                content_type = response.headers.get("Content-Type", "")
        except Exception as exc:
            QMessageBox.critical(self, "Download Error", f"Failed to download image:\n{exc}")
            self.statusBar().showMessage("Cover download failed")
            return

        # Guess extension from content-type or URL
        mimetype = "image/jpeg"
        ext = ".jpg"
        if "png" in content_type or url.lower().endswith(".png"):
            mimetype = "image/png"
            ext = ".png"
        elif "webp" in content_type or url.lower().endswith(".webp"):
            mimetype = "image/webp"
            ext = ".webp"
        elif "gif" in content_type or url.lower().endswith(".gif"):
            mimetype = "image/gif"
            ext = ".gif"
        elif "jpeg" in content_type or url.lower().endswith((".jpg", ".jpeg")):
            mimetype = "image/jpeg"
            ext = ".jpg"

        filename = f"cover{ext}"

        # Auto-enhance if cover is too small
        enhanced_bytes = self._maybe_auto_enhance(image_bytes)
        if enhanced_bytes is not None:
            image_bytes = enhanced_bytes
            if mimetype == "image/png":
                filename = "cover.jpg"
                mimetype = "image/jpeg"

        try:
            self.handler.set_cover_image(image_bytes, filename, mimetype)
        except Exception as exc:
            QMessageBox.critical(self, "Error", f"Failed to update cover:\n{exc}")
            return

        self._load_cover_image()
        self._mark_changed()
        self.statusBar().showMessage("Cover downloaded and updated — Save to persist", 3000)

    def _maybe_auto_enhance(self, image_bytes: bytes) -> Optional[bytes]:
        """Auto-upscale small covers (< 400 px width) using Pillow."""
        try:
            from PIL import Image, ImageFilter
            img = Image.open(io.BytesIO(image_bytes))
            w, h = img.size
            if w >= 400:
                return None  # Already large enough
            # Upscale 2x
            new_w, new_h = w * 2, h * 2
            img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
            # Mild sharpen
            img = img.filter(ImageFilter.UnsharpMask(radius=2, percent=150, threshold=3))
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=95)
            return buf.getvalue()
        except Exception:
            return None

    def _enhance_image_bytes(self, image_bytes: bytes) -> Optional[bytes]:
        """Upscale and sharpen an image using Pillow."""
        try:
            from PIL import Image, ImageFilter
            img = Image.open(io.BytesIO(image_bytes))
            w, h = img.size
            # Upscale 2x (or at least to 600px min width)
            target_w = max(w * 2, 600)
            ratio = target_w / w
            new_w, new_h = int(target_w), int(h * ratio)
            img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
            # Sharpen
            img = img.filter(ImageFilter.UnsharpMask(radius=2, percent=150, threshold=3))
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=95)
            return buf.getvalue()
        except Exception:
            return None

    def _on_enhance_cover(self) -> None:
        """Enhance the current cover image (upscale + sharpen)."""
        if self._cover_bytes is None:
            QMessageBox.warning(self, "No Cover", "There is no cover image to enhance.")
            return

        self.statusBar().showMessage("Enhancing cover quality...")
        enhanced = self._enhance_image_bytes(self._cover_bytes)
        if enhanced is None:
            QMessageBox.critical(self, "Error", "Failed to enhance the cover image.")
            self.statusBar().showMessage("Enhancement failed")
            return

        try:
            self.handler.set_cover_image(enhanced, "cover.jpg", "image/jpeg")
        except Exception as exc:
            QMessageBox.critical(self, "Error", f"Failed to update cover:\n{exc}")
            return

        self._load_cover_image()
        self._mark_changed()
        self.statusBar().showMessage("Cover enhanced — Save to persist", 3000)

    def _on_remove_cover(self) -> None:
        """Remove the cover image from the EPUB."""
        reply = QMessageBox.question(
            self,
            "Remove Cover",
            "Are you sure you want to remove the cover image from this EPUB?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        try:
            self.handler.remove_cover_image()
        except Exception as exc:
            QMessageBox.critical(self, "Error", f"Failed to remove cover:\n{exc}")
            return

        # Clear the UI cover display
        self.cover_lbl.setPixmap(self._create_placeholder_pixmap(60))
        self.cover_lbl.setStyleSheet(self._cover_empty_style)
        self.cover_dim_lbl.setText("")
        self._cover_bytes = None
        self._cover_mimetype = ""
        self._mark_changed()
        self.statusBar().showMessage("Cover removed — Save to persist", 3000)

    def _on_edit_toc(self) -> None:
        """Open a text editor for the TOC file (toc.ncx or nav.xhtml)."""
        if self.handler.toc_path is None:
            return
        self._edit_aux_file(self.handler.toc_path, "Edit TOC")

    def _on_edit_pagemap(self) -> None:
        """Open a text editor for page-map.xml."""
        if self.handler.page_map_path is None:
            return
        self._edit_aux_file(self.handler.page_map_path, "Edit page-map")

    def _on_edit_opf(self) -> None:
        """Open a text editor for the OPF package file."""
        if self.handler.opf_path_in_zip is None:
            return
        self._edit_aux_file(self.handler.opf_path_in_zip, "Edit OPF")

    def _edit_aux_file(self, path_in_zip: str, title: str) -> None:
        """Generic helper: read aux file, show editor, save if accepted."""
        try:
            text = self.handler.get_aux_file_text(path_in_zip)
        except Exception as exc:
            QMessageBox.critical(self, "Error", f"Could not read file:\n{exc}")
            return

        dlg = TextEditorDialog(title=title, parent=self)
        dlg.set_content(text, path_in_zip)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            new_text = dlg.get_content()
            try:
                self.handler.save_aux_file(path_in_zip, new_text)
                self._mark_changed()
                self.statusBar().showMessage(f"Saved {path_in_zip}", 3000)
            except Exception as exc:
                QMessageBox.critical(
                    self, "Error", f"Failed to save {path_in_zip}:\n{exc}"
                )

    # ------------------------------------------------------------------
    # Change tracking
    # ------------------------------------------------------------------
    def _mark_changed(self) -> None:
        if not self.changed:
            self.changed = True
            self.save_btn.setEnabled(True)
            self.setWindowTitle("* EPUB Metadata Editor")

    def _reset_changed(self) -> None:
        self.changed = False
        self.save_btn.setEnabled(False)
        self.setWindowTitle("EPUB Metadata Editor")

    # ------------------------------------------------------------------
    # Save
    # ------------------------------------------------------------------
    def _on_save(self) -> None:
        if self.current_path is None:
            return
        meta = self._collect_metadata_from_ui()
        self.handler.set_metadata(meta)
        try:
            self.handler.save_metadata()
            self._reset_changed()
            self.statusBar().showMessage("Saved successfully", 3000)
        except Exception as exc:
            QMessageBox.critical(
                self,
                "Error saving EPUB",
                f"Failed to save:\n{self.current_path}\n\n{exc}",
            )
            self.statusBar().showMessage("Save failed")

    def _collect_metadata_from_ui(self) -> EpubMetadata:
        """Gather values from widgets into an EpubMetadata object."""
        return EpubMetadata(
            title=self.ed_title.text(),
            title_sort=self.ed_title_sort.text(),
            creators=[c.strip() for c in self.ed_creators.text().split(";") if c.strip()],
            author_sort=self.ed_author_sort.text(),
            series=self.ed_series.text(),
            series_index=self.ed_series_index.text(),
            language=self._language_code_from_ui(),
            identifiers=self._collect_identifiers(),
            description=self.ed_description.toPlainText(),
            publisher=self.ed_publisher.text(),
            date=self.ed_date.text(),
            subjects=[s.strip() for s in self.ed_subjects.text().split(";") if s.strip()],
            version=self.ed_version.text(),
            rating=self.ed_rating.text(),
            modification_date=self.ed_modification_date.text(),
            cover_id=self.handler.metadata.cover_id,
        )

    def _language_code_from_ui(self) -> str:
        """Extract the raw BCP-47 code from the language combo display text."""
        text = self.ed_language.currentText().strip()
        if " — " in text:
            return text.split(" — ")[0].strip()
        return text

    def closeEvent(self, event):
        if self.changed and self.current_path is not None:
            reply = QMessageBox.question(
                self,
                "Unsaved changes",
                "You have unsaved changes. Save before exiting?",
                QMessageBox.StandardButton.Yes
                | QMessageBox.StandardButton.No
                | QMessageBox.StandardButton.Cancel,
            )
            if reply == QMessageBox.StandardButton.Yes:
                self._on_save()
                event.accept()
            elif reply == QMessageBox.StandardButton.No:
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()

    # ------------------------------------------------------------------
    # Drag & Drop
    # ------------------------------------------------------------------
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if any(u.toLocalFile().lower().endswith(".epub") for u in urls):
                event.acceptProposedAction()
                return
        event.ignore()

    def dropEvent(self, event):
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if path.lower().endswith(".epub"):
                self._load_epub(path)
                break  # load first EPUB only for now

    def eventFilter(self, watched, event):
        if watched is self.ed_language and event.type() == event.Type.Wheel:
            # Ignore wheel events on the language combo so scrolling the form
            # doesn't accidentally change the selected language.
            event.ignore()
            return True
        return super().eventFilter(watched, event)

    def showEvent(self, event):
        super().showEvent(event)
        if not hasattr(self, '_initial_sized'):
            self._initial_sized = True
            # Center on screen
            self._center_window()

    def _center_window(self):
        screen = QApplication.primaryScreen().geometry()
        fg = self.frameGeometry()
        fg.moveCenter(screen.center())
        self.move(fg.topLeft())
