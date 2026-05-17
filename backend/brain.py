import json
from typing import Dict, Any, List
import re

try:
    from backend.llm_provider import LLMProviderError, OllamaProvider
except ImportError:
    from llm_provider import LLMProviderError, OllamaProvider

# Arabic-Indic numeral mapping
ARABIC_INDIC_MAP = str.maketrans('٠١٢٣٤٥٦٧٨٩', '0123456789')

NUMBER_WORDS = {
    "a": 1,
    "an": 1,
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "واحد": 1,
    "واحدة": 1,
    "اثنين": 2,
    "إثنين": 2,
    "اثنتين": 2,
    "إثنتين": 2,
    "طائرتين": 2,
    "بطائرتين": 2,
    "طائرتان": 2,
    "ثلاثة": 3,
    "ثلاث": 3,
    "بثلاث": 3,
    "اربعة": 4,
    "أربعة": 4,
    "اربع": 4,
    "أربع": 4,
    "بأربع": 4,
    "خمسة": 5,
    "خمس": 5,
    "بخمس": 5,
    "ستة": 6,
    "سبعة": 7,
    "ثمانية": 8,
    "تسعة": 9,
    "عشرة": 10,
}

FLEET_SIZE = 13
KNOWN_TARGET_ALIASES = [
    ("ministry of defense", "ministry of defense"),
    ("the airport", "the airport"),
    ("national museum", "national museum"),
    ("wadi hanifah", "wadi hanifah"),
    ("king saud university", "king saud university"),
    ("imam university", "imam university"),
    ("kingdom centre", "kingdom centre"),
    ("kingdom center", "kingdom center"),
    ("al faisaliyah", "al faisaliyah"),
    ("al nada", "al nada"),
    ("stadium", "stadium"),
    ("airport", "airport"),
    ("boulevard", "boulevard"),
    ("diriyah", "diriyah"),
    ("masmak", "masmak"),
    ("kafd", "kafd"),
    ("وزارة الدفاع", "وزارة الدفاع"),
    ("المتحف الوطني", "المتحف الوطني"),
    ("المركز المالي", "المركز المالي"),
    ("وادي حنيفة", "وادي حنيفة"),
    ("حي الندى", "حي الندى"),
    ("الدرعية", "الدرعية"),
    ("المطار", "المطار"),
    ("الملعب", "الملعب"),
    ("جامعة الامام", "جامعة الامام"),
]
AMBIGUOUS_TARGETS = {"there", "over there", "هناك", "هنالك"}

