import json
import httpx
from typing import Dict, Any, List
import re

# Arabic-Indic numeral mapping
ARABIC_INDIC_MAP = str.maketrans('٠١٢٣٤٥٦٧٨٩', '0123456789')

NUMBER_WORDS = {
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
    "اثنين": 2,
    "إثنين": 2,
    "ثلاثة": 3,
    "اربعة": 4,
    "أربعة": 4,
    "خمسة": 5,
    "ستة": 6,
    "سبعة": 7,
    "ثمانية": 8,
    "تسعة": 9,
    "عشرة": 10,
}

class OllamaClient:
    def __init__(self, base_url: str = "http://localhost:11434"):
        self.base_url = base_url

    async def is_available(self) -> bool:
        """Quick health check against the Ollama server."""
        try:
            async with httpx.AsyncClient() as client:
                res = await client.get(f"{self.base_url}/api/tags", timeout=2.0)
                return res.status_code == 200
        except Exception:
            return False

    async def generate(self, model: str, prompt: str) -> str:
        """Calls the local Ollama API."""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.base_url}/api/generate",
                    json={
                        "model": model,
                        "prompt": prompt,
                        "stream": False,
                        "format": "json" # Ollama supports strict JSON format
                    },
                    timeout=30.0 # 30s timeout — 2B models can be slow on CPU
                )
                response.raise_for_status()
                return response.json().get("response", "{}")
            except Exception as e:
                print(f"Ollama generation failed: {e}")
                return "{}"

