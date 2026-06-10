import json
import logging
import re

from openai import OpenAI

from app.core.config import settings

logger = logging.getLogger(__name__)


class MiniMaxLLMService:
    def __init__(self) -> None:
        self._client: OpenAI | None = None
        self.model = settings.minimax_llm_model

    @property
    def client(self) -> OpenAI:
        if self._client is None:
            self._client = OpenAI(
                api_key=settings.minimax_api_key,
                base_url=f"{settings.minimax_base_url.rstrip('/')}/v1",
            )
        return self._client

    def reset(self) -> None:
        self._client = None

    def _chat(self, system: str, user: str, max_tokens: int = 8192, temperature: float = 0.7) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            max_completion_tokens=max_tokens,
            temperature=temperature,
        )
        content = response.choices[0].message.content or ""
        return content.strip()

    @staticmethod
    def _strip_markdown_fence(text: str) -> str:
        text = text.strip()
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
            text = re.sub(r"\s*```\s*$", "", text)
        return text.strip()

    @classmethod
    def _extract_json(cls, text: str) -> dict:
        """Parse the first JSON object from LLM output (tolerates trailing text / multiple blocks)."""
        text = cls._strip_markdown_fence(text)
        decoder = json.JSONDecoder()

        # Try raw_decode from each '{' position (handles prefix text)
        search_from = 0
        last_error: Exception | None = None
        while search_from < len(text):
            start = text.find("{", search_from)
            if start < 0:
                break
            try:
                data, end = decoder.raw_decode(text, start)
                if isinstance(data, dict):
                    if end < len(text) and text[end:].strip():
                        logger.warning(
                            "LLM JSON had trailing content after char %d, ignored: %s",
                            end,
                            text[end : end + 200],
                        )
                    return data
            except json.JSONDecodeError as e:
                last_error = e
                search_from = start + 1
                continue
            search_from = start + 1

        # Fallback: greedy block inside markdown / mixed content
        match = re.search(r"\{[\s\S]*\}", text)
        if match:
            try:
                data, _ = decoder.raw_decode(match.group(), 0)
                if isinstance(data, dict):
                    return data
            except json.JSONDecodeError as e:
                last_error = e

        preview = text[:800] + ("..." if len(text) > 800 else "")
        raise ValueError(
            f"LLM response does not contain valid JSON: {last_error}. Preview: {preview}"
        )

    def generate_script_and_storyboard(
        self,
        prompt: str,
        theme: str | None,
        style: str | None,
        audience: str | None,
        script_direction: str | None,
        segment_count: int,
        segment_duration_sec: int,
    ) -> dict:
        system = """你是一位专业的短视频编剧和分镜师。请根据用户需求生成完整的短视频脚本，并拆分为固定数量的分镜片段。

【重要】只输出一个 JSON 对象，不要输出 markdown 代码块，不要输出任何解释、注释或第二个 JSON。
JSON 结构如下：
{
  "title": "视频标题",
  "total_duration_sec": 180,
  "segment_duration_sec": 6,
  "segment_count": 30,
  "global_style": "整体视觉风格描述（写实/电影感/纪录片等）",
  "setting_anchor": "从用户需求提取的固定场景锚点（英文），如 zoo outdoor enclosure with baby monkeys playing",
  "setting_keywords": ["必须从用户描述提取的英文关键词，如 zoo", "monkey", "enclosure"],
  "segments": [
    {
      "index": 1,
      "duration_sec": 6,
      "narration": "旁白文案（6秒约15-20个中文字）",
      "subtitle": "字幕文案（可与旁白相同或精简）",
      "shot_type": "wide | medium | close-up | aerial | tracking 之一",
      "visual_description": "本段画面内容（中文，与其他段必须明显不同）",
      "start_visual_description": "本段第一帧画面（第1段必填；后续段描述如何从上段末帧自然延续但视角/主体有变化）",
      "camera_movement": "运镜：必须包含具体动作，如 slow dolly in / pan left / crane up / orbit / handheld follow",
      "motion_in_shot": "镜头内动态：人物走动、车流、霓虹闪烁、云层移动等，禁止静态定格画面",
      "scene_prompt": "英文视频生成 prompt：描述起止状态、光影、材质、景深，强调 6 秒内有可见变化",
      "end_visual_description": "本段最后一帧画面（用于与下一段衔接）",
      "transition_to_next": "与下一段的转场方式：cut | dissolve | match-cut | whip-pan 及具体衔接逻辑"
    }
  ]
}

【分镜硬性规则 — 必须全部满足】
1. segments 数组长度必须等于 segment_count
2. 每段旁白字数适配 duration_sec（6 秒约 15–20 字）
3. 首段强钩子，末段总结/号召
4. **每段必须是不同镜头**：景别（wide/medium/close-up/aerial）不得连续两段完全相同
5. **每段 visual_description / scene_prompt 不得重复同一场景描述**；应呈现「同一主题下的不同视角/不同主体/不同时间段」
6. **每段必须有 motion_in_shot 和 camera_movement**，确保 6 秒内画面有运镜和主体动态，禁止「静止单帧」式描述
7. scene_prompt 使用英文，适合 AI 视频生成；需写明：opening state → mid action → ending state
8. end_visual_description 描述该段最后一帧；下一段 start_visual_description 与之衔接但**景别或焦点必须变化**
9. transition_to_next 说明段间转场，让成片像真实剪辑而非两张静态图拼接
10. 即使用户只给一句话，也要自动扩展为多镜头叙事（建立镜头 → 细节/动作 → 情绪/总结）
11. **setting_anchor 与 setting_keywords 必须从用户输入提取，所有片段的 scene_prompt 必须包含 setting_anchor 及全部 setting_keywords**
12. **禁止更换用户指定的地点/场景/主体**（如用户说动物园，所有片段必须在 zoo/enclosure 内，不得变成森林、家里、城市街头等）
13. 每段 scene_prompt 开头必须重复 setting_anchor，再描述该段独有镜头

scene_prompt 英文写作模板（每段都应类似）：
"[setting_anchor]. [shot type], [subject action in same setting], [opening frame]. Camera [movement] over 6 seconds. [motion in shot]. [lighting and mood]. Ending on [end frame description]. Must remain in the user-specified location. Cinematic, photorealistic, natural motion."
"""

        user_parts = [
            f"用户方案：{prompt}",
            f"片段数量：{segment_count}，每段 {segment_duration_sec} 秒",
            "【硬性约束】用户指定的地点、场景、主体（如动物园、小猴子）不得更改或替换；所有片段必须发生在同一用户描述的场景内。",
        ]
        if theme:
            user_parts.append(f"主题：{theme}")
        if style:
            user_parts.append(f"风格：{style}")
        if audience:
            user_parts.append(f"受众：{audience}")
        if script_direction:
            user_parts.append(f"脚本方向：{script_direction}")

        user_msg = "\n".join(user_parts)
        raw = self._chat(system, user_msg, max_tokens=16384, temperature=0.5)
        logger.info("[MiniMax LLM] script response length=%d preview=%s", len(raw), raw[:300])

        try:
            data = self._extract_json(raw)
        except ValueError:
            logger.warning("[MiniMax LLM] JSON parse failed, retrying with strict prompt")
            raw = self._chat(
                system + "\n上次输出格式有误。请仅返回一个合法 JSON 对象，首尾不要有任何其他字符。",
                user_msg,
                max_tokens=16384,
            )
            logger.info("[MiniMax LLM] retry response length=%d preview=%s", len(raw), raw[:300])
            data = self._extract_json(raw)

        segments = data.get("segments", [])
        if len(segments) != segment_count:
            raise ValueError(
                f"Expected {segment_count} segments, got {len(segments)}"
            )
        for seg in segments:
            logger.info(
                "[MiniMax LLM] storyboard seg=%s | shot=%s | scene_prompt=%s",
                seg.get("index"),
                seg.get("shot_type", "-"),
                seg.get("scene_prompt", ""),
            )
        data = self.enforce_setting_anchor(data, prompt)
        return data

    @staticmethod
    def enforce_setting_anchor(script_data: dict, user_prompt: str) -> dict:
        """Ensure every segment scene_prompt anchors to user-specified setting."""
        anchor = (script_data.get("setting_anchor") or "").strip()
        keywords: list[str] = script_data.get("setting_keywords") or []

        if not anchor:
            anchor = user_prompt.strip()

        if not keywords and anchor:
            if any("\u4e00" <= c <= "\u9fff" for c in anchor):
                keywords = [anchor]
            else:
                keywords = [w for w in anchor.replace(",", " ").split() if len(w) > 2][:8]

        script_data["setting_anchor"] = anchor
        script_data["setting_keywords"] = keywords

        prefix = anchor
        if keywords:
            kw = ", ".join(keywords[:8])
            prefix = f"{anchor}. Required elements: {kw}"

        def _anchor_present(sp: str) -> bool:
            sp_lower = sp.lower()
            if anchor in sp or anchor.lower() in sp_lower:
                return True
            return any(k in sp or k.lower() in sp_lower for k in keywords)

        for seg in script_data.get("segments", []):
            sp = (seg.get("scene_prompt") or "").strip()
            if not sp or not _anchor_present(sp):
                seg["scene_prompt"] = f"{prefix}. {sp}" if sp else prefix
                logger.info(
                    "[MiniMax LLM] enforced setting on seg=%s anchor=%s",
                    seg.get("index"), anchor[:60],
                )
        return script_data


llm_service = MiniMaxLLMService()