class MissionParser:
    def __init__(self, model_name: str | None = None):
        self.provider = OllamaProvider(model_name=model_name)
        self.model_name = self.provider.model_name
        self._ollama_available = None  # Backward-compatible test override.
        self._fallback_active = True
        self._last_parser = "heuristic"
        self._last_error = None

    def status(self) -> Dict[str, Any]:
        provider_status = self.provider.status()
        return {
            **provider_status,
            "model": self.model_name,
            "ollama_available": bool(provider_status.get("ollama_running")),
            "llm_online": bool(provider_status.get("llm_online")),
            "fallback_active": self._fallback_active,
            "mode": "llm" if not self._fallback_active and provider_status.get("llm_online") else "heuristic_fallback",
            "last_parser": self._last_parser,
            "last_error": self._last_error or provider_status.get("last_error"),
        }

    async def refresh_status(self) -> Dict[str, Any]:
        await self.provider.refresh_status(force=True)
        return self.status()

    def _normalize_arabic_numerals(self, text: str) -> str:
        """Converts Arabic-Indic numerals (٠-٩) to Western numerals (0-9)."""
        return text.translate(ARABIC_INDIC_MAP)

    def _normalize_number_words(self, text: str) -> str:
        normalized = self._normalize_arabic_numerals(text)
        for word, value in NUMBER_WORDS.items():
            normalized = re.sub(rf'\b{re.escape(word.lower())}\b', str(value), normalized, flags=re.IGNORECASE)
        return normalized

    def _detect_pattern(self, lower_text: str) -> str:
        if any(kw in lower_text for kw in ["spiral", "close in", "converge", "حلزوني"]):
            return "spiral"
        if any(kw in lower_text for kw in ["secure", "surround", "perimeter", "تأمين", "محيط"]):
            return "perimeter"
        if any(kw in lower_text for kw in ["scan", "sweep", "search", "مسح", "تمشيط", "مشط"]):
            return "lawn_mower"
        return "perimeter"

    def _known_target(self, lower_text: str) -> str | None:
        for needle, canonical in sorted(KNOWN_TARGET_ALIASES, key=lambda item: len(item[0]), reverse=True):
            if needle in lower_text:
                return canonical
        return None

    def _clean_target_zone(self, target_zone: str | None, lower_text: str) -> str:
        if not target_zone:
            return "unknown"
        target = target_zone.strip().strip(" .،,!")
        known = self._known_target(lower_text)
        if known and (known in target or target in known or known in lower_text):
            return known

        target = re.sub(r'\s+(?:for|with|using)\s+.+$', '', target, flags=re.IGNORECASE)
        target = re.sub(r'\s+(?:لمسح|ب|بـ)\s*.+$', '', target)
        target = re.sub(r'^(?:the\s+)?base$', 'unknown', target, flags=re.IGNORECASE)
        if target.lower() in AMBIGUOUS_TARGETS:
            return "unknown"
        return target or "unknown"

    def _extract_drone_count(self, normalized_input: str, lower_input: str, explicit_drones: List[str]) -> int | None:
        if re.search(r'(?:ب|بـ)?طائرت(?:ين|ان)\b', lower_input):
            return 2
        if re.search(r'(?:ب|بـ)?طائرة\b', lower_input):
            return 1

        count_patterns = [
            r'(?:send|deploy|dispatch|make|go|bring|move|guide|أرسل|وجه|ابعث|أحضر|ارسل)\s+(\d+)\s+(?:drone|drones|unit|units|طائرة|طائرات|طائر|وحدة|وحدات)',
            r'(?:send|deploy|dispatch|make|go|bring|move|guide|أرسل|وجه|ابعث|أحضر|ارسل)\s+(?:drone|drones|unit|units|طائرة|طائرات|طائر|وحدة|وحدات)\s+(\d+)',
            r'(?:with|using|ب|بـ)\s*(\d+)\s+(?:drone|drones|unit|units|طائرة|طائرات|طائر|وحدة|وحدات)',
            r'(?:drone|drones|unit|units|طائرة|طائرات|طائر|وحدة|وحدات)\s+(\d+)',
            r'(?:send|deploy|dispatch|make|go|bring|move|guide|أرسل|وجه|ابعث|أحضر|ارسل)\s+(\d+)\s+(?:to|at|near|towards|إلى|الى)',
            r'^(\d+)\s+(?:to|at|near|towards|إلى|الى)',
            r'\b(\d+)\s+(?:drone|drones|unit|units|طائرة|طائرات|طائر|وحدة|وحدات)\b',
        ]
        for pattern in count_patterns:
            match = re.search(pattern, normalized_input)
            if match:
                return int(match.group(1))

        if explicit_drones:
            return len(explicit_drones)
        if "all" in lower_input or "الكل" in lower_input or "جميع" in lower_input:
            return FLEET_SIZE
        return None

    def _fragment_has_action(self, text: str) -> bool:
        lower = text.lower()
        action_terms = [
            "attack", "strike", "secure", "defend", "protect", "recon", "observe", "scout", "scan",
            "search", "sweep", "patrol", "return", "recall", "bring", "rendezvous", "come to",
            " هجوم", "تأمين", "استطلاع", "استطلع", "مسح", "تمشيط", "مشط", "عودة", "أحضر", "أعد"
        ]
        return any(term in lower for term in action_terms)

    def _split_compound_fragments(self, user_input: str) -> List[str]:
        parts = [part.strip() for part in re.split(r'\s+(?:and|و)\s+|,\s+', user_input) if part.strip()]
        if len(parts) <= 1:
            return [user_input.strip()]

        fragments = [parts[0]]
        for part in parts[1:]:
            normalized = self._normalize_arabic_numerals(part.lower())
            starts_with_count = re.match(r'^\d+\s+(?:to|at|near|towards|إلى|الى)\b', normalized)
            has_target_preposition = re.search(r'\b(?:to|at|near|towards)\b|(?:إلى|الى)', normalized)
            if starts_with_count or has_target_preposition:
                fragments.append(part)
            else:
                fragments[-1] = f"{fragments[-1]} and {part}"

        return fragments

    def _heuristic_parse(self, user_input: str) -> Dict[str, Any]:
        """
        Pure heuristic parser — no LLM needed. Works offline.
        Maps keywords to actions and extracts targets via regex.
        """
        lower = user_input.lower()
        normalized = self._normalize_arabic_numerals(lower)
        
        # Action detection via keyword matching
        action = "scout"  # default
        action_keywords = {
            "attack": ["attack", "strike", "هجوم", "اضرب", "ضرب"],
            "secure": ["secure", "defend", "protect", "تأمين", "حماية", "أمّن"],
            "recon": ["recon", "reconnaissance", "observe", "استطلاع", "استطلع", "مراقبة", "راقب"],
            "scout": ["scout", "scan", "search", "sweep", "patrol", "تمشيط", "مشط", "بحث", "مسح", "دورية"],
            "rendezvous": ["bring", "come to", "rendezvous", "meet", "link up", "أحضر"],
            "return": ["return", "recall", "come back", "rtb", "عودة", "ارجع", "رجوع", "أعد"],
        }
        for act, keywords in action_keywords.items():
            if any(kw in lower for kw in keywords):
                action = act
                break

        # Priority detection
        priority = "medium"
        if any(w in lower for w in ["urgent", "critical", "emergency", "عاجل", "طوارئ", "حرج"]):
            priority = "high"
        elif any(w in lower for w in ["low priority", "when possible", "غير عاجل"]):
            priority = "low"

        pattern = self._detect_pattern(lower)
        
        return {
            "action": action,
            "target_zone": "unknown",
            "target_reference": None,
            "priority": priority,
            "pattern": pattern,
            "needs_confirmation": True,
            "confidence": 0.62,
            "clarifying_question": None,
            "parser": "heuristic"
        }

    def _coerce_llm_intent(self, parsed: Dict[str, Any]) -> Dict[str, Any]:
        allowed_actions = {"scout", "recon", "secure", "attack", "rendezvous", "return"}
        allowed_priorities = {"high", "medium", "low"}
        allowed_patterns = {"perimeter", "lawn_mower", "spiral"}

        action = str(parsed.get("action") or "scout").lower().strip()
        priority = str(parsed.get("priority") or "medium").lower().strip()
        pattern = str(parsed.get("pattern") or "perimeter").lower().strip()
        target_reference = parsed.get("target_reference")
        if isinstance(target_reference, str):
            target_reference = target_reference.lower().strip()
            if target_reference in ("none", "null", ""):
                target_reference = None

        try:
            confidence = float(parsed.get("confidence", 0.75))
        except (TypeError, ValueError):
            confidence = 0.75

        result = {
            "action": action if action in allowed_actions else "scout",
            "target_zone": parsed.get("target_zone") or "unknown",
            "target_reference": target_reference if target_reference == "operator" else None,
            "priority": priority if priority in allowed_priorities else "medium",
            "pattern": pattern if pattern in allowed_patterns else "perimeter",
            "needs_confirmation": bool(parsed.get("needs_confirmation", True)),
            "confidence": round(max(0.0, min(confidence, 1.0)), 2),
            "clarifying_question": parsed.get("clarifying_question"),
        }

        if parsed.get("drone_count") is not None:
            try:
                result["drone_count"] = max(1, int(parsed["drone_count"]))
            except (TypeError, ValueError):
                pass
        if parsed.get("area_size_m") is not None:
            try:
                result["area_size_m"] = max(25, int(parsed["area_size_m"]))
            except (TypeError, ValueError):
                pass
        if isinstance(parsed.get("target_coords"), dict):
            try:
                result["target_coords"] = {
                    "lat": float(parsed["target_coords"]["lat"]),
                    "lng": float(parsed["target_coords"]["lng"]),
                }
            except (KeyError, TypeError, ValueError):
                pass
        return result

    async def parse_intent(self, user_input: str) -> Dict[str, Any]:
        """
        Parses multi-lingual military jargon into a JSON structure.
        Falls back to pure heuristics if Ollama is unavailable.
        """
        parsed = None
        if self._ollama_available is False:
            status = {"llm_online": False}
        else:
            status = await self.provider.refresh_status()
            self._ollama_available = bool(status.get("ollama_running"))
        
        if status.get("llm_online"):
            prompt = f"""
            You are Shepherd-AI's tactical intent parser. Extract bounded mission intent from the command.
            You do not fly drones. You only return structured JSON intent for a deterministic planner.
            Map Arabic terms to actions (e.g., تمشيط = scout, استطلاع = recon, تأمين = secure, هجوم = attack).
            Detect pattern as perimeter, lawn_mower, or spiral.
            If the target is the operator/current commander position ("me", "my location", "to me"), set target_reference to "operator" and target_zone to "operator_current_position".
            Do not invent coordinates. If a place name may be ambiguous, keep the place name and set needs_confirmation to true.
            Output ONLY valid JSON in the following format:
            {{
                "action": "scout | recon | secure | attack | rendezvous | return",
                "target_zone": "name of the area, coordinates, or operator_current_position",
                "target_reference": "operator or null",
                "drone_count": 1,
                "priority": "high | medium | low",
                "pattern": "perimeter | lawn_mower | spiral",
                "area_size_m": 200,
                "needs_confirmation": true,
                "confidence": 0.86,
                "clarifying_question": "short question or null"
            }}
            Command: {user_input}
            """
            
            try:
                raw_response = await self.provider.generate_json(prompt)
            except LLMProviderError as exc:
                self._last_error = str(exc)
                raw_response = "{}"
            
            try:
                parsed = json.loads(raw_response)
                if not isinstance(parsed, dict):
                    raise ValueError("Not a dictionary")
                # If Ollama nested it in an 'intent' key, flatten it
                if "intent" in parsed and isinstance(parsed["intent"], dict):
                    parsed = parsed["intent"]
                parsed = self._coerce_llm_intent(parsed)
                parsed["parser"] = "llm"
                self._fallback_active = False
                self._last_parser = "llm"
                self._last_error = None
            except (json.JSONDecodeError, ValueError):
                print("Failed to parse LLM JSON, falling back to heuristics.")
                parsed = None

        # Use heuristic parser if LLM failed or unavailable
        if parsed is None:
            parsed = self._heuristic_parse(user_input)
            self._fallback_active = True
            self._last_parser = "heuristic"
            
        # ─── UNIVERSAL ENRICHMENT ─────────────────────────────────────────────
        # These run regardless of parser to guarantee extraction
        
        lower_input = user_input.lower()
        normalized_input = self._normalize_number_words(lower_input)
        parsed["pattern"] = self._detect_pattern(lower_input)

        operator_reference = re.search(
            r'\b(?:to|at|near|towards)\s+(?:me|my position|my location|my current position|the operator|operator|commander)\b|(?:إلى|الى)\s+(?:موقعي|مكاني|القائد)',
            normalized_input,
        )
        if operator_reference or parsed.get("target_reference") == "operator":
            parsed["target_reference"] = "operator"
            parsed["target_zone"] = "operator_current_position"
        
        # Extract explicit drones — includes all fleet members
        known_drones = [
            "alpha-1", "alpha-2", "alpha-3", "alpha-4", "alpha-5",
            "beta-1", "beta-2", "beta-3",
            "gamma-1", "gamma-2", "gamma-3",
            "delta-1", "delta-2"
        ]
        explicit_drones = [d for d in known_drones if d in lower_input]
        if explicit_drones:
            parsed["explicit_drones"] = explicit_drones

        drone_count = self._extract_drone_count(normalized_input, lower_input, explicit_drones)
        if drone_count is not None:
            parsed["drone_count"] = drone_count

        area_match = re.search(r'(\d+)\s*(?:m|meters?|meter|متر)', normalized_input)
        if area_match:
            parsed["area_size_m"] = int(area_match.group(1))

        coord_match = re.search(r'(-?\d{1,2}\.\d+)\s*,\s*(-?\d{1,3}\.\d+)', normalized_input)
        if coord_match:
            parsed["target_coords"] = {
                "lat": float(coord_match.group(1)),
                "lng": float(coord_match.group(2)),
            }
            parsed["target_zone"] = "coordinates"
            
        # Dynamically extract target zone using regex if parser missed it
        if parsed.get("target_reference") != "operator" and parsed.get("target_zone") in ["unknown", "", None, "undefined"]:
            known_target = self._known_target(lower_input)
            if known_target:
                parsed["target_zone"] = known_target

            # Try specific verb patterns first, then generic "to X" as fallback
            patterns = [
                r'(?:send|deploy|dispatch|bring|move|guide)\s+(?:\d+\s+)?(?:drones?|units?)?\s*(?:to|at|near|towards)\s+(.+?)(?:$|\.|!| and|,)',
                r'(?:go to|head to|scout|secure|attack|target|towards)\s+(.+?)(?:$|\.|!| and|,)',
                r'(?:recon|observe|secure|search)\s+(?:the\s+)?(.+?)(?:\s+with\s+\d+\s+drones?|$|\.|!| and|,)',
                r'(?:drones?|units?)\s+(?:to|at|near|towards)\s+(.+?)(?:$|\.|!| and|,)',
                r'(?:استطلع|راقب|أمّن|امن|مشط|نفذ)\s+(.+?)(?:\s+(?:ب|بـ)\s*\d+\s+طائرات|$|\.|!| و|،)',
                r'(?:حول)\s+(.+?)(?:\s+(?:ب|بـ)\s*\d+\s+طائرات|$|\.|!| و|،)',
                r'(?:إلى|الى)\s+(.+?)(?:$|\.|!| و|,)',
                r'\bto\s+(.+?)(?:$|\.|!| and|,)',
            ]
            if parsed.get("target_zone") in ["unknown", "", None, "undefined"]:
                for pattern in patterns:
                    match = re.search(pattern, normalized_input)
                    if match:
                        extracted = self._clean_target_zone(match.group(1), lower_input)
                        if extracted not in ["the", "a", "an", "my", "base", "unknown"]:
                            parsed["target_zone"] = extracted
                            break

        if parsed.get("target_reference") != "operator":
            parsed["target_zone"] = self._clean_target_zone(parsed.get("target_zone"), lower_input)

        if parsed.get("action") == "return":
            parsed["target_zone"] = "home"
            parsed["pattern"] = "return_to_launch"
            parsed["priority"] = "high"
            if "drone_count" not in parsed:
                parsed["drone_count"] = FLEET_SIZE
        elif "drone_count" not in parsed:
            parsed["drone_count"] = 1
                
        # Enforce action schema so it's never undefined
        if parsed.get("action") in ["unknown", "", None, "undefined"]:
            parsed["action"] = "scout"

        parsed.setdefault("target_reference", None)
        parsed.setdefault("needs_confirmation", True)
        parsed.setdefault("confidence", 0.62 if parsed.get("parser") == "heuristic" else 0.75)
        parsed.setdefault("clarifying_question", None)
        if parsed.get("target_zone") in ["unknown", "", None, "undefined"] and parsed.get("action") != "return":
            parsed["needs_confirmation"] = True
            parsed["confidence"] = min(float(parsed.get("confidence", 0.5)), 0.5)
            parsed["clarifying_question"] = "Which target zone should Shepherd-AI resolve for this mission?"
        elif parsed.get("action") != "return" and not parsed.get("clarifying_question"):
            target = parsed.get("target_zone") or "the selected target"
            parsed["clarifying_question"] = f"Is {target} the correct target for this mission?"

        return parsed

    async def parse_compound_intent(self, user_input: str) -> List[Dict[str, Any]]:
        fragments = self._split_compound_fragments(user_input)
        intents = []
        inherited_action = None
        inherited_pattern = None

        for fragment in fragments:
            has_action = self._fragment_has_action(fragment)
            intent = await self.parse_intent(fragment)
            if inherited_action and not has_action:
                intent["action"] = inherited_action
            if inherited_pattern and not has_action and intent.get("pattern") == "perimeter":
                intent["pattern"] = inherited_pattern

            inherited_action = intent.get("action", inherited_action)
            inherited_pattern = intent.get("pattern", inherited_pattern)
            intent["fragment"] = fragment
            intents.append(intent)

        return intents
