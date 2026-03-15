"""
seed_data.py
============
将前端 Mock 数据完整导入数据库。

覆盖范围:
  - units          : 1 条（亲近自然）
  - themes         : 3 条（主题阅读 / 主题活动 / 技法学习）
  - blocks         : 来自 themeReadingMock / themeActivityMock / techniqueLearningMock
  - badges         : 5 条
  - users          : 1 名教师 + 2 名学生

用法:
    python seed_data.py
    # 或带 DATABASE_URL 覆盖
    DATABASE_URL=postgresql+asyncpg://... python seed_data.py
"""

from __future__ import annotations

import asyncio
import os

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

# --------------------------------------------------------------------------- #
# 数据库连接（优先读环境变量，回退到本地默认值）
# --------------------------------------------------------------------------- #

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:123456@localhost:5432/writing_system",
)

engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False)


# --------------------------------------------------------------------------- #
# Seed 数据
# --------------------------------------------------------------------------- #

# ── Units ──────────────────────────────────────────────────────────────────
UNITS = [
    {
        "id": 1,
        "title": "亲近自然",
        "description": "走进大自然，感受四季之美",
        "image_url": (
            "https://images.unsplash.com/photo-1598439473183-42c9301db5dc"
            "?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&q=80&w=1080"
        ),
        "sort_order": 1,
        "is_published": True,
    }
]

# ── Themes ─────────────────────────────────────────────────────────────────
THEMES = [
    {
        "id": 1,
        "unit_id": 1,
        "title": "主题阅读",
        "theme_type": "themeReading",
        "description": "品读名家自然美文，交流分享阅读感悟，赏析经典文学作品",
        "sort_order": 1,
        "is_published": True,
        "status": "published",
    },
    {
        "id": 2,
        "unit_id": 1,
        "title": "主题活动",
        "theme_type": "themeActivity",
        "description": "拍美景、写美文、展秋色，用镜头和文字记录自然之美",
        "sort_order": 2,
        "is_published": True,
        "status": "published",
    },
    {
        "id": 3,
        "unit_id": 1,
        "title": "技法学习",
        "theme_type": "techniqueLearning",
        "description": "学习写作技法，提升语言表达能力",
        "sort_order": 3,
        "is_published": True,
        "status": "published",
    },
]

