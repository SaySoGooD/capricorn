"""Чистка ответов нейросети перед озвучкой: без «мыслей вслух», повторов и третьего лица."""
import difflib
import re


class LlmText:
    """Чистка ответов модели перед озвучкой. Без состояния — методы статические, шаблоны в атрибутах класса."""

    FOREIGN = re.compile(r"[　-鿿가-힯＀-￯]+")

    THIRD_PERSON = re.compile(r"(одн(а|ой|у|у) прекрасн(ая|ой|ую) (я|мне|меня|мной))", re.IGNORECASE)

    SELF_TALK = re.compile(r"\bя\s*[—–-]?\s*капри\b|меня зовут капри|\bкапри (здесь|тут|на связи)|^капри\b|"
                           r"\bне (просто |какой-то |обычный |обычная )?(бот|ии|программ\w*|голос в)|"
                           r"сильнее (любого |обычного )?(бот|ии)|(называ|зови|счита)\w* меня (просто )?(бот|ии)|"
                           r"каприкорн", re.IGNORECASE)
    ASKED_SELF = re.compile(r"кто ты|как тебя зовут|тво[её] имя|\bии\b|бот|программ|нейросет|о себе|про себя|"
                            r"ты кто|кто такая")

    # рассуждения без меток: «думающие» модели (qwen3:4b = qwen3:4b-thinking) пишут их прямо в ответ
    REASONING = re.compile(r"^\W*(okay|ok,|alright|let me|the user|first,|хорошо,? (пользователь|мне|нужно|давай)|"
                           r"пользователь (спрашива|хочет|проси|пиш|говор)|мне нужно|нужно ответить|"
                           r"итак,? (пользователь|мне|нужно)|сначала (мне |нужно |надо )|давайте? (подума|разбер))",
                           re.IGNORECASE)

    @staticmethod
    def drop_third_person(answer):
        """Страховка поверх промпта: Капри не говорит о себе в третьем лице. Такие предложения
        выкидываем целиком (чтобы не ломать согласование глаголов), а если других нет — меняем на «я»."""
        sentences = re.split(r"(?<=[.!?…])\s+", answer)
        clean = [s for s in sentences if not LlmText.THIRD_PERSON.search(s)]
        if clean:
            return " ".join(clean)
        return LlmText.THIRD_PERSON.sub("я", answer)

    @staticmethod
    def naturalize(answer, question, recent):
        """Страховка поверх промпта — чтобы Капри звучала как собеседница, а не как персонаж,
        зацикленный на своих чертах: без самопредставлений и «я не бот» без повода, без «чумба» в каждой фразе."""
        parts = [p for p in re.split(r"(?<=[.!?…])\s+", answer) if p.strip()]
        if not LlmText.ASKED_SELF.search(question.lower()):
            parts = [p for p in parts if not LlmText.SELF_TALK.search(p)] or parts
        parts = [p for p in parts if not re.fullmatch(r"\W*чумба\W*", p.lower())] or parts
        text = " ".join(parts)
        # «чумба» — не чаще раза на несколько ответов
        allow = not any("чумба" in r.lower() for r in recent[-3:])
        used = []

        def drop(m):
            if allow and not used:
                used.append(1)
                return m.group(0)
            return "," if m.group(1) and m.group(2) else ""
        text = re.sub(r"(,\s*)?\bчумба\b(\s*,)?", drop, text, flags=re.IGNORECASE)
        text = re.sub(r"\s+([,.!?…])", r"\1", text)
        text = re.sub(r"(^|[.!?…]\s+)[,\s]+", r"\1", text)
        text = re.sub(r"(^|[.!?…]\s+)(\w)", lambda m: m.group(1) + m.group(2).upper(), text)
        return text.strip() or answer

    @staticmethod
    def _key(sentence):
        return re.sub(r"[^\w ]", "", sentence.lower().replace("ё", "е")).strip()

    @staticmethod
    def drop_repeats(answer, history):
        """Маленькая модель залипает на своих же фразах из истории («Вздыхаю…», «Иди, проверяй…»):
        выкидываем предложения, которые уже звучали (или почти так же) в прошлых ответах."""
        previous = [LlmText._key(s) for m in history if m["role"] == "assistant"
                    for s in re.split(r"(?<=[.!?…])\s+", m["content"])]
        previous = [p for p in previous if len(p) >= 8]
        kept = []
        for s in re.split(r"(?<=[.!?…])\s+", answer):
            k = LlmText._key(s)
            if re.match(r"(вздыха|вздох)", k):
                continue
            if len(k) >= 8 and any(k == p or difflib.SequenceMatcher(None, k, p).ratio() > 0.8 for p in previous):
                continue
            kept.append(s)
        return " ".join(kept) or answer

    @staticmethod
    def strip_reasoning(text):
        """Убирает «мысли вслух»: блоки <think>…</think>, хвост до одинокого </think>
        (у новых Qwen открывающей метки нет) и незакрытый <think> до конца."""
        text = re.sub(r"<think>.*?</think>", "", text, flags=re.S)
        if "</think>" in text:
            text = text.rsplit("</think>", 1)[1]
        return re.sub(r"<think>.*", "", text, flags=re.S).strip()
