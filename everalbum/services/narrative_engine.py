from __future__ import annotations

import random
import re
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


def is_non_location_label(label: str) -> bool:
    if not label:
        return True
    normalized = label.strip()
    if normalized in ("旅途中", "Unknown", "Unknown Location"):
        return True
    if re.search(r"\d+\.\d+[NSns]", normalized):
        return True
    if re.match(r"^\d{4}年\d{1,2}月\d{1,2}日$", normalized):
        return True
    return False


def shorten_location(label: str) -> str:
    if is_non_location_label(label):
        return ""
    parts = [part.strip() for part in label.split(",") if part.strip()]
    if not parts:
        return label.strip()
    return parts[0]


@dataclass(slots=True)
class NarrativeContext:
    event_key: str
    date_text: str
    date_hint: str
    location: str
    scene: str
    time_of_day: str
    season: str
    photo_count: int
    hour_span: float
    day_span: int
    pace: str
    energy: str
    has_location: bool


@dataclass(slots=True)
class EventNarrativePlan:
    context: NarrativeContext
    chapter_kicker: str
    chapter_story: str
    summary_line: str
    role_notes: dict[str, list[str]]

    def note_for_role(self, role: str, page_index: int = 0) -> str:
        notes = self.role_notes.get(role) or self.role_notes.get("narrative") or []
        if not notes:
            return ""
        if page_index < len(notes):
            return notes[page_index]
        return NarrativeEngine.extend_note_for_page(self, role, page_index)