# ── Blocks：主题阅读（theme_id=1） ────────────────────────────────────────
# Tab 映射（来自 themeReadingMock.ts）：
#   reading      → 名著导读  📖  (sort_order 1-4)
#   exchange     → 读后交流  💬  (sort_order 5-7)
#   appreciation → 美文欣赏  ✨  (sort_order 8)
BLOCKS_THEME_READING = [
    # ── Tab: 名著导读 ──────────────────────────────────────────────────────
    {
        "theme_id": 1,
        "block_type": "description",
        "title": "学习指引",
        "sort_order": 1,
        "config_json": {
            "id": "reading-desc-1",
            "type": "description",
            "tab_key": "reading",
            "tab_label": "名著导读",
            "tab_icon": "📖",
            "iconName": "BookOpen",
            "themeColor": "blue",
            "title": "学习指引",
            "content": (
                "品读名家关于自然的美文，领会其主旨与情感，"
                "学习\"语言风格借鉴法\"和\"添枝加叶法\"。"
            ),
        },
    },
    {
        "theme_id": 1,
        "block_type": "reading_guide",
        "title": "名著导读",
        "sort_order": 2,
        "config_json": {
            "id": "reading-guide-1",
            "type": "reading_guide",
            "tab_key": "reading",
            "tab_label": "名著导读",
            "tab_icon": "📖",
            "title": "名著导读",
            "guideText": (
                "草木枯荣，春秋更迭，自然万物，值得我们慢慢品味。"
                "正如汪曾祺所言：“如果你来访我，我不在，"
                "请和我门外的花坐一会儿，它们很温暖，我注视它们很多很多日子了。”"
                "翻阅《人间草木》，仿佛沐浴在阳光下，草木虫鸟鱼被赋予了人的气息，"
                "寻常食物在炊烟袅袅中散发着家的味道……"
            ),
            "articleTitle": "《人间草木》节选 - 汪曾祺",
            "audioUrl": "https://www.soundhelix.com/architecture/mp3-player/SoundHelix-Song-1.mp3",
            "paragraphs": [
                (
                    "如果你来访我，我不在，请和我门外的花坐一会儿，"
                    "它们很温暖，我注视它们很多很多日子了。"
                    "它们开得不茂盛，想起来什么颜色就在秋天或春天开起一两朵。"
                    "我是个不讲究种花的人。我只随便插活了一两棵。"
                ),
                (
                    "都说梨花像雪，其实苹果花才像雪。雪是厚重的，不是透明的。"
                    "梨花像什么呢？——梨花的瓣子是月亮做的。"
                    "那一年，花开得很迟。我是五月二日到的，"
                    "这地方的杏花、桃花都已经谢了，只有几棵秋海棠开得正好。"
                ),
            ],
        },
    },
    {
        "theme_id": 1,
        "block_type": "task_driven",
        "title": "任务驱动",
        "sort_order": 3,
        "config_json": {
            "id": "reading-task-1",
            "type": "task_driven",
            "tab_key": "reading",
            "tab_label": "名著导读",
            "tab_icon": "📖",
            "title": "任务驱动",
            "iconName": "Rocket",
            "themeColor": "purple",
            "submitText": "提交任务",
            "tasks": [
                {
                    "id": "task-1",
                    "title": "任务一：读一读汪曾祺的\"草木情\"",
                    "description": [
                        (
                            "古人云\"读万卷书不如行万里路\"，而读《人间草木》，"
                            "就像是与一个可爱的老头走在田间地头……"
                        ),
                        (
                            "重点阅读《人间草木》中\"一果一蔬\"和\"季节的供养\"两辑，"
                            "感受作者寄托在花、树、虫、鱼、鸟、兽、四季果园中的情思，并做批注。"
                        ),
                    ],
                    "extraContent": {
                        "title": "《人间草木》节选（一果一蔬/季节的供养）",
                        "content": [
                            "西瓜以绳络悬之井中，下午剖食，一刀下去，喀嚓有声，凉气四溢，连眼睛都是凉的。",
                            "秋海棠的叶子一面是绿的，一面是红的。这花开得很繁，花瓣有些像小莲花，不过是粉红的。",
                            "葡萄抽条，长叶，开花，结果，成熟，都是悄悄的。葡萄熟了，果园里充满了香气。",
                            "枸杞子红了。秋天，树叶落了，只剩下这些红豆豆，很鲜艳。",
                            "花总是要开的。不管是不是有人看，不管你是不是心情好。",
                        ],
                    },
                    "inputType": "textarea",
                    "placeholder": "在此输入你对文章的批注和感悟...",
                },
                {
                    "id": "task-2",
                    "title": "任务二：品一品汪曾祺的文字",
                    "description": [
                        (
                            "汪曾祺的文字给人一种舒服、有趣的感觉。"
                            "\"舒服\"在于他的语言质朴、自然、温润、亲切；"
                            "\"有趣\"在于他很擅长描写，其文字的画面感极强。"
                        ),
                        "反复朗读你欣赏的语段，选择一段模仿练习，描绘一下身边的花草树木或虫鱼鸟兽。",
                    ],
                    "inputType": "textarea",
                    "placeholder": "参考汪曾祺的风格，在这里描绘你身边的自然景物...",
                    "wordLimit": "100-300字",
                },
            ],
        },
    },
    {
        "theme_id": 1,
        "block_type": "description",
        "title": "课后任务",
        "sort_order": 4,
        "config_json": {
            "id": "reading-desc-2",
            "type": "description",
            "tab_key": "reading",
            "tab_label": "名著导读",
            "tab_icon": "📖",
            "iconName": "MessageCircleQuestion",
            "themeColor": "indigo",
            "title": "课后任务",
            "content": (
                "请在课后仔细阅读汪曾祺先生的散文集《人间草木》，"
                "感受作者平实质朴、形象生动、风趣幽默的语言风格，体会其笔下的\"草木情\"。"
            ),
        },
    },
    # ── Tab: 读后交流 ──────────────────────────────────────────────────────
    {
        "theme_id": 1,
        "block_type": "task_driven",
        "title": "读后交流",
        "sort_order": 5,
        "config_json": {
            "id": "exchange-task-1",
            "type": "task_driven",
            "tab_key": "exchange",
            "tab_label": "读后交流",
            "tab_icon": "💬",
            "title": "读后交流",
            "iconName": "MessageCircleQuestion",
            "themeColor": "indigo",
            "submitText": "提交任务",
            "tasks": [
                {
                    "id": "exchange-1",
                    "title": "话题一：说说身边的自然万物",
                    "description": [
                        "汪曾祺笔下的一草一木，都很天真、质朴，透出勃勃生机。"
                        "《人间草木》流露着亲切的人间烟火气，读完这本书，"
                        "跟自然握握手，去感受身边的自然万物，谈谈你的\"草木情\"吧。",
                    ],
                    "inputType": "textarea",
                    "placeholder": "在此输入你的想法...",
                },
                {
                    "id": "exchange-2",
                    "title": "话题二：谈谈描画自然的方法",
                    "description": [
                        "汪曾祺被誉为\"中国最后一个纯粹的文人，中国最后一个士大夫\"。"
                        "细细品读汪曾祺的文字，思考描画自然的方法，谈谈你的收获。",
                    ],
                    "inputType": "textarea",
                    "placeholder": "在此输入你的想法...",
                },
            ],
        },
    },
    {
        "theme_id": 1,
        "block_type": "reading_recommendation",
        "title": "阅读推荐",
        "sort_order": 6,
        "config_json": {
            "id": "exchange-rec-1",
            "type": "reading_recommendation",
            "tab_key": "exchange",
            "tab_label": "读后交流",
            "tab_icon": "💬",
            "title": "阅读推荐",
            "classics": "孙犁《白洋淀纪事》",
            "essays": "郁达夫《故都的秋》，林语堂《秋天的况味》，冯骥才《冬日絮语》，丰子恺《春》，迟子建《春天是一点一点化开的》",
        },
    },
    # ── Tab: 美文欣赏 ──────────────────────────────────────────────────────
    {
        "theme_id": 1,
        "block_type": "appreciation_list",
        "title": "美文欣赏",
        "sort_order": 7,
        "config_json": {
            "id": "appreciation-list-1",
            "type": "appreciation_list",
            "tab_key": "appreciation",
            "tab_label": "美文欣赏",
            "tab_icon": "✨",
            "items": [
                {
                    "id": "article-1",
                    "tag": "美文赏析一",
                    "intro": (
                        "那城，那河，那古路，那山影，那座诗意般秋色纷呈的济南城，"
                        "是否恰似你幻想中的秋景？作者把对秋天的钟爱，寄于济南那片叠彩幻化、"
                        "层出不穷的山水间，通过对秋天景色的细腻描绘，述说济南古城静美的诗境。"
                    ),
                    "article": {
                        "title": "济南的秋天",
                        "author": "老舍",
                        "allowAnnotation": False,
                        "paragraphs": [
                            {
                                "text": (
                                    "济南的秋天是诗境的。设若你的幻想中有个中古的老城，"
                                    "有睡着了的大城楼，有狭窄的古石路，有宽厚的石城墙，"
                                    "环城流着一道清溪，倒映着山影，岸上蹲着红袍绿裤的小妞儿。"
                                    "你的幻想中要是这么个境界，那便是个济南。"
                                ),
                                "annotations": [
                                    {
                                        "id": "b1",
                                        "start": 0,
                                        "end": 11,
                                        "note": "一句话统领全文。",
                                        "type": "builtin",
                                    }
                                ],
                            },
                            {
                                "text": (
                                    "请你在秋天来。那城，那河，那古路，那山影，"
                                    "是终年给你预备着的。可是，加上济南的秋色，"
                                    "济南由古朴的画境转入静美的诗境中了。"
                                ),
                                "annotations": [],
                            },
                        ],
                    },
                },
            ],
        },
    },
]