class MissionParser:
    def __init__(self, model_name: str = "gemma:2b"):
        self.model_name = model_name
        self.client = OllamaClient()
        self._ollama_available = None  # Cached availability check

    def status(self) -> Dict[str, Any]:
        return {
            "model": self.model_name,
            "ollama_available": bool(self._ollama_available),
            "mode": "llm" if self._ollama_available else "heuristic_fallback",
        }

    def _normalize_arabic_numerals(self, text: str) -> str:
        """Converts Arabic-Indic numerals (٠-٩) to Western numerals (0-9)."""
        return text.translate(ARABIC_INDIC_MAP)

    def _normalize_number_words(self, text: str) -> str:
        normalized = self._normalize_arabic_numerals(text)
        for word, value in NUMBER_WORDS.items():
            normalized = re.sub(rf'\b{re.escape(word.lower())}\b', str(value), normalized, flags=re.IGNORECASE)
        return normalized

    def _detect_pattern(self, lower_text: str) -> str:
        if any(kw in lower_text for kw in ["scan", "sweep", "search", "مسح", "تمشيط"]):
            return "lawn_mower"
        if any(kw in lower_text for kw in ["spiral", "close in", "converge", "حلزوني"]):
            return "spiral"
        if any(kw in lower_text for kw in ["secure", "surround", "perimeter", "تأمين", "محيط"]):
            return "perimeter"
        return "perimeter"

    def _fragment_has_action(self, text: str) -> bool:
        lower = text.lower()
        action_terms = [
            "attack", "strike", "secure", "defend", "protect", "recon", "observe", "scout", "scan",
            "search", "sweep", "patrol", "return", "recall", "bring", "rendezvous", "come to",
            " هجوم", "تأمين", "استطلاع", "مسح", "تمشيط", "عودة"
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
            "recon": ["recon", "reconnaissance", "observe", "استطلاع", "مراقبة", "راقب"],
            "scout": ["scout", "scan", "search", "sweep", "patrol", "تمشيط", "بحث", "مسح", "دورية"],
            "rendezvous": ["bring", "come to", "rendezvous", "meet", "link up"],
            "return": ["return", "recall", "come back", "rtb", "عودة", "ارجع", "رجوع"],
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
            "priority": priority,
            "pattern": pattern,
            "parser": "heuristic"
        }

    async def parse_intent(self, user_input: str) -> Dict[str, Any]:
        """
        Parses multi-lingual military jargon into a JSON structure.
        Falls back to pure heuristics if Ollama is unavailable.
        """
        # Check Ollama availability (cache the result for the session)
        if self._ollama_available is None:
            self._ollama_available = await self.client.is_available()
            if self._ollama_available:
                print("Ollama connected - using LLM-assisted parsing")
            else:
                print("Ollama unavailable - using heuristic-only parsing")

        parsed = None
        
        if self._ollama_available:
            prompt = f"""
            You are a Saudi military AI tactical parser. Extract the intent and target from the following command.
            Map Arabic terms to actions (e.g., تمشيط = scout, استطلاع = recon, تأمين = secure, هجوم = attack).
            Detect pattern as perimeter, lawn_mower, or spiral.
            If the target is the operator/current commander position ("me", "my location", "to me"), set target_reference to "operator" instead of inventing a place name.
            Output ONLY valid JSON in the following format:
            {{
                "action": "scout | recon | secure | attack | rendezvous | return",
                "target_zone": "name of the area or coordinates",
                "target_reference": "operator | none",
                "priority": "high | medium | low",
                "pattern": "perimeter | lawn_mower | spiral"
            }}
            Command: {user_input}
            """
            
            raw_response = await self.client.generate(self.model_name, prompt)
            
            try:
                parsed = json.loads(raw_response)
                if not isinstance(parsed, dict):
                    raise ValueError("Not a dictionary")
                # If Ollama nested it in an 'intent' key, flatten it
                if "intent" in parsed and isinstance(parsed["intent"], dict):
                    parsed = parsed["intent"]
                parsed["parser"] = "llm"
            except (json.JSONDecodeError, ValueError):
                print("Failed to parse LLM JSON, falling back to heuristics.")
                parsed = None

        # Use heuristic parser if LLM failed or unavailable
        if parsed is None:
            parsed = self._heuristic_parse(user_input)
            
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

        # Extract drone count from phrases like "send 3 drones", "deploy 4 units", "أرسل ٤ طائرات"
        count_match = re.search(
            r'(?:send|deploy|dispatch|make|go|bring|move|guide|أرسل|وجه|ابعث)\s+(\d+)\s+(?:drone|drones|unit|units|طائر|طائرات|وحد)',
            normalized_input
        )
        if count_match:
            parsed["drone_count"] = int(count_match.group(1))
        else:
            verb_count = re.search(
                r'(?:send|deploy|dispatch|make|go|bring|move|guide|أرسل|وجه|ابعث)\s+(\d+)\s+(?:to|at|near|towards|إلى|الى)',
                normalized_input
            )
            bare_count = re.match(r'^(\d+)\s+(?:to|at|near|towards|إلى|الى)', normalized_input)
            if verb_count:
                parsed["drone_count"] = int(verb_count.group(1))
            elif bare_count:
                parsed["drone_count"] = int(bare_count.group(1))

        if "drone_count" not in parsed and ("all" in lower_input or "الكل" in lower_input or "جميع" in lower_input):
            parsed["drone_count"] = 99  # Sentinel for "all available"

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
            # Try specific verb patterns first, then generic "to X" as fallback
            patterns = [
                r'(?:go to|head to|bring|move|guide|scout|secure|attack|target|towards)\s+(.+?)(?:$|\.|!| and|,)',
                r'(?:drones?|units?)\s+to\s+(.+?)(?:$|\.|!| and|,)',
                r'(?:إلى|الى)\s+(.+?)(?:$|\.|!| و|,)',
                r'\bto\s+(.+?)(?:$|\.|!| and|,)',
            ]
            for pattern in patterns:
                match = re.search(pattern, lower_input)
                if match:
                    extracted = match.group(1).strip()
                    # Filter out noise words that aren't locations
                    if extracted and extracted not in ["the", "a", "an", "my", "base"]:
                        parsed["target_zone"] = extracted
                        break
            
            # Final fallback: scan raw text for any known location name
            if parsed.get("target_zone") in ["unknown", "", None, "undefined"]:
                known_locations = [
                    "kafd", "airport", "imam university", "wadi hanifah", "kingdom centre",
                    "kingdom center", "al faisaliyah", "boulevard", "diriyah", "masmak",
                    "stadium", "king saud university", "national museum", "ministry of defense", "al nada",
                    "المطار", "جامعة الامام", "المركز المالي", "وادي حنيفة"
                ]
                # Check longest names first to avoid partial matches
                for loc in sorted(known_locations, key=len, reverse=True):
                    if loc in lower_input:
                        parsed["target_zone"] = loc
                        break
                else:
                    parsed["target_zone"] = "unknown"
                
        # Enforce action schema so it's never undefined
        if parsed.get("action") in ["unknown", "", None, "undefined"]:
            parsed["action"] = "scout"

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