class NarrativeEngine:
    TIME_LABELS = {
        "morning": "清晨",
        "afternoon": "午后",
        "evening": "傍晚",
        "night": "夜里",
    }

    SEASON_LABELS = {
        "spring": "春天",
        "summer": "夏天",
        "autumn": "秋天",
        "winter": "冬天",
    }

    SETTING_WITH_LOCATION = [
        "{date_hint}的{location}",
        "{location}的{time_of_day}",
        "{date_hint}，在{location}",
        "{location}这一段{time_of_day}",
        "{season}里的{location}",
        "{date_hint}走到{location}时",
        "{location}把这天的{time_of_day}留了下来",
    ]

    SETTING_NO_LOCATION = [
        "{date_hint}",
        "这一天的{time_of_day}",
        "{season}里的{time_of_day}",
        "{date_text}这一天",
        "镜头停下来的这个{time_of_day}",
    ]

    SCENE_LEADS = {
        "sky": [
            "天空先把视野打开了",
            "抬头时，天色已经足够辽阔",
            "云层替这段行程铺好了开场",
            "光线从高处慢慢落下来",
        ],
        "night": [
            "夜色把情绪压得很低，却很稳",
            "灯火一亮，城市的轮廓就清楚了",
            "夜里最先被记住的，总是光点和人影",
            "暗下去的天色，反而让细节更显眼",
        ],
        "sunset": [
            "傍晚的光把一切都镀得温柔了一点",
            "黄昏出现时，画面自己就有了层次",
            "余晖一落下来，气氛就慢慢完整了",
            "快要落山的太阳，把这段时间照得刚刚好",
        ],
        "water": [
            "水面把光留住，也把时间拉慢了",
            "有水的地方，总会多一点呼吸感",
            "波纹一层层展开，画面也跟着安静下来",
            "风从水边经过时，照片里总会有流动感",
        ],
        "nature": [
            "绿色先把人安静下来",
            "树影和远处的线条，把空间慢慢撑开",
            "走进自然以后，镜头也会变得松弛",
            "山、树和空气一起把节奏放慢了",
        ],
        "outdoor": [
            "户外的光线让画面天然有了呼吸",
            "人在外面走着，故事也就自然展开了",
            "光一落在脸上，记忆就有了温度",
            "开阔的空间，总能把情绪一起带开",
        ],
        "general": [
            "这一段时间没有急着解释自己",
            "镜头先把当时的空气收了进去",
            "那一刻不喧哗，却很完整",
            "画面里没有刻意安排，却刚好成立",
        ],
    }

    DETAIL_LINES = {
        "sky": [
            "风把云的边缘吹得很轻",
            "高处的颜色干净得像一段留白",
            "天光把远近关系一下子拉开了",
            "抬头的瞬间，心情也跟着变得宽一点",
        ],
        "night": [
            "街灯把夜晚切成一小段一小段的光",
            "黑暗没有吞掉细节，反而让它们更集中",
            "越是安静的时候，镜头越能记住情绪",
            "灯火落进画面里，像是在替这一天收尾",
        ],
        "sunset": [
            "颜色从亮到暗的过渡，正好像这一天的尾声",
            "暖光贴在人物和景物边缘，连轮廓都柔和了",
            "短短一会儿的金色，足够把记忆点亮",
            "天边开始发橙的时候，照片就有了温度",
        ],
        "water": [
            "倒影和波纹把静止的画面轻轻推开",
            "有些情绪不必说，水面已经替它表达了",
            "亮处和暗处都被水连在了一起",
            "镜头一靠近水边，节奏就自然慢了下来",
        ],
        "nature": [
            "树影、草地和风声，把杂念都往后放了放",
            "层层叠叠的绿色，让画面很难显得仓促",
            "自然里的细节不抢镜，却总能留住人",
            "宽阔感不是来自远方，而是来自呼吸终于松开",
        ],
        "outdoor": [
            "边走边看时，照片会自己积累出层次",
            "光线、表情和动作在外面更容易碰到一起",
            "开阔的空间让每个停顿都显得不拘束",
            "那些不经意的小动作，往往最像当时的心情",
        ],
        "general": [
            "先留下的是气氛，后来才慢慢变成回忆",
            "不是每一张都在讲大事，但都在保存当时的感觉",
            "镜头收下来的，往往是最难复述的那部分",
            "有些时候不用热闹，画面也足够成立",
        ],
    }

    PACE_LINES = {
        "still": [
            "镜头没有追求热闹，只把那个停顿认真留下",
            "没有太多铺陈，一个瞬间就足够说明当时的状态",
            "画面收得很轻，却把情绪压得很实",
        ],
        "stroll": [
            "这组照片像是在边走边看，慢慢把情境补齐",
            "镜头不是一下子靠近的，而是随着脚步一点点进入现场",
            "从一个细节走到下一个细节，这段经历就有了顺序",
        ],
        "journey": [
            "从前一段路走到下一段路，记忆也跟着慢慢展开",
            "时间往前推着走，画面把沿途的层次一并收了进来",
            "不是单一的停留，更像是一段逐渐展开的行程",
        ],
        "collect": [
            "照片数量多起来以后，像是在把这一天分段收藏",
            "镜头没有急着总结，而是一点点把细节收拢成形",
            "这一组更像连续取样，把现场的变化都耐心记了下来",
        ],
    }

    CLOSING_LINES = {
        "calm": [
            "后来回头看，最先浮现出来的还是这份安静。",
            "它没有很响亮，却很适合被长久记住。",
            "真正留下来的，不是热闹，而是那种慢慢沉下来的感觉。",
        ],
        "warm": [
            "等很久以后再翻到这里，应该还会先想起当时的温度。",
            "它让这一天有了一个柔和、可信的落点。",
            "所以这一页看起来很轻，却很容易让人重新回到现场。",
        ],
        "lively": [
            "这种有来有往的热度，会让整段经历显得格外鲜活。",
            "等回看时，节奏感会比单张照片更先把记忆叫醒。",
            "它把这段时间的生气完整保留下来了。",
        ],
        "balanced": [
            "于是这一页既留下了现场，也留下了当时的心情。",
            "它不是最喧闹的一页，却很像这一段经历真正的样子。",
            "等时间过去以后，这样的画面往往最耐看。",
        ],
    }

    PACE_LABELS = {
        "still": "停顿",
        "stroll": "漫游",
        "journey": "行程",
        "collect": "铺陈",
    }

    ENERGY_LABELS = {
        "calm": "安静",
        "warm": "温度",
        "lively": "热度",
        "balanced": "平衡",
    }

    _album_story_history: set[str] = set()
    _album_note_history: dict[str, set[str]] = {
        "opening": set(),
        "narrative": set(),
        "highlight": set(),
        "closing": set(),
    }
    _album_note_global_history: set[str] = set()
    _album_usage: dict[str, Counter] = {}
    _album_prefix_usage: dict[str, Counter] = {}

    TEMPLATE_FAMILIES = {
        "still": [
            "{setting}，{scene_lead}。{detail}，{closing}",
            "{setting}。{scene_lead}，{closing}",
            "{setting}，{pace_line}。{closing}",
            "{setting}。{detail}，这让这一页更像被认真停住的一个片刻。{closing}",
            "{setting}，{scene_lead}。{pace_line}，{closing}",
        ],
        "stroll": [
            "{setting}，{scene_lead}。{pace_line}，{closing}",
            "{setting}。{detail}，{pace_line}；{closing}",
            "{setting}，{scene_lead}，也让这组照片慢慢有了层次。{closing}",
            "{setting}。{detail}，于是故事不是一下子说完，而是顺着画面慢慢展开。{closing}",
            "{setting}，{pace_line}。{scene_lead}，{closing}",
        ],
        "journey": [
            "{setting}，{pace_line}。{detail}，{closing}",
            "{setting}。{scene_lead}，一路把零散的片段串成了同一段经历。{closing}",
            "{setting}，这并不是单一的停留。{detail}，{closing}",
            "{setting}。{pace_line}，也让沿途的变化都获得了位置。{closing}",
            "{setting}，{scene_lead}。{detail}，于是这一页更像路上的连续章节。{closing}",
        ],
        "collect": [
            "{setting}。{pace_line}，{detail}；{closing}",
            "{setting}，{scene_lead}。镜头把细小变化都认真收了下来，{closing}",
            "{setting}，这一组像是在给当天做一次完整取样。{detail}，{closing}",
            "{setting}。{detail}，丰富感不是突然出现的，而是这些片段一点点堆出来的。{closing}",
            "{setting}，{pace_line}。{scene_lead}，{closing}",
        ],
    }

    ROLE_NOTE_TEMPLATES = {
        "opening": [
            "故事从{setting_short}开始。",
            "{time_of_day}先把这一段慢慢打开。",
            "{scene_short}，这一页更像整段故事的开场。",
            "第一页先交代空气和光线，{setting_short}就这样出现了。",
            "镜头先在{setting_short}站稳，故事才继续往前。",
            "{photo_short}里，这一页负责把场景抬起来。",
            "{scene_short}，开场不必热闹，先把氛围放准就够了。",
            "从{setting_short}起笔，这一段有了第一个落点。",
            "{time_of_day}刚刚展开，画面先替故事定了调。",
            "{setting_short}先出现，后面的内容才有了方向。",
        ],
        "narrative": [
            "{pace_short}，细节开始一层层补齐。",
            "{detail_short}，画面继续往前推进。",
            "这一页负责把现场真正铺开。",
            "镜头没有停在表面，反而把更多细枝末节留了下来。",
            "{pace_short}，所以这一页像是在把过程补完整。",
            "场景继续向前延展，情绪也跟着有了层次。",
            "{duration_short}的变化，被这一页认真接住了。",
            "{energy_short}没有一下子冲出来，而是被这一页慢慢推近。",
            "这页不像总结，更像故事中间最自然的一次换气。",
            "{scene_short}，于是故事不是跳着发生，而是顺着长出来。",
        ],
        "highlight": [
            "这一页留给最能代表当下的一刻。",
            "{scene_short}，情绪在这里被看得最清楚。",
            "最能把气氛定住的画面，被放在了这里。",
            "如果要从这一段里记住一页，多半就是现在这一页。",
            "这一刻不一定最热闹，却最像这段经历真正的核心。",
            "{detail_short}，于是重点不需要再额外强调。",
            "画面走到这里，情绪终于被看见了。",
            "{energy_short}在这里最完整，所以这一页自然成了重心。",
            "高光不一定靠夸张，这一页靠的是气氛终于站稳。",
            "它把前面铺过的内容，在这里收成了最清楚的一笔。",
        ],
        "closing": [
            "这一段到这里慢慢收住。",
            "{closing_short}",
            "最后留下来的，是气氛而不是解释。",
            "这一页不急着总结，只让情绪自然落下去。",
            "{time_of_day}走到尾声时，这页把余味留了下来。",
            "{duration_short}过后，故事在这里放慢了收束的速度。",
            "真正耐看的，往往就是这样慢慢退场的画面。",
            "到最后，记住的通常不是信息，而是这一页的气息。",
            "{closing_short}，所以结尾并不喧闹，却很稳。",
            "故事没有被说尽，但它已经完成了自己的落点。",
        ],
    }

    ROLE_NOTE_EXPANSIONS = {
        "opening": [
            "先把空气和方向交代清楚。",
            "画面还没急着靠近，气氛已经先到了。",
            "镜头先站稳，后面的内容才有了入口。",
            "这一眼更像在替整段经历定调。",
            "从这里开始，视线才慢慢有了方向。",
            "先让人知道身在何处，故事才好继续。",
            "这页不抢着说明，只把门轻轻推开。",
            "开场收得越稳，后面的情绪越容易接上。",
        ],
        "narrative": [
            "前后的关系也从这里开始顺起来。",
            "镜头不再只看表面，而是开始碰到更多层次。",
            "这一页把零散片段接成了连续的一段。",
            "内容往前推的时候，细节也被一点点带了出来。",
            "现场的密度，就是在这种页里慢慢长出来的。",
            "它让前面铺下的气氛，开始真正变成过程。",
            "画面继续往里走，记忆也跟着更具体。",
            "到这里，故事已经不只是记录，而是有了推进感。",
        ],
        "highlight": [
            "真正的记忆点也在这里立住了。",
            "前面铺开的东西，到这里终于对上了焦点。",
            "它不是最大声的一页，却最像核心。",
            "这页把气氛和主题一下子扣紧了。",
            "到这里，最能代表当下的一瞬被看见了。",
            "画面走到这里，情绪终于有了正面。",
            "这一页让整段经历的重心清晰下来。",
            "前后所有细节，在这里都有了归拢。",
        ],
        "closing": [
            "余味就是从这里慢慢沉下来的。",
            "解释到这里已经不再重要，气息更重要。",
            "收束感不是突然停下，而是这样一点点放轻。",
            "它替这一段把声音放低了。",
            "翻过去以后，最先留下来的多半就是这一页的气氛。",
            "这页把前面的热度安静地收了回来。",
            "故事没有说尽，但落点已经够了。",
            "到这里，整段经历有了可以停住的地方。",
        ],
    }

    ROLE_PAGE_TRANSITIONS = {
        "opening": [
            "翻到这里，故事才算真正起笔。",
            "从这一页往后，节奏会慢慢打开。",
            "这页把入口留给了后面的内容。",
            "接下来的层次，都是从这里长出来的。",
            "它让后面的内容不至于突兀地闯进来。",
            "这一页像把门推开了一半，刚好够人走进去。",
            "也正因为这样，后面的照片都有了来处。",
            "它把第一口空气先留给了这一段。",
        ],
        "narrative": [
            "再往后看，内容已经比前面更靠近现场。",
            "看到这里，视线开始从大处转向具体。",
            "这一页把前后几张照片串成了同一段呼吸。",
            "继续翻下去，会发现情绪已经悄悄累积起来。",
            "这里像一次顺势的推进，不突兀，却很必要。",
            "画面到了这里，叙事已经开始自己往前走。",
            "这页让节奏不至于断开，也不至于太满。",
            "它把前后内容接得更顺，也更耐看。",
        ],
        "highlight": [
            "所以人会很自然地在这里停一下。",
            "它让整段经历第一次有了明确中心。",
            "这一页很容易先被记住。",
            "看到这里，前面的铺垫才算真正落地。",
            "也正因为这样，这页会比别的页更先留在脑子里。",
            "从这一页回看，前面的内容都会更清楚。",
            "它让整段经历一下子有了抓手。",
            "故事走到这里，终于亮出了最核心的一面。",
        ],
        "closing": [
            "翻到这里，整段经历开始把声音放低。",
            "到这一页，收束感已经比解释更重要了。",
            "后面的空白，也像是这页的一部分。",
            "它让结束来得自然，而不是突然。",
            "这一页留住的不是信息，而是余韵。",
            "看到这里，故事已经知道该在哪里停下。",
            "整段节奏在这里慢慢落回安静。",
            "也因此，结尾不需要再额外强调什么。",
        ],
    }

    @classmethod
    def reset_album_memory(cls):
        cls._album_story_history = set()
        cls._album_note_history = {
            "opening": set(),
            "narrative": set(),
            "highlight": set(),
            "closing": set(),
        }
        cls._album_note_global_history = set()
        cls._album_usage = {}
        cls._album_prefix_usage = {}

    @classmethod
    def time_of_day_label(cls, dt: datetime | None) -> str:
        if dt is None:
            return "白天"
        hour = dt.hour
        if hour < 10:
            return cls.TIME_LABELS["morning"]
        if hour < 14:
            return cls.TIME_LABELS["afternoon"]
        if hour < 19:
            return cls.TIME_LABELS["evening"]
        return cls.TIME_LABELS["night"]

    @classmethod
    def season_label(cls, month: int | None) -> str:
        if month in (3, 4, 5):
            return cls.SEASON_LABELS["spring"]
        if month in (6, 7, 8):
            return cls.SEASON_LABELS["summer"]
        if month in (9, 10, 11):
            return cls.SEASON_LABELS["autumn"]
        return cls.SEASON_LABELS["winter"]

    @classmethod
    def build_context(cls, group: list, location_label: str, scene: str = "general") -> NarrativeContext:
        dates = sorted([photo.dt for photo in group if getattr(photo, "dt", None)])
        start = dates[0] if dates else None
        end = dates[-1] if dates else start
        hour_span = 0.0
        day_span = 0
        if start and end:
            hour_span = max((end - start).total_seconds() / 3600.0, 0.0)
            day_span = max((end.date() - start.date()).days, 0)

        photo_count = len(group)
        pace = cls._infer_pace(photo_count, hour_span, day_span)
        energy = cls._infer_energy(photo_count, scene, hour_span)
        location = shorten_location(location_label)
        has_location = bool(location)

        date_text = start.strftime("%Y年%m月%d日") if start else "这一天"
        date_hint = start.strftime("%m月%d日") if start else "这一天"
        time_of_day = cls.time_of_day_label(start)
        season = cls.season_label(start.month if start else None)

        seed_parts = [date_text, location or "no-location", scene, str(photo_count), pace]
        seed_parts.extend(Path(getattr(photo, "path", "")).name for photo in group[:4])
        event_key = "|".join(seed_parts)

        return NarrativeContext(
            event_key=event_key,
            date_text=date_text,
            date_hint=date_hint,
            location=location,
            scene=scene if scene in cls.SCENE_LEADS else "general",
            time_of_day=time_of_day,
            season=season,
            photo_count=photo_count,
            hour_span=hour_span,
            day_span=day_span,
            pace=pace,
            energy=energy,
            has_location=has_location,
        )

    @classmethod
    def generate_from_group(cls, group: list, location_label: str, scene: str = "general") -> str:
        context = cls.build_context(group, location_label, scene=scene)
        return cls.generate(context)

    @classmethod
    def generate(cls, context: NarrativeContext) -> str:
        story_pool = cls._album_counter("story_pool")
        prefix_pool = cls._album_counter("story_prefix")
        template_pool = cls._album_counter("story_template")
        setting_pool_usage = cls._album_counter("story_setting")
        scene_pool_usage = cls._album_counter("story_scene")
        detail_pool_usage = cls._album_counter("story_detail")
        pace_pool_usage = cls._album_counter("story_pace")
        closing_pool_usage = cls._album_counter("story_closing")

        candidates = []
        seen: set[str] = set()
        for attempt in range(72):
            rng = random.Random(f"{context.event_key}|story|{attempt}")
            template = rng.choice(cls.TEMPLATE_FAMILIES.get(context.pace, cls.TEMPLATE_FAMILIES["stroll"]))
            setting_template = rng.choice(
                cls.SETTING_WITH_LOCATION if context.has_location else cls.SETTING_NO_LOCATION
            )
            setting = setting_template.format(
                date_text=context.date_text,
                date_hint=context.date_hint,
                location=context.location,
                time_of_day=context.time_of_day,
                season=context.season,
            )
            scene_lead = rng.choice(cls.SCENE_LEADS.get(context.scene, cls.SCENE_LEADS["general"]))
            detail = rng.choice(cls.DETAIL_LINES.get(context.scene, cls.DETAIL_LINES["general"]))
            pace_line = rng.choice(cls.PACE_LINES.get(context.pace, cls.PACE_LINES["stroll"]))
            closing = rng.choice(cls.CLOSING_LINES.get(context.energy, cls.CLOSING_LINES["balanced"]))
            story = cls._cleanup(
                template.format(
                    setting=setting,
                    scene_lead=scene_lead,
                    detail=detail,
                    pace_line=pace_line,
                    closing=closing,
                )
            )
            if story in seen:
                continue
            seen.add(story)
            prefix = cls._first_clause(story)
            score = (
                story_pool[story] * 500
                + prefix_pool[prefix] * 120
                + template_pool[template] * 18
                + setting_pool_usage[setting_template] * 10
                + scene_pool_usage[scene_lead] * 10
                + detail_pool_usage[detail] * 8
                + pace_pool_usage[pace_line] * 7
                + closing_pool_usage[closing] * 7
            )
            candidates.append((score, attempt, story, prefix, template, setting_template, scene_lead, detail, pace_line, closing))

        if not candidates:
            story = "这一页把当时的片段安静留了下来。"
            prefix = cls._first_clause(story)
            template = ""
            setting_template = ""
            scene_lead = detail = pace_line = closing = ""
        else:
            _, _, story, prefix, template, setting_template, scene_lead, detail, pace_line, closing = min(candidates)

        story = cls._claim_unique(
            story,
            cls._album_story_history,
            cls._unique_suffixes(context),
        )
        final_prefix = cls._first_clause(story)
        story_pool[story] += 1
        prefix_pool[final_prefix] += 1
        if template:
            template_pool[template] += 1
        if setting_template:
            setting_pool_usage[setting_template] += 1
        if scene_lead:
            scene_pool_usage[scene_lead] += 1
        if detail:
            detail_pool_usage[detail] += 1
        if pace_line:
            pace_pool_usage[pace_line] += 1
        if closing:
            closing_pool_usage[closing] += 1
        return story

    @classmethod
    def build_plan(cls, context: NarrativeContext) -> EventNarrativePlan:
        chapter_story = cls.generate(context)
        chapter_kicker = cls._build_kicker(context)
        summary_line = cls._build_summary(context)
        role_notes = {
            role: cls._build_role_notes(context, role)
            for role in ("opening", "narrative", "highlight", "closing")
        }
        return EventNarrativePlan(
            context=context,
            chapter_kicker=chapter_kicker,
            chapter_story=chapter_story,
            summary_line=summary_line,
            role_notes=role_notes,
        )

    @classmethod
    def build_plan_from_group(cls, group: list, location_label: str, scene: str = "general") -> EventNarrativePlan:
        context = cls.build_context(group, location_label, scene=scene)
        return cls.build_plan(context)

    @staticmethod
    def _pick(rng: random.Random, pool: list[str], used: set[str]) -> str:
        fresh = [item for item in pool if item not in used]
        choice = rng.choice(fresh or pool)
        used.add(choice)
        return choice

    @staticmethod
    def _infer_pace(photo_count: int, hour_span: float, day_span: int) -> str:
        if day_span >= 1 or hour_span >= 8:
            return "journey"
        if photo_count >= 12:
            return "collect"
        if photo_count <= 3 or hour_span <= 0.6:
            return "still"
        return "stroll"

    @staticmethod
    def _infer_energy(photo_count: int, scene: str, hour_span: float) -> str:
        if scene in ("night", "sky", "water") and photo_count <= 8:
            return "calm"
        if scene in ("sunset", "outdoor"):
            return "warm"
        if photo_count >= 10 or hour_span >= 4:
            return "lively"
        return "balanced"

    @staticmethod
    def _cleanup(text: str) -> str:
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\s*([，。；])\s*", r"\1", text)
        text = text.replace("。。", "。")
        text = text.replace("，，", "，")
        text = text.replace("；。", "。")
        return text.strip()

    @classmethod
    def _build_kicker(cls, context: NarrativeContext) -> str:
        parts = [
            context.time_of_day,
            cls.PACE_LABELS.get(context.pace, context.pace),
            f"{context.photo_count}张记录",
        ]
        if context.has_location:
            parts.insert(0, context.location)
        return " / ".join(parts)

    @classmethod
    def _build_summary(cls, context: NarrativeContext) -> str:
        duration = cls._duration_label(context)
        parts = [context.date_hint, context.time_of_day, f"{context.photo_count}张"]
        if duration:
            parts.append(duration)
        return " / ".join(parts)

    @classmethod
    def _duration_label(cls, context: NarrativeContext) -> str:
        if context.day_span >= 1:
            return f"{context.day_span + 1}天片段"
        if context.hour_span >= 6:
            return f"{int(round(context.hour_span))}小时展开"
        if context.hour_span >= 1.2:
            return f"{int(round(context.hour_span))}小时经过"
        return "短暂停留"

    @classmethod
    def _build_role_notes(cls, context: NarrativeContext, role: str) -> list[str]:
        templates = cls.ROLE_NOTE_TEMPLATES.get(role, cls.ROLE_NOTE_TEMPLATES["narrative"])
        history = cls._album_note_history.setdefault(role, set())
        global_history = cls._album_note_global_history
        pool_usage = cls._album_counter(f"{role}_pool")
        prefix_usage = cls._album_counter(f"{role}_prefix")
        template_usage = cls._album_counter(f"{role}_template")
        setting_usage = cls._album_counter(f"{role}_setting")
        scene_usage = cls._album_counter(f"{role}_scene")
        detail_usage = cls._album_counter(f"{role}_detail")
        closing_usage = cls._album_counter(f"{role}_closing")
        pace_usage = cls._album_counter(f"{role}_pace")
        expansion_usage = cls._album_counter(f"{role}_expansion")
        transition_usage = cls._album_counter(f"{role}_transition")
        notes: list[str] = []
        local_seen: set[str] = set()
        target_count = min(36, max(12, context.photo_count // 2 + 6))
        for note_index in range(target_count):
            candidates = []
            for attempt in range(max(240, len(templates) * 18)):
                rng = random.Random(f"{context.event_key}|{role}|{note_index}|{attempt}")
                template = rng.choice(templates)
                setting_short = rng.choice(cls._setting_short_options(context))
                scene_short = rng.choice(cls.SCENE_LEADS.get(context.scene, cls.SCENE_LEADS["general"]))
                detail_short = rng.choice(cls.DETAIL_LINES.get(context.scene, cls.DETAIL_LINES["general"]))
                closing_short = rng.choice(cls.CLOSING_LINES.get(context.energy, cls.CLOSING_LINES["balanced"]))
                pace_short = rng.choice(cls.PACE_LINES.get(context.pace, cls.PACE_LINES["stroll"]))
                expansion = rng.choice(cls.ROLE_NOTE_EXPANSIONS.get(role, cls.ROLE_NOTE_EXPANSIONS["narrative"]))
                transition = rng.choice(cls.ROLE_PAGE_TRANSITIONS.get(role, cls.ROLE_PAGE_TRANSITIONS["narrative"]))
                compose_mode = rng.randrange(4)
                note = cls._cleanup(
                    template.format(
                        setting_short=setting_short,
                        time_of_day=context.time_of_day,
                        scene_short=scene_short,
                        detail_short=detail_short,
                        closing_short=closing_short,
                        pace_short=pace_short,
                        photo_short=f"{context.photo_count}张的这一段",
                        duration_short=cls._duration_label(context),
                        energy_short=cls.ENERGY_LABELS.get(context.energy, context.energy),
                    )
                )
                if compose_mode == 1:
                    note = cls._cleanup(f"{expansion} {note}")
                elif compose_mode == 2:
                    note = cls._cleanup(f"{transition} {note}")
                elif compose_mode == 3:
                    note = cls._cleanup(f"{transition} {note} {expansion}")
                if note in local_seen:
                    continue
                prefix = cls._first_clause(note)
                score = (
                    pool_usage[note] * 400
                    + prefix_usage[prefix] * 150
                    + template_usage[template] * 24
                    + setting_usage[setting_short] * 16
                    + scene_usage[scene_short] * 16
                    + detail_usage[detail_short] * 14
                    + closing_usage[closing_short] * 12
                    + pace_usage[pace_short] * 10
                    + expansion_usage[expansion] * 9
                    + transition_usage[transition] * 8
                )
                candidates.append(
                    (
                        score,
                        attempt,
                        note,
                        prefix,
                        template,
                        setting_short,
                        scene_short,
                        detail_short,
                        closing_short,
                        pace_short,
                        expansion,
                        transition,
                    )
                )
            if not candidates:
                break
            (
                _,
                _,
                note,
                prefix,
                template,
                setting_short,
                scene_short,
                detail_short,
                closing_short,
                pace_short,
                expansion,
                transition,
            ) = min(candidates)
            local_seen.add(note)
            note = cls._claim_unique(note, global_history, cls._unique_suffixes(context))
            final_prefix = cls._first_clause(note)
            notes.append(note)
            history.add(note)
            pool_usage[note] += 1
            prefix_usage[final_prefix] += 1
            template_usage[template] += 1
            setting_usage[setting_short] += 1
            scene_usage[scene_short] += 1
            detail_usage[detail_short] += 1
            closing_usage[closing_short] += 1
            pace_usage[pace_short] += 1
            expansion_usage[expansion] += 1
            transition_usage[transition] += 1
        return notes

    @classmethod
    def extend_note_for_page(cls, plan: EventNarrativePlan, role: str, page_index: int) -> str:
        notes = plan.role_notes.setdefault(role, [])
        if not notes:
            notes.extend(cls._build_role_notes(plan.context, role))
        local_seen = set(notes)
        while len(notes) <= page_index:
            seed = random.Random(f"{plan.context.event_key}|{role}|extra|{len(notes)}")
            fields = {
                "setting_short": seed.choice(cls._setting_short_options(plan.context)),
                "time_of_day": plan.context.time_of_day,
                "scene_short": seed.choice(cls.SCENE_LEADS.get(plan.context.scene, cls.SCENE_LEADS["general"])),
                "detail_short": seed.choice(cls.DETAIL_LINES.get(plan.context.scene, cls.DETAIL_LINES["general"])),
                "closing_short": seed.choice(cls.CLOSING_LINES.get(plan.context.energy, cls.CLOSING_LINES["balanced"])),
                "pace_short": seed.choice(cls.PACE_LINES.get(plan.context.pace, cls.PACE_LINES["stroll"])),
                "photo_short": f"{plan.context.photo_count}张照片的这一段",
                "duration_short": cls._duration_label(plan.context),
                "energy_short": cls.ENERGY_LABELS.get(plan.context.energy, plan.context.energy),
            }
            template = seed.choice(cls.ROLE_NOTE_TEMPLATES.get(role, cls.ROLE_NOTE_TEMPLATES["narrative"]))
            expansion = seed.choice(cls.ROLE_NOTE_EXPANSIONS.get(role, cls.ROLE_NOTE_EXPANSIONS["narrative"]))
            transition = seed.choice(cls.ROLE_PAGE_TRANSITIONS.get(role, cls.ROLE_PAGE_TRANSITIONS["narrative"]))
            compose_mode = seed.randrange(4)
            note = cls._cleanup(template.format(**fields))
            if compose_mode == 1:
                note = cls._cleanup(f"{expansion} {note}")
            elif compose_mode == 2:
                note = cls._cleanup(f"{transition} {note}")
            elif compose_mode == 3:
                note = cls._cleanup(f"{transition} {note} {expansion}")
            if note in local_seen:
                note = cls._claim_unique(note, cls._album_note_global_history, cls._unique_suffixes(plan.context))
            else:
                cls._album_note_global_history.add(note)
            local_seen.add(note)
            cls._album_note_history.setdefault(role, set()).add(note)
            notes.append(note)
        return notes[page_index]

    @classmethod
    def _setting_short_options(cls, context: NarrativeContext) -> list[str]:
        if context.has_location:
            return [
                context.location,
                f"{context.date_hint}的{context.location}",
                f"{context.location}这段{context.time_of_day}",
                f"{context.season}里的{context.location}",
            ]
        return [
            f"{context.date_hint}的{context.time_of_day}",
            f"这一段{context.time_of_day}",
            f"{context.season}里的这一页",
            "没有明确地名的这个片刻",
        ]

    @classmethod
    def _album_counter(cls, key: str) -> Counter:
        counter = cls._album_usage.get(key)
        if counter is None:
            counter = Counter()
            cls._album_usage[key] = counter
        return counter

    @staticmethod
    def _least_used(pool: list[str], usage: Counter, rng: random.Random) -> str:
        ranked = []
        for index, item in enumerate(pool):
            ranked.append((usage[item], rng.random(), index, item))
        ranked.sort()
        return ranked[0][3]

    @staticmethod
    def _first_clause(text: str) -> str:
        for sep in ("。", "；", "，", "："):
            if sep in text:
                return text.split(sep, 1)[0].strip()
        return text.strip()[:18]

    @classmethod
    def _unique_suffixes(cls, context: NarrativeContext) -> list[str]:
        return [
            f"它被留在{context.date_hint}的这一页里。",
            f"这也是{context.time_of_day}最容易被记住的部分。",
            f"{context.photo_count}张照片一起把这段气氛托住了。",
            f"于是{context.date_hint}有了自己的叙事落点。",
        ]

    @classmethod
    def _claim_unique(cls, text: str, history: set[str], suffixes: list[str]) -> str:
        candidate = cls._cleanup(text)
        if candidate not in history:
            history.add(candidate)
            return candidate
        stem = candidate.rstrip("。；， ")
        for suffix in suffixes:
            merged = cls._cleanup(f"{stem}，{suffix}")
            if merged not in history:
                history.add(merged)
                return merged
        index = 2
        while True:
            merged = cls._cleanup(f"{stem}（片段{index}）")
            if merged not in history:
                history.add(merged)
                return merged
            index += 1