# ── Blocks：主题活动（theme_id=2） ────────────────────────────────────────
# Tab 映射（来自 themeActivityMock.ts）：
#   step1 → 拍羊城秋色  📸
#   step2 → 写羊城秋色  ✍️
#   step3 → 展羊城秋色  🖼️
BLOCKS_THEME_ACTIVITY = [
    # ── Tab: step1 拍羊城秋色 ──────────────────────────────────────────────
    {
        "theme_id": 2,
        "block_type": "task_driven",
        "title": "拍羊城秋色",
        "sort_order": 1,
        "config_json": {
            "id": "activity-task-1",
            "type": "task_driven",
            "tab_key": "step1",
            "tab_label": "拍羊城秋色",
            "tab_icon": "📸",
            "title": "拍羊城秋色",
            "iconName": "Image",
            "themeColor": "green",
            "submitText": "提交任务",
            "tasks": [
                {
                    "id": "act-1-1",
                    "title": "任务一：学习摄影技巧",
                    "description": [
                        (
                            "说明：摄影是一门艺术，也是一门学问。"
                            "想要拍好照片，可从取景、构图、光影等方面着手，"
                            "如留白取景，对称式构图、框架式构图、前景式构图、三分法等构图技巧，"
                            "逆光、柔光、冷暖光、光线投影、控制曝光等光影技巧。"
                        )
                    ],
                    "inputType": "textarea",
                    "placeholder": "记录下你学到的摄影技巧或心得体会...",
                },
                {
                    "id": "act-1-2",
                    "title": "任务二：拍摄羊城秋色",
                    "description": [
                        (
                            "说明：秋天的羊城处处展现着其独特的魅力：帽峰山的枫叶、"
                            "华南植物园的奇花异草、天河公园的落羽杉……"
                            "运用你学到的摄影技巧，用镜头来捕捉独特的羊城秋色吧。"
                        )
                    ],
                    "inputType": "image",
                },
            ],
        },
    },
    # ── Tab: step2 写羊城秋色 ──────────────────────────────────────────────
    {
        "theme_id": 2,
        "block_type": "task_driven",
        "title": "写羊城秋色",
        "sort_order": 2,
        "config_json": {
            "id": "activity-task-2",
            "type": "task_driven",
            "tab_key": "step2",
            "tab_label": "写羊城秋色",
            "tab_icon": "✍️",
            "title": "写羊城秋色",
            "iconName": "Edit3",
            "themeColor": "purple",
            "submitText": "提交任务",
            "tasks": [
                {
                    "id": "act-2-1",
                    "title": "任务一：学习作文技法",
                    "description": [
                        "学习「语言风格借鉴法」，细细品味平实质朴、形象生动、风趣幽默三种语言风格，并掌握它们的要点。"
                    ],
                    "inputType": "textarea",
                    "placeholder": "记录下你学习作文技法的心得体会...",
                },
                {
                    "id": "act-2-2",
                    "title": "任务二：写摄影作品配文",
                    "description": [
                        (
                            "仿照朱自清《春》和老舍《济南的冬天》的写法，"
                            "抓住羊城秋天的特点，从外形、色彩、声音等角度展开想象，"
                            "选用一种语言风格，给摄影作品配上情景相融的文字。"
                        )
                    ],
                    "inputType": "textarea",
                    "placeholder": "对于一个在广州住惯的人，像我，秋天要是...",
                    "wordLimit": "不限",
                },
            ],
        },
    },
    # ── Tab: step3 展羊城秋色 ──────────────────────────────────────────────
    {
        "theme_id": 2,
        "block_type": "task_driven",
        "title": "展羊城秋色",
        "sort_order": 3,
        "config_json": {
            "id": "activity-task-3",
            "type": "task_driven",
            "tab_key": "step3",
            "tab_label": "展羊城秋色",
            "tab_icon": "🖼️",
            "title": "展羊城秋色",
            "iconName": "Map",
            "themeColor": "indigo",
            "submitText": "提交任务",
            "tasks": [
                {
                    "id": "act-3-1",
                    "title": "任务一：筹备「羊城之秋」摄影展",
                    "description": [
                        "1. 学习摄影作品赏析小知识，以小组为单位，选择展现羊城秋色的摄影作品，并配文制作演示文稿。",
                        "2. 学习朗诵技巧，以小组为单位，选择朗诵形式，并选出朗诵表演者和朗诵作品。",
                        "3. 以小组为单位，分工排练，筹备展览。",
                    ],
                    "inputType": "images",
                },
            ],
        },
    },
]

# ── Blocks：技法学习（theme_id=3） ───────────────────────────────────────
# Tab 映射（来自 techniqueLearningMock.ts）：
#   technique-1 → 积累入格——"语言风格借鉴法"  ✍️  (sort_order 1-4)
#   technique-2 → 审题立意——"添枝加叶法"      🌿  (sort_order 5-6)
BLOCKS_TECHNIQUE_LEARNING = [
    # ── Tab: technique-1 语言风格借鉴法 ───────────────────────────────────
    {
        "theme_id": 3,
        "block_type": "description",
        "title": "积累入格——「语言风格借鉴法」",
        "sort_order": 1,
        "config_json": {
            "id": "tech-1-desc",
            "type": "description",
            "tab_key": "technique-1",
            "tab_label": "积累入格——\u201c语言风格借鉴法\u201d",
            "tab_icon": "✍️",
            "iconName": "BookOpen",
            "themeColor": "blue",
            "title": "积累入格——「语言风格借鉴法」",
            "content": (
                "我们使用语言来叙事说理、表情达意。丰富的思想、真挚的情感，"
                "要用准确、明白、流畅的语言表达出来。因作者年龄、性格、阅历、"
                "生活环境和写作目的等因素的影响，作品往往呈现出不同的语言风格。"
            ),
        },
    },
    {
        "theme_id": 3,
        "block_type": "markdown",
        "title": "方法指导",
        "sort_order": 2,
        "config_json": {
            "id": "tech-1-markdown",
            "type": "markdown",
            "tab_key": "technique-1",
            "tab_label": "积累入格——\u201c语言风格借鉴法\u201d",
            "tab_icon": "✍️",
            "title": "方法指导",
            "iconName": "Book",
            "themeColor": "indigo",
            "content": (
                "让我们一起品味平实质朴、形象生动、风趣幽默三种常见语言风格的文段，"
                "有意识地去借鉴模仿，以形成自己的语言风格。\n\n"
                "### 1. 平实质朴\n"
                "平实质朴的语言，不造作、不雕饰，不追求辞藻的华丽、句式的整饬，"
                "显现出质朴自然的特点，于平淡中蕴含着深意。\n\n"
                "### 2. 形象生动\n"
                "作者常运用丰富的辞藻、细节描写和修辞手法，把所描述的人物、"
                "事物、情境等具体、形象地展现在读者面前。\n\n"
                "### 3. 风趣幽默\n"
                "风趣幽默的语言往往轻松活泼，引人发笑，同时也可能带有一些深刻的思考或讽刺。"
            ),
        },
    },
    {
        "theme_id": 3,
        "block_type": "editable_table",
        "title": "小试身手",
        "sort_order": 3,
        "config_json": {
            "id": "tech-1-editable",
            "type": "editable_table",
            "tab_key": "technique-1",
            "tab_label": "积累入格——\u201c语言风格借鉴法\u201d",
            "tab_icon": "✍️",
            "title": "小试身手",
            "iconName": "Edit3",
            "themeColor": "green",
            "description": "阅读下面一段文字，分析其语言风格。",
            "headers": ["示例", "点评"],
            "rows": [
                {
                    "id": "row-1",
                    "example": (
                        "我们在田野上散步：我，我的母亲，我的妻子和儿子。\n"
                        "母亲本不愿出来的；她老了，身体不好，走远一点儿就觉得累。\n"
                        "（节选自莫怀戚《散步》）"
                    ),
                    "review": "",
                    "placeholder": "请在此输入你的点评...",
                },
                {
                    "id": "row-2",
                    "example": (
                        "一日下午，我刚进教室就听见福久在眉飞色舞地高喊：“我的青春我做主！”\n"
                        "（节选自《我的同桌叫福久》）"
                    ),
                    "review": "",
                    "placeholder": "请在此输入你的点评...",
                },
            ],
        },
    },
    {
        "theme_id": 3,
        "block_type": "task_driven",
        "title": "实战操练",
        "sort_order": 4,
        "config_json": {
            "id": "tech-1-task",
            "type": "task_driven",
            "tab_key": "technique-1",
            "tab_label": "积累入格——\u201c语言风格借鉴法\u201d",
            "tab_icon": "✍️",
            "title": "实战操练",
            "iconName": "Target",
            "themeColor": "purple",
            "submitText": "提交练习",
            "tasks": [
                {
                    "id": "t1-task-1",
                    "title": "写作练习",
                    "description": [
                        "以《广州的诗意》为题，写一篇500字以上的记叙文，尝试仿效某种语言风格。"
                    ],
                    "inputType": "images",
                    "aiEvaluate": True,
                }
            ],
        },
    },
    # ── Tab: technique-2 添枝加叶法 ───────────────────────────────────────
    {
        "theme_id": 3,
        "block_type": "description",
        "title": "审题立意——「添枝加叶法」",
        "sort_order": 5,
        "config_json": {
            "id": "tech-2-desc",
            "type": "description",
            "tab_key": "technique-2",
            "tab_label": "审题立意——\u201c添枝加叶法\u201d",
            "tab_icon": "🌿",
            "iconName": "BookOpen",
            "themeColor": "blue",
            "title": "审题立意——「添枝加叶法」",
            "content": (
                "「添枝加叶法」，是在题目前后添加一些有关人、事、物、景、情的词语，"
                "使题意更加明显、完整的审题方法。"
            ),
        },
    },
    {
        "theme_id": 3,
        "block_type": "markdown",
        "title": "方法指导 - 题目链接",
        "sort_order": 6,
        "config_json": {
            "id": "tech-2-markdown",
            "type": "markdown",
            "tab_key": "technique-2",
            "tab_label": "审题立意——\u201c添枝加叶法\u201d",
            "tab_icon": "🌿",
            "title": "方法指导",
            "iconName": "Book",
            "themeColor": "indigo",
            "content": (
                "### 题目链接\n"
                "《我》《绿》《秋天》《眼神》《出发》《诱惑》\n\n"
                "### 题目分析\n"
                "以上题目均由一个独词组成，对这类作文题，"
                "我们可以通过添加成分来明确写作范围，确定文章的写作对象、事件和题意。"
            ),
        },
    },
]

# ── Badges ─────────────────────────────────────────────────────────────────
BADGES = [
    {
        "id": 1,
        "unit_id": 1,
        "name": "自然观察家",
        "icon": "🌿",
        "description": "完成\"亲近自然\"单元的主题阅读",
        "condition_json": {"type": "complete_theme", "theme_id": 1},
    },
    {
        "id": 2,
        "unit_id": 1,
        "name": "文学爱好者",
        "icon": "📚",
        "description": "完成\"亲近自然\"单元的全部主题",
        "condition_json": {"type": "complete_unit", "unit_id": 1},
    },
    {
        "id": 6,
        "unit_id": None,
        "name": "勤奋学习者",
        "icon": "✨",
        "description": "累计提交 10 次作答",
        "condition_json": {"type": "submit_count", "count": 10},
    },
    {
        "id": 7,
        "unit_id": None,
        "name": "完美主义者",
        "icon": "🏆",
        "description": "AI 评分达到 90 分以上",
        "condition_json": {"type": "ai_score_gte", "score": 90},
    },
    {
        "id": 8,
        "unit_id": None,
        "name": "坚持不懈",
        "icon": "💪",
        "description": "连续 7 天登录学习",
        "condition_json": {"type": "login_streak", "days": 7},
    },
]

# ── Demo Users ──────────────────────────────────────────────────────────────
DEMO_USERS = [
    {
        "username": "teacher01",
        "display_name": "示例教师",
        "role": "teacher",
        "password": "Teacher@123",
        "class_name": None,
        "is_active": True,
    },
    {
        "username": "S001",
        "display_name": "张三",
        "role": "student",
        "password": "Student@123",
        "class_name": "七年级一班",
        "is_active": True,
    },
    {
        "username": "S002",
        "display_name": "李四",
        "role": "student",
        "password": "Student@123",
        "class_name": "七年级一班",
        "is_active": True,
    },
]


# --------------------------------------------------------------------------- #
# 插入辅助函数
# --------------------------------------------------------------------------- #

async def upsert_unit(session: AsyncSession, data: dict) -> None:
    await session.execute(
        text("""
        INSERT INTO units (id, title, description, image_url, sort_order, is_published)
        VALUES (:id, :title, :description, :image_url, :sort_order, :is_published)
        ON CONFLICT (id) DO UPDATE SET
            title        = EXCLUDED.title,
            description  = EXCLUDED.description,
            image_url    = EXCLUDED.image_url,
            sort_order   = EXCLUDED.sort_order,
            is_published = EXCLUDED.is_published,
            updated_at   = now()
        """),
        data,
    )


async def upsert_theme(session: AsyncSession, data: dict) -> None:
    await session.execute(
        text("""
        INSERT INTO themes (id, unit_id, title, theme_type, description, sort_order, is_published, status)
        VALUES (:id, :unit_id, :title, :theme_type, :description, :sort_order, :is_published, :status)
        ON CONFLICT (id) DO UPDATE SET
            title        = EXCLUDED.title,
            description  = EXCLUDED.description,
            sort_order   = EXCLUDED.sort_order,
            is_published = EXCLUDED.is_published,
            status       = EXCLUDED.status,
            updated_at   = now()
        """),
        data,
    )


async def insert_block(session: AsyncSession, data: dict) -> None:
    """按 theme_id + title + sort_order 做幂等插入（避免重复运行时重复写入）"""
    import json
    await session.execute(
        text("""
        INSERT INTO blocks (theme_id, block_type, title, sort_order, config_json)
        VALUES (:theme_id, :block_type, :title, :sort_order, CAST(:config_json AS jsonb))
        ON CONFLICT DO NOTHING
        """),
        {
            "theme_id":   data["theme_id"],
            "block_type": data["block_type"],
            "title":      data["title"],
            "sort_order": data["sort_order"],
            "config_json": json.dumps(data["config_json"], ensure_ascii=False),
        },
    )


async def upsert_badge(session: AsyncSession, data: dict) -> None:
    import json
    await session.execute(
        text("""
        INSERT INTO badges (id, unit_id, name, icon, description, condition_json)
        VALUES (:id, :unit_id, :name, :icon, :description, CAST(:condition_json AS jsonb))
        ON CONFLICT (id) DO UPDATE SET
            name           = EXCLUDED.name,
            icon           = EXCLUDED.icon,
            description    = EXCLUDED.description,
            condition_json = CAST(EXCLUDED.condition_json AS jsonb)
        """),
        {**data,
            "condition_json": json.dumps(data["condition_json"], ensure_ascii=False)},
    )


async def upsert_user(session: AsyncSession, data: dict) -> None:
    import bcrypt
    hashed = bcrypt.hashpw(
        data["password"].encode(), bcrypt.gensalt()
    ).decode()

    await session.execute(
        text("""
        INSERT INTO users (username, hashed_password, display_name, role, class_name, is_active)
        VALUES (:username, :hashed_password, :display_name, :role, :class_name, :is_active)
        ON CONFLICT (username) DO UPDATE SET
            display_name    = EXCLUDED.display_name,
            role            = EXCLUDED.role,
            class_name      = EXCLUDED.class_name,
            is_active       = EXCLUDED.is_active,
            updated_at      = now()
        """),
        {
            "username":        data["username"],
            "hashed_password": hashed,
            "display_name":    data["display_name"],
            "role":            data["role"],
            "class_name":      data.get("class_name"),
            "is_active":       data.get("is_active", True),
        },
    )


# --------------------------------------------------------------------------- #
# 主入口
# --------------------------------------------------------------------------- #

async def run_seed() -> None:
    async with AsyncSessionLocal() as session:
        async with session.begin():
            print("▶ 插入 Units ...")
            for u in UNITS:
                await upsert_unit(session, u)

            print("▶ 插入 Themes ...")
            await session.execute(text("SELECT setval('themes_id_seq', 10, false)"))
            for t in THEMES:
                await upsert_theme(session, t)

            print("▶ 插入 Blocks（主题阅读）...")
            await session.execute(text("DELETE FROM blocks WHERE theme_id = 1"))
            for b in BLOCKS_THEME_READING:
                await insert_block(session, b)

            print("▶ 插入 Blocks（主题活动）...")
            await session.execute(text("DELETE FROM blocks WHERE theme_id = 2"))
            for b in BLOCKS_THEME_ACTIVITY:
                await insert_block(session, b)

            print("▶ 插入 Blocks（技法学习）...")
            await session.execute(text("DELETE FROM blocks WHERE theme_id = 3"))
            for b in BLOCKS_TECHNIQUE_LEARNING:
                await insert_block(session, b)

            print("▶ 插入 Badges ...")
            for badge in BADGES:
                await upsert_badge(session, badge)

            print("▶ 插入 Users ...")
            for user in DEMO_USERS:
                await upsert_user(session, user)

        print("✅ Seed 完成！")
        print(f"   Units  : {len(UNITS)}")
        print(f"   Themes : {len(THEMES)}")
        blocks_total = (
            len(BLOCKS_THEME_READING)
            + len(BLOCKS_THEME_ACTIVITY)
            + len(BLOCKS_TECHNIQUE_LEARNING)
        )
        print(f"   Blocks : {blocks_total}")
        print(f"   Badges : {len(BADGES)}")
        print(f"   Users  : {len(DEMO_USERS)}")
        print()
        print("   账号一览：")
        for u in DEMO_USERS:
            tag = "👨‍🏫 教师" if u["role"] == "teacher" else "👨‍🎓 学生"
            cls = f"  班级: {u['class_name']}" if u.get("class_name") else ""
            print(f"   {tag}  用户名: {u['username']}  密码: {u['password']}{cls}")


if __name__ == "__main__":
    asyncio.run(run_seed())
