"""
MATHS OVERLOAD: ULTIMATE EDITION
================================

A large, single-file Pygame maths game.

Features
--------
* Animated main menu and scene transitions
* Campaign, Survival, Time Attack, Practice and Endless modes
* Procedural arithmetic, fractions, powers, roots, algebra,
  geometry, trigonometry, logarithms, probability and calculus
* XP, levels, coins, achievements, streaks and unlocks
* Boss encounters, shields, hints, skips and double-score boosts
* Persistent profile, settings, statistics and leaderboard
* Particle effects, floating text, screen shake and sound hooks
* Pause screen, settings screen, help screen and results screen

Install:
    python -m pip install pygame

Run:
    python maths_overload_ultimate.py

Controls:
    Mouse: menus and answers
    1-4: answer choices
    Enter: submit typed answer / continue
    Escape: pause / return
    H: use a hint (when available)
    S: skip (when available)

This project intentionally keeps the game in one file so it is easy
to study, edit and extend.  The code is organized into sections and
classes rather than relying on external assets.
"""

from __future__ import annotations

import json
import math
import os
import random
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Optional

import pygame


# ============================================================================
# 01. CONFIGURATION
# ============================================================================

class Config:
    """Central place for screen, timing, scoring and file settings."""

    TITLE = "MATHS OVERLOAD: ULTIMATE EDITION"
    WIDTH = 1280
    HEIGHT = 800
    FPS = 60

    DATA_DIR = Path("maths_overload_data")
    SAVE_FILE = DATA_DIR / "profile.json"
    BACKUP_FILE = DATA_DIR / "profile_backup.json"

    QUESTION_TIME = 22.0
    BOSS_QUESTION_TIME = 18.0
    TRANSITION_TIME = 0.22
    PARTICLE_LIMIT = 350

    STARTING_LIVES = 3
    STARTING_COINS = 0
    XP_PER_LEVEL = 500

    COLORS = {
        "background": (13, 17, 31),
        "panel": (24, 31, 53),
        "panel_light": (34, 44, 72),
        "white": (240, 245, 255),
        "muted": (151, 164, 190),
        "cyan": (68, 220, 235),
        "blue": (76, 130, 255),
        "purple": (163, 104, 255),
        "pink": (255, 94, 174),
        "green": (77, 220, 145),
        "yellow": (255, 205, 76),
        "orange": (255, 145, 70),
        "red": (255, 82, 100),
        "dark": (8, 11, 21),
    }

    DIFFICULTIES = {
        "Beginner": {"number": 12, "time": 28, "points": 80},
        "Easy": {"number": 30, "time": 25, "points": 100},
        "Normal": {"number": 70, "time": 22, "points": 125},
        "Hard": {"number": 180, "time": 19, "points": 160},
        "Expert": {"number": 500, "time": 16, "points": 210},
        "Master": {"number": 1500, "time": 14, "points": 280},
        "Insane": {"number": 5000, "time": 12, "points": 360},
        "Nightmare": {"number": 15000, "time": 10, "points": 500},
        "Legend": {"number": 50000, "time": 9, "points": 700},
        "Impossible": {"number": 100000, "time": 8, "points": 1000},
    }

    MODES = [
        "Campaign",
        "Survival",
        "Time Attack",
        "Practice",
        "Endless",
    ]


# ============================================================================
# 02. GENERAL HELPERS
# ============================================================================

def clamp(value: float, low: float, high: float) -> float:
    """Keep a number inside a range."""
    return max(low, min(high, value))


def lerp(start: float, end: float, amount: float) -> float:
    """Linear interpolation used by animations."""
    return start + (end - start) * amount


def ease_out_cubic(value: float) -> float:
    """Smooth easing curve for popups and transitions."""
    value = clamp(value, 0.0, 1.0)
    return 1.0 - (1.0 - value) ** 3


def format_number(value: float | int) -> str:
    """Format large scores with separators."""
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    return f"{value:,}"


def safe_int(text: str, fallback: Optional[int] = None) -> Optional[int]:
    """Convert typed input to an integer without raising an exception."""
    try:
        return int(text.strip())
    except (TypeError, ValueError):
        return fallback


def safe_float(text: str, fallback: Optional[float] = None) -> Optional[float]:
    """Convert typed input to a float without raising an exception."""
    try:
        return float(text.strip())
    except (TypeError, ValueError):
        return fallback


def nice_fraction(numerator: int, denominator: int) -> str:
    """Return a reduced fraction as text."""
    divisor = math.gcd(numerator, denominator)
    numerator //= divisor
    denominator //= divisor
    return f"{numerator}/{denominator}"


def almost_equal(a: float, b: float, tolerance: float = 0.0001) -> bool:
    """Compare floating-point answers with a small tolerance."""
    return abs(a - b) <= tolerance


def wrap_text(font: pygame.font.Font, text: str, width: int) -> list[str]:
    """Wrap text into lines that fit a pixel width."""
    words = str(text).split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = word if not current else current + " " + word
        if font.size(candidate)[0] <= width:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def draw_text(
    surface: pygame.Surface,
    font: pygame.font.Font,
    text: str,
    color: tuple[int, int, int],
    position: tuple[int, int],
    center: bool = False,
) -> pygame.Rect:
    """Draw text and return its rectangle."""
    image = font.render(str(text), True, color)
    rect = image.get_rect()
    if center:
        rect.center = position
    else:
        rect.topleft = position
    surface.blit(image, rect)
    return rect


def rounded_rect(
    surface: pygame.Surface,
    color: tuple[int, int, int],
    rect: pygame.Rect,
    radius: int = 14,
    width: int = 0,
) -> None:
    """Draw a rounded rectangle."""
    pygame.draw.rect(surface, color, rect, width, border_radius=radius)


# ============================================================================
# 03. DATA MODELS
# ============================================================================

@dataclass
class Question:
    """One generated maths challenge."""

    prompt: str
    answer: float
    topic: str
    explanation: str
    difficulty: int = 1
    choices: list[str] = field(default_factory=list)
    time_limit: float = Config.QUESTION_TIME
    boss: bool = False

    def check(self, raw_answer: str) -> bool:
        """Check an answer, accepting integers, decimals and fractions."""
        raw_answer = raw_answer.strip().replace(",", ".")
        if "/" in raw_answer:
            parts = raw_answer.split("/", 1)
            try:
                submitted = float(parts[0]) / float(parts[1])
            except (ValueError, ZeroDivisionError):
                return False
        else:
            try:
                submitted = float(raw_answer)
            except ValueError:
                return False
        return almost_equal(submitted, float(self.answer), 0.01)


@dataclass
class FloatingText:
    """Text that rises and fades after an event."""

    text: str
    x: float
    y: float
    color: tuple[int, int, int]
    life: float = 1.0
    duration: float = 1.0
    size: int = 28

    def update(self, dt: float) -> None:
        self.life -= dt
        self.y -= 42 * dt

    def draw(self, surface: pygame.Surface, fonts: "FontBook") -> None:
        alpha = int(255 * clamp(self.life / self.duration, 0, 1))
        image = fonts.get(self.size, True).render(self.text, True, self.color)
        image.set_alpha(alpha)
        rect = image.get_rect(center=(int(self.x), int(self.y)))
        surface.blit(image, rect)


@dataclass
class Particle:
    """Small colored square or circle used for visual feedback."""

    x: float
    y: float
    vx: float
    vy: float
    color: tuple[int, int, int]
    life: float
    size: float
    shape: str = "circle"

    def update(self, dt: float) -> None:
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.vy += 100 * dt
        self.life -= dt
        self.size = max(0.0, self.size - 8 * dt)

    def draw(self, surface: pygame.Surface) -> None:
        if self.life <= 0 or self.size <= 0:
            return
        rect = pygame.Rect(
            int(self.x - self.size / 2),
            int(self.y - self.size / 2),
            max(1, int(self.size)),
            max(1, int(self.size)),
        )
        if self.shape == "square":
            pygame.draw.rect(surface, self.color, rect, border_radius=2)
        else:
            pygame.draw.circle(
                surface, self.color, rect.center, max(1, int(self.size / 2))
            )


@dataclass
class Achievement:
    """A named challenge that can be unlocked."""

    key: str
    title: str
    description: str
    reward: int
    condition: Callable[["Profile"], bool]


# ============================================================================
# 04. PROFILE AND SAVE SYSTEM
# ============================================================================

class Profile:
    """Persistent player information."""

    DEFAULTS = {
        "name": "Player",
        "xp": 0,
        "coins": 0,
        "level": 1,
        "games_played": 0,
        "questions_answered": 0,
        "correct_answers": 0,
        "best_score": 0,
        "best_streak": 0,
        "total_score": 0,
        "unlocked": ["Campaign", "Survival", "Practice"],
        "achievements": [],
        "settings": {
            "volume": 0.7,
            "particles": True,
            "screen_shake": True,
            "show_timer": True,
            "difficulty": "Normal",
        },
        "history": [],
    }

    def __init__(self, data: Optional[dict[str, Any]] = None):
        merged = dict(self.DEFAULTS)
        if data:
            for key, value in data.items():
                if key == "settings":
                    merged["settings"] = {**self.DEFAULTS["settings"], **value}
                else:
                    merged[key] = value
        self.data = merged

    @property
    def name(self) -> str:
        return str(self.data["name"])

    @name.setter
    def name(self, value: str) -> None:
        self.data["name"] = value[:18] or "Player"

    @property
    def xp(self) -> int:
        return int(self.data["xp"])

    @property
    def coins(self) -> int:
        return int(self.data["coins"])

    @property
    def level(self) -> int:
        return int(self.data["level"])

    @property
    def best_score(self) -> int:
        return int(self.data["best_score"])

    @property
    def settings(self) -> dict[str, Any]:
        return self.data["settings"]

    def xp_for_next_level(self) -> int:
        return self.level * Config.XP_PER_LEVEL

    def add_xp(self, amount: int) -> bool:
        """Add XP and return True if the player leveled up."""
        self.data["xp"] += max(0, amount)
        leveled = False
        while self.data["xp"] >= self.xp_for_next_level():
            self.data["xp"] -= self.xp_for_next_level()
            self.data["level"] += 1
            self.data["coins"] += 100
            leveled = True
        return leveled

    def add_coins(self, amount: int) -> None:
        self.data["coins"] = max(0, self.coins + amount)

    def record_answer(self, correct: bool, streak: int) -> None:
        self.data["questions_answered"] += 1
        if correct:
            self.data["correct_answers"] += 1
        self.data["best_streak"] = max(self.data["best_streak"], streak)

    def record_game(self, score: int, mode: str) -> None:
        self.data["games_played"] += 1
        self.data["total_score"] += score
        self.data["best_score"] = max(self.best_score, score)
        self.data["history"].append({
            "score": int(score),
            "mode": mode,
            "date": time.strftime("%Y-%m-%d %H:%M"),
        })
        self.data["history"] = self.data["history"][-30:]

    def accuracy(self) -> float:
        total = self.data["questions_answered"]
        if total == 0:
            return 0.0
        return self.data["correct_answers"] / total * 100


class SaveManager:
    """Read and write the local profile safely."""

    def __init__(self):
        Config.DATA_DIR.mkdir(parents=True, exist_ok=True)

    def load(self) -> Profile:
        if not Config.SAVE_FILE.exists():
            return Profile()
        try:
            with Config.SAVE_FILE.open("r", encoding="utf-8") as file:
                return Profile(json.load(file))
        except (OSError, json.JSONDecodeError, TypeError):
            try:
                with Config.BACKUP_FILE.open("r", encoding="utf-8") as file:
                    return Profile(json.load(file))
            except (OSError, json.JSONDecodeError, TypeError):
                return Profile()

    def save(self, profile: Profile) -> None:
        """Write a backup first, then replace the main save."""
        try:
            if Config.SAVE_FILE.exists():
                Config.BACKUP_FILE.write_text(
                    Config.SAVE_FILE.read_text(encoding="utf-8"),
                    encoding="utf-8",
                )
            temporary = Config.SAVE_FILE.with_suffix(".tmp")
            temporary.write_text(
                json.dumps(profile.data, indent=2),
                encoding="utf-8",
            )
            temporary.replace(Config.SAVE_FILE)
        except OSError as error:
            print("Could not save profile:", error)


# ============================================================================
# 05. FONT AND SOUND MANAGEMENT
# ============================================================================

class FontBook:
    """Cache fonts so the game does not recreate them every frame."""

    def __init__(self):
        self.cache: dict[tuple[int, bool], pygame.font.Font] = {}

    def get(self, size: int, bold: bool = False) -> pygame.font.Font:
        key = (size, bold)
        if key not in self.cache:
            font = pygame.font.SysFont("arial", size, bold=bold)
            self.cache[key] = font
        return self.cache[key]


class SoundManager:
    """Optional sound effects. The game remains playable without audio."""

    def __init__(self, volume: float = 0.7):
        self.volume = volume
        self.enabled = False
        self.sounds: dict[str, pygame.mixer.Sound] = {}
        try:
            pygame.mixer.init()
            self.enabled = True
        except pygame.error:
            self.enabled = False

    def set_volume(self, value: float) -> None:
        self.volume = clamp(value, 0.0, 1.0)
        for sound in self.sounds.values():
            sound.set_volume(self.volume)

    def load(self, key: str, path: str) -> None:
        if not self.enabled or not os.path.exists(path):
            return
        try:
            sound = pygame.mixer.Sound(path)
            sound.set_volume(self.volume)
            self.sounds[key] = sound
        except pygame.error:
            pass

    def play(self, key: str) -> None:
        if self.enabled and key in self.sounds:
            self.sounds[key].play()


# ============================================================================
# 06. QUESTION GENERATION ENGINE
# ============================================================================

class QuestionFactory:
    """Creates questions across a range of mathematical topics."""

    TOPICS = [
        "Arithmetic",
        "Fractions",
        "Powers",
        "Roots",
        "Algebra",
        "Geometry",
        "Trigonometry",
        "Probability",
        "Logarithms",
        "Calculus",
    ]

    def __init__(self):
        self.random = random.Random()

    def generate(
        self,
        difficulty: int = 2,
        topics: Optional[list[str]] = None,
        boss: bool = False,
    ) -> Question:
        """Generate a question using an enabled topic list."""
        allowed = topics or self.TOPICS
        allowed = [topic for topic in allowed if topic in self.TOPICS]
        if not allowed:
            allowed = ["Arithmetic"]
        topic = self.random.choice(allowed)
        makers = {
            "Arithmetic": self.arithmetic,
            "Fractions": self.fractions,
            "Powers": self.powers,
            "Roots": self.roots,
            "Algebra": self.algebra,
            "Geometry": self.geometry,
            "Trigonometry": self.trigonometry,
            "Probability": self.probability,
            "Logarithms": self.logarithms,
            "Calculus": self.calculus,
        }
        question = makers[topic](difficulty)
        question.boss = boss
        if boss:
            question.time_limit = Config.BOSS_QUESTION_TIME
        return question

    def arithmetic(self, difficulty: int) -> Question:
        maximum = min(10 ** (difficulty + 1), 100000)
        a = self.random.randint(2, maximum)
        b = self.random.randint(2, maximum)
        operation = self.random.choice(["+", "-", "×", "÷"])
        if operation == "+":
            answer = a + b
            prompt = f"{a} + {b}"
        elif operation == "-":
            if b > a:
                a, b = b, a
            answer = a - b
            prompt = f"{a} − {b}"
        elif operation == "×":
            answer = a * b
            prompt = f"{a} × {b}"
        else:
            answer = self.random.randint(2, maximum)
            b = self.random.randint(2, 30)
            a = answer * b
            prompt = f"{a} ÷ {b}"
        return Question(prompt, answer, "Arithmetic",
                        f"Evaluate the expression: {prompt}.")

    def fractions(self, difficulty: int) -> Question:
        a = self.random.randint(1, 12 * difficulty)
        b = self.random.randint(2, 16)
        c = self.random.randint(1, 12 * difficulty)
        d = self.random.randint(2, 16)
        operation = self.random.choice(["+", "−", "×"])
        if operation == "+":
            numerator = a * d + c * b
            denominator = b * d
            prompt = f"{a}/{b} + {c}/{d}"
        elif operation == "−":
            numerator = a * d - c * b
            denominator = b * d
            prompt = f"{a}/{b} − {c}/{d}"
        else:
            numerator = a * c
            denominator = b * d
            prompt = f"{a}/{b} × {c}/{d}"
        divisor = math.gcd(abs(numerator), denominator)
        answer = numerator / denominator
        reduced = nice_fraction(numerator, denominator)
        return Question(prompt + " (decimal answer)", answer, "Fractions",
                        f"Combine the numerators over a common denominator. "
                        f"The reduced result is {reduced}.")

    def powers(self, difficulty: int) -> Question:
        base = self.random.randint(2, min(12, difficulty + 4))
        exponent = self.random.randint(2, min(5, difficulty + 2))
        answer = base ** exponent
        return Question(
            f"Evaluate {base}^{exponent}",
            answer,
            "Powers",
            f"{base}^{exponent} means multiplying {base} by itself "
            f"{exponent} times.",
        )

    def roots(self, difficulty: int) -> Question:
        root = self.random.randint(2, min(30, 5 + difficulty * 4))
        if self.random.random() < 0.2 and difficulty >= 4:
            value = root ** 3
            return Question(
                f"Find the cube root of {value}",
                root,
                "Roots",
                f"{root} × {root} × {root} = {value}.",
            )
        value = root * root
        return Question(
            f"Find √{value}",
            root,
            "Roots",
            f"{root} × {root} = {value}.",
        )

    def algebra(self, difficulty: int) -> Question:
        x = self.random.randint(-20 * difficulty, 20 * difficulty)
        a = self.random.randint(1, 5 + difficulty)
        b = self.random.randint(-30, 30)
        result = a * x + b
        sign = "+" if b >= 0 else "−"
        prompt = f"Solve for x: {a}x {sign} {abs(b)} = {result}"
        return Question(
            prompt,
            x,
            "Algebra",
            f"Subtract {b} from both sides, then divide by {a}. "
            f"The answer is x = {x}.",
        )

    def geometry(self, difficulty: int) -> Question:
        shape = self.random.choice(["rectangle", "triangle", "circle"])
        if shape == "rectangle":
            width = self.random.randint(2, 10 * difficulty)
            height = self.random.randint(2, 10 * difficulty)
            answer = width * height
            prompt = f"Rectangle area: width {width}, height {height}"
            explanation = f"Area = width × height = {answer}."
        elif shape == "triangle":
            base = self.random.randint(2, 12 * difficulty)
            height = self.random.randint(2, 12 * difficulty)
            answer = base * height / 2
            prompt = f"Triangle area: base {base}, height {height}"
            explanation = f"Area = base × height ÷ 2 = {answer:g}."
        else:
            radius = self.random.randint(2, 5 * difficulty)
            answer = math.pi * radius * radius
            prompt = f"Circle area with radius {radius} (use π = 3.1416)"
            explanation = f"Area = πr² = {answer:.2f}."
        return Question(prompt, answer, "Geometry", explanation)

    def trigonometry(self, difficulty: int) -> Question:
        angles = [0, 30, 45, 60, 90]
        angle = self.random.choice(angles)
        function = self.random.choice(["sin", "cos"])
        value = getattr(math, function)(math.radians(angle))
        # Use percentages to make answers easy to type.
        answer = round(value * 100)
        prompt = f"Find {function}({angle}°) × 100, rounded"
        explanation = f"{function}({angle}°) × 100 ≈ {answer}."
        return Question(prompt, answer, "Trigonometry", explanation)

    def probability(self, difficulty: int) -> Question:
        red = self.random.randint(1, 10 * difficulty)
        blue = self.random.randint(1, 10 * difficulty)
        total = red + blue
        answer = round(red / total * 100)
        prompt = (
            f"A bag has {red} red and {blue} blue balls. "
            f"What is the percentage chance of red? Round to whole %."
        )
        explanation = f"Probability = {red}/{total} × 100 ≈ {answer}%."
        return Question(prompt, answer, "Probability", explanation)

    def logarithms(self, difficulty: int) -> Question:
        base = self.random.choice([2, 3, 5, 10])
        exponent = self.random.randint(1, min(6, difficulty + 2))
        value = base ** exponent
        prompt = f"Evaluate log base {base} of {value}"
        return Question(
            prompt,
            exponent,
            "Logarithms",
            f"Because {base}^{exponent} = {value}, the logarithm is {exponent}.",
        )

    def calculus(self, difficulty: int) -> Question:
        power = self.random.randint(2, min(8, difficulty + 3))
        coefficient = self.random.randint(1, 6)
        # Ask for the derivative at x=2.
        answer = coefficient * power * (2 ** (power - 1))
        prompt = (
            f"If f(x) = {coefficient}x^{power}, "
            f"find f'(2)"
        )
        explanation = (
            f"Power rule: f'(x) = {coefficient * power}x^{power - 1}. "
            f"Substitute x = 2 to get {answer}."
        )
        return Question(prompt, answer, "Calculus", explanation)


# ============================================================================
# 07. ACHIEVEMENTS
# ============================================================================

def build_achievements() -> list[Achievement]:
    """Create achievement definitions in one place."""
    return [
        Achievement(
            "first_game", "First Steps", "Finish your first game.", 50,
            lambda p: p.data["games_played"] >= 1,
        ),
        Achievement(
            "ten_games", "Dedicated", "Finish 10 games.", 150,
            lambda p: p.data["games_played"] >= 10,
        ),
        Achievement(
            "hundred_questions", "Question Machine",
            "Answer 100 questions.", 200,
            lambda p: p.data["questions_answered"] >= 100,
        ),
        Achievement(
            "perfect_ten", "Perfect Ten",
            "Get 10 correct answers in a row.", 250,
            lambda p: p.data["best_streak"] >= 10,
        ),
        Achievement(
            "big_score", "High Scorer", "Reach 5,000 points in one game.",
            300, lambda p: p.best_score >= 5000,
        ),
        Achievement(
            "level_five", "Getting Stronger", "Reach level 5.", 300,
            lambda p: p.level >= 5,
        ),
        Achievement(
            "level_ten", "Maths Veteran", "Reach level 10.", 700,
            lambda p: p.level >= 10,
        ),
        Achievement(
            "accurate", "Precision", "Reach 90% overall accuracy.",
            400, lambda p: p.accuracy() >= 90 and
            p.data["questions_answered"] >= 50,
        ),
        Achievement(
            "boss_slayer", "Boss Slayer", "Defeat a boss.",
            250, lambda p: p.data.get("bosses_defeated", 0) >= 1,
        ),
        Achievement(
            "coin_collector", "Treasure Hunter", "Collect 1,000 coins.",
            300, lambda p: p.coins >= 1000,
        ),
    ]


class AchievementManager:
    """Checks and grants achievements."""

    def __init__(self, profile: Profile):
        self.profile = profile
        self.items = build_achievements()

    def check(self) -> list[Achievement]:
        unlocked = []
        owned = self.profile.data["achievements"]
        for achievement in self.items:
            if achievement.key in owned:
                continue
            if achievement.condition(self.profile):
                owned.append(achievement.key)
                self.profile.add_coins(achievement.reward)
                unlocked.append(achievement)
        return unlocked


# ============================================================================
# 08. PARTICLE AND BACKGROUND SYSTEMS
# ============================================================================

class ParticleSystem:
    """Owns all short-lived particles and floating score messages."""

    def __init__(self):
        self.particles: list[Particle] = []
        self.floating: list[FloatingText] = []

    def burst(
        self,
        x: float,
        y: float,
        color: tuple[int, int, int],
        count: int = 28,
    ) -> None:
        for _ in range(count):
            angle = random.uniform(0, math.tau)
            speed = random.uniform(45, 260)
            self.particles.append(Particle(
                x, y,
                math.cos(angle) * speed,
                math.sin(angle) * speed,
                color,
                random.uniform(0.45, 1.2),
                random.uniform(3, 9),
                random.choice(["circle", "square"]),
            ))
        self._trim()

    def add_text(
        self,
        text: str,
        x: float,
        y: float,
        color: tuple[int, int, int],
        size: int = 28,
    ) -> None:
        self.floating.append(FloatingText(text, x, y, color, 1, 1, size))

    def _trim(self) -> None:
        if len(self.particles) > Config.PARTICLE_LIMIT:
            self.particles = self.particles[-Config.PARTICLE_LIMIT:]

    def update(self, dt: float) -> None:
        for particle in self.particles:
            particle.update(dt)
        self.particles = [p for p in self.particles if p.life > 0]
        for floating in self.floating:
            floating.update(dt)
        self.floating = [f for f in self.floating if f.life > 0]

    def draw(self, surface: pygame.Surface, fonts: FontBook) -> None:
        for particle in self.particles:
            particle.draw(surface)
        for floating in self.floating:
            floating.draw(surface, fonts)


class Starfield:
    """Slow moving stars add depth to the dark background."""

    def __init__(self, width: int, height: int, count: int = 90):
        self.width = width
        self.height = height
        self.stars = []
        for _ in range(count):
            self.stars.append([
                random.randrange(width),
                random.randrange(height),
                random.uniform(10, 48),
                random.randint(1, 3),
            ])

    def update(self, dt: float) -> None:
        for star in self.stars:
            star[1] += star[2] * dt
            if star[1] > self.height:
                star[1] = 0
                star[0] = random.randrange(self.width)

    def draw(self, surface: pygame.Surface) -> None:
        for x, y, speed, size in self.stars:
            brightness = int(clamp(100 + speed * 2, 100, 190))
            color = (brightness, brightness, min(255, brightness + 35))
            pygame.draw.circle(surface, color, (int(x), int(y)), size)


# ============================================================================
# 09. UI COMPONENTS
# ============================================================================

class Button:
    """Reusable animated button."""

    def __init__(
        self,
        rect: pygame.Rect,
        label: str,
        callback: Callable[[], None],
        color: tuple[int, int, int] = Config.COLORS["blue"],
        width: int = 2,
    ):
        self.rect = pygame.Rect(rect)
        self.label = label
        self.callback = callback
        self.color = color
        self.border_width = width
        self.hover = False
        self.enabled = True
        self.scale = 1.0

    def handle_event(self, event: pygame.event.Event) -> bool:
        if not self.enabled:
            return False
        if event.type == pygame.MOUSEMOTION:
            self.hover = self.rect.collidepoint(event.pos)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self.callback()
                return True
        return False

    def draw(self, surface: pygame.Surface, fonts: FontBook) -> None:
        color = self.color
        if not self.enabled:
            color = (65, 72, 90)
        elif self.hover:
            color = tuple(min(255, c + 35) for c in self.color)

        rounded_rect(surface, (7, 10, 20), self.rect.move(0, 5), 13)
        rounded_rect(surface, color, self.rect, 13)
        rounded_rect(surface, Config.COLORS["white"], self.rect, 13, 2)
        text_color = Config.COLORS["white"] if self.enabled else (130, 135, 150)
        draw_text(
            surface, fonts.get(22, True), self.label,
            text_color, self.rect.center, True,
        )


class TextInput:
    """Simple text box for the player's display name."""

    def __init__(self, rect: pygame.Rect, value: str = ""):
        self.rect = pygame.Rect(rect)
        self.value = value
        self.active = False
        self.limit = 18

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self.active = self.rect.collidepoint(event.pos)
        if event.type == pygame.KEYDOWN and self.active:
            if event.key == pygame.K_BACKSPACE:
                self.value = self.value[:-1]
            elif event.key == pygame.K_RETURN:
                self.active = False
            elif event.unicode.isprintable() and len(self.value) < self.limit:
                self.value += event.unicode

    def draw(self, surface: pygame.Surface, fonts: FontBook) -> None:
        border = Config.COLORS["cyan"] if self.active else (80, 95, 125)
        rounded_rect(surface, Config.COLORS["panel"], self.rect, 10)
        rounded_rect(surface, border, self.rect, 10, 2)
        shown = self.value or "Enter player name"
        color = Config.COLORS["white"] if self.value else Config.COLORS["muted"]
        draw_text(surface, fonts.get(20), shown, color,
                  (self.rect.x + 14, self.rect.y + 12))


class ProgressBar:
    """Horizontal progress bar with a label."""

    def __init__(self, rect: pygame.Rect, color: tuple[int, int, int]):
        self.rect = pygame.Rect(rect)
        self.color = color
        self.value = 0.0
        self.label = ""

    def draw(self, surface: pygame.Surface, fonts: FontBook) -> None:
        rounded_rect(surface, (43, 51, 73), self.rect, 8)
        fill_width = int(self.rect.width * clamp(self.value, 0, 1))
        if fill_width > 0:
            fill_rect = pygame.Rect(
                self.rect.x, self.rect.y, fill_width, self.rect.height
            )
            rounded_rect(surface, self.color, fill_rect, 8)
        if self.label:
            draw_text(
                surface, fonts.get(14, True), self.label,
                Config.COLORS["white"],
                (self.rect.centerx, self.rect.centery), True,
            )


# ============================================================================
# 10. GAME SESSION
# ============================================================================

class GameSession:
    """Stores state for a single run."""

    def __init__(
        self,
        mode: str,
        difficulty: str,
        factory: QuestionFactory,
        topics: Optional[list[str]] = None,
    ):
        self.mode = mode
        self.difficulty_name = difficulty
        self.difficulty_index = list(Config.DIFFICULTIES).index(difficulty) + 1
        self.difficulty = Config.DIFFICULTIES[difficulty]
        self.factory = factory
        self.topics = topics or factory.TOPICS[:]
        self.score = 0
        self.lives = Config.STARTING_LIVES
        self.streak = 0
        self.best_streak = 0
        self.combo_multiplier = 1
        self.question_count = 0
        self.correct_count = 0
        self.wrong_count = 0
        self.started_at = time.time()
        self.elapsed = 0.0
        self.remaining = 90.0 if mode == "Time Attack" else 0.0
        self.question: Optional[Question] = None
        self.question_elapsed = 0.0
        self.answer_text = ""
        self.feedback = ""
        self.feedback_color = Config.COLORS["white"]
        self.feedback_timer = 0.0
        self.show_explanation = False
        self.hints = 2
        self.skips = 1
        self.shields = 0
        self.double_score = 0
        self.boss_active = False
        self.boss_health = 3
        self.boss_max_health = 3
        self.bosses_defeated = 0
        self.finished = False
        self.finish_reason = ""
        self.paused = False
        self.new_question()

    def new_question(self) -> None:
        self.question_count += 1
        self.answer_text = ""
        self.question_elapsed = 0.0
        self.show_explanation = False

        boss_now = (
            self.mode in ("Campaign", "Endless")
            and self.question_count % 10 == 0
        )
        self.boss_active = boss_now
        if boss_now:
            self.boss_health = self.boss_max_health
        self.question = self.factory.generate(
            self.difficulty_index,
            self.topics,
            boss=boss_now,
        )

    def time_limit(self) -> float:
        if self.question is None:
            return Config.QUESTION_TIME
        return self.question.time_limit or self.difficulty["time"]

    def update(self, dt: float) -> None:
        if self.finished or self.paused:
            return
        self.elapsed += dt
        self.question_elapsed += dt
        if self.mode == "Time Attack":
            self.remaining -= dt
            if self.remaining <= 0:
                self.remaining = 0
                self.finish("Time is up!")
                return
        if self.mode != "Practice" and self.question_elapsed >= self.time_limit():
            self.submit_timeout()
        if self.feedback_timer > 0:
            self.feedback_timer -= dt

    def submit_timeout(self) -> None:
        self.answer_text = ""
        self._wrong("Time ran out!")

    def submit(self) -> bool:
        if not self.question or self.finished:
            return False
        if not self.answer_text.strip():
            return False
        if self.question.check(self.answer_text):
            self._correct()
        else:
            self._wrong("Incorrect!")
        return True

    def _correct(self) -> None:
        assert self.question is not None
        self.correct_count += 1
        self.streak += 1
        self.best_streak = max(self.best_streak, self.streak)
        self.combo_multiplier = min(1 + self.streak // 4, 8)

        base = self.difficulty["points"]
        speed_ratio = self.question_elapsed / max(1, self.time_limit())
        speed_bonus = int((1 - clamp(speed_ratio, 0, 1)) * base * 0.7)
        points = base * self.combo_multiplier + speed_bonus
        if self.double_score > 0:
            points *= 2
            self.double_score -= 1
        self.score += points

        if self.boss_active:
            self.boss_health -= 1
            if self.boss_health <= 0:
                self.boss_active = False
                self.bosses_defeated += 1
                self.score += 1000
                self.feedback = "BOSS DEFEATED! +1000"
            else:
                self.feedback = f"BOSS HIT! +{points}"
        else:
            self.feedback = f"CORRECT! +{points}"

        self.feedback_color = Config.COLORS["green"]
        self.feedback_timer = 1.3
        self.show_explanation = True
        if self.mode == "Time Attack":
            self.remaining = min(120, self.remaining + 2.5)

    def _wrong(self, message: str) -> None:
        self.wrong_count += 1
        self.streak = 0
        self.combo_multiplier = 1
        if self.shields > 0:
            self.shields -= 1
            self.feedback = "SHIELD BLOCKED THE HIT!"
            self.feedback_color = Config.COLORS["cyan"]
        elif self.mode != "Practice":
            self.lives -= 1
            self.feedback = message
            self.feedback_color = Config.COLORS["red"]
        else:
            self.feedback = message
            self.feedback_color = Config.COLORS["orange"]
        self.feedback_timer = 1.4
        self.show_explanation = True
        if self.lives <= 0 and self.mode != "Practice":
            self.finish("Out of lives!")

    def use_hint(self) -> Optional[str]:
        if self.hints <= 0 or not self.question:
            return None
        self.hints -= 1
        return self.question.explanation

    def use_skip(self) -> bool:
        if self.skips <= 0 or self.finished:
            return False
        self.skips -= 1
        self.streak = 0
        self.new_question()
        return True

    def activate_shield(self) -> bool:
        if self.shields >= 3:
            return False
        self.shields += 1
        return True

    def activate_double_score(self) -> bool:
        self.double_score = min(5, self.double_score + 3)
        return True

    def finish(self, reason: str) -> None:
        self.finished = True
        self.finish_reason = reason

    def accuracy(self) -> float:
        if self.question_count <= 0:
            return 0.0
        return self.correct_count / max(1, self.correct_count + self.wrong_count) * 100

    def summary(self) -> dict[str, Any]:
        return {
            "score": self.score,
            "mode": self.mode,
            "difficulty": self.difficulty_name,
            "correct": self.correct_count,
            "wrong": self.wrong_count,
            "accuracy": self.accuracy(),
            "best_streak": self.best_streak,
            "elapsed": self.elapsed,
            "bosses": self.bosses_defeated,
            "reason": self.finish_reason,
        }


# ============================================================================
# 11. SCENE BASE CLASS
# ============================================================================

class Scene:
    """Base interface shared by every screen."""

    def __init__(self, game: "MathsOverload"):
        self.game = game
        self.buttons: list[Button] = []

    def enter(self) -> None:
        self.buttons.clear()

    def handle_event(self, event: pygame.event.Event) -> None:
        for button in list(self.buttons):
            button.handle_event(event)

    def update(self, dt: float) -> None:
        pass

    def draw(self, surface: pygame.Surface) -> None:
        pass

    def draw_title(
        self,
        surface: pygame.Surface,
        title: str,
        subtitle: str = "",
    ) -> None:
        draw_text(
            surface, self.game.fonts.get(42, True), title,
            Config.COLORS["white"], (Config.WIDTH // 2, 80), True,
        )
        if subtitle:
            draw_text(
                surface, self.game.fonts.get(18), subtitle,
                Config.COLORS["muted"], (Config.WIDTH // 2, 122), True,
            )

    def add_button(
        self,
        rect: tuple[int, int, int, int],
        label: str,
        callback: Callable[[], None],
        color: tuple[int, int, int] = Config.COLORS["blue"],
    ) -> Button:
        button = Button(pygame.Rect(rect), label, callback, color)
        self.buttons.append(button)
        return button

    def draw_buttons(self, surface: pygame.Surface) -> None:
        for button in self.buttons:
            button.draw(surface, self.game.fonts)


# ============================================================================
# 12. MAIN MENU SCENE
# ============================================================================

class MainMenu(Scene):
    """Main title screen and navigation."""

    def enter(self) -> None:
        super().enter()
        self.title_phase = 0.0
        self.add_button((470, 285, 340, 58), "PLAY", self.open_modes,
                        Config.COLORS["blue"])
        self.add_button((470, 360, 340, 58), "PROFILE", self.open_profile,
                        Config.COLORS["purple"])
        self.add_button((470, 435, 340, 58), "ACHIEVEMENTS",
                        self.open_achievements, Config.COLORS["pink"])
        self.add_button((470, 510, 340, 58), "SETTINGS",
                        self.open_settings, Config.COLORS["panel_light"])
        self.add_button((470, 585, 340, 58), "QUIT",
                        self.game.quit, Config.COLORS["red"])

    def open_modes(self) -> None:
        self.game.change_scene("modes")

    def open_profile(self) -> None:
        self.game.change_scene("profile")

    def open_achievements(self) -> None:
        self.game.change_scene("achievements")

    def open_settings(self) -> None:
        self.game.change_scene("settings")

    def update(self, dt: float) -> None:
        self.title_phase += dt

    def draw(self, surface: pygame.Surface) -> None:
        self.game.draw_background(surface)
        pulse = 1 + math.sin(self.title_phase * 2) * 0.025
        title_font = self.game.fonts.get(int(52 * pulse), True)
        draw_text(
            surface, title_font, "MATHS OVERLOAD",
            Config.COLORS["cyan"], (640, 145), True,
        )
        draw_text(
            surface, self.game.fonts.get(21, True), "ULTIMATE EDITION",
            Config.COLORS["purple"], (640, 198), True,
        )
        profile = self.game.profile
        draw_text(
            surface, self.game.fonts.get(17),
            f"{profile.name}  •  LEVEL {profile.level}  •  "
            f"{format_number(profile.coins)} COINS",
            Config.COLORS["muted"], (640, 245), True,
        )
        self.draw_buttons(surface)
        draw_text(
            surface, self.game.fonts.get(14),
            "A maths adventure. Think fast. Level up. Defeat the boss.",
            Config.COLORS["muted"], (640, 760), True,
        )


# ============================================================================
# 13. MODE SELECTION SCENE
# ============================================================================

class ModeSelect(Scene):
    """Choose a mode and difficulty before starting."""

    def enter(self) -> None:
        super().enter()
        self.selected_mode = "Campaign"
        self.selected_difficulty = self.game.profile.settings.get(
            "difficulty", "Normal"
        )
        self.add_button((60, 710, 180, 48), "BACK",
                        lambda: self.game.change_scene("menu"),
                        Config.COLORS["panel_light"])
        self.add_button((950, 710, 260, 48), "START GAME",
                        self.start_game, Config.COLORS["green"])

    def start_game(self) -> None:
        self.game.profile.settings["difficulty"] = self.selected_difficulty
        self.game.start_session(
            self.selected_mode,
            self.selected_difficulty,
        )

    def handle_event(self, event: pygame.event.Event) -> None:
        super().handle_event(event)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for index, mode in enumerate(Config.MODES):
                rect = pygame.Rect(100, 190 + index * 82, 470, 62)
                if rect.collidepoint(event.pos):
                    self.selected_mode = mode
            difficulties = list(Config.DIFFICULTIES)
            for index, name in enumerate(difficulties):
                col = index % 5
                row = index // 5
                rect = pygame.Rect(650 + col * 112, 260 + row * 100, 100, 62)
                if rect.collidepoint(event.pos):
                    self.selected_difficulty = name

    def draw(self, surface: pygame.Surface) -> None:
        self.game.draw_background(surface)
        self.draw_title(surface, "CHOOSE YOUR CHALLENGE",
                        "Pick a mode and a difficulty")
        draw_text(surface, self.game.fonts.get(24, True), "GAME MODES",
                  Config.COLORS["cyan"], (100, 155))
        for index, mode in enumerate(Config.MODES):
            rect = pygame.Rect(100, 190 + index * 82, 470, 62)
            selected = mode == self.selected_mode
            color = Config.COLORS["blue"] if selected else Config.COLORS["panel"]
            rounded_rect(surface, color, rect, 12)
            rounded_rect(surface, Config.COLORS["cyan"] if selected else
                         (66, 78, 110), rect, 12, 2)
            draw_text(surface, self.game.fonts.get(22, True), mode,
                      Config.COLORS["white"], rect.center, True)
        draw_text(surface, self.game.fonts.get(24, True), "DIFFICULTY",
                  Config.COLORS["purple"], (650, 155))
        for index, name in enumerate(Config.DIFFICULTIES):
            col = index % 5
            row = index // 5
            rect = pygame.Rect(650 + col * 112, 260 + row * 100, 100, 62)
            selected = name == self.selected_difficulty
            color = Config.COLORS["purple"] if selected else Config.COLORS["panel"]
            rounded_rect(surface, color, rect, 10)
            rounded_rect(surface, Config.COLORS["white"] if selected else
                         (66, 78, 110), rect, 10, 2)
            draw_text(surface, self.game.fonts.get(14, True), name,
                      Config.COLORS["white"], rect.center, True)
        descriptions = {
            "Campaign": "Progress through stages and defeat bosses.",
            "Survival": "You have three lives. How long can you last?",
            "Time Attack": "Score as much as possible before time runs out.",
            "Practice": "Learn without losing lives or racing a timer.",
            "Endless": "An endless challenge with boss encounters.",
        }
        draw_text(
            surface, self.game.fonts.get(18),
            descriptions[self.selected_mode],
            Config.COLORS["muted"], (100, 625),
        )
        self.draw_buttons(surface)


# ============================================================================
# 14. GAMEPLAY SCENE
# ============================================================================

class GameplayScene(Scene):
    """Main game screen."""

    def enter(self) -> None:
        super().enter()
        self.session = self.game.session
        self.feedback_seen = 0
        self.hint_message = ""
        self.hint_timer = 0.0
        self.answer_rect = pygame.Rect(360, 515, 560, 64)
        self.add_button((370, 605, 170, 52), "SUBMIT",
                        self.submit_answer, Config.COLORS["green"])
        self.add_button((555, 605, 170, 52), "HINT",
                        self.show_hint, Config.COLORS["purple"])
        self.add_button((740, 605, 170, 52), "SKIP",
                        self.skip_question, Config.COLORS["orange"])

    def submit_answer(self) -> None:
        self.session.submit()

    def show_hint(self) -> None:
        result = self.session.use_hint()
        if result:
            self.hint_message = result
            self.hint_timer = 5.0

    def skip_question(self) -> None:
        if self.session.use_skip():
            self.hint_message = "Question skipped."
            self.hint_timer = 1.5

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.game.change_scene("pause")
                return
            if event.key == pygame.K_RETURN:
                self.submit_answer()
                return
            if event.key == pygame.K_BACKSPACE:
                self.session.answer_text = self.session.answer_text[:-1]
                return
            if event.key == pygame.K_h:
                self.show_hint()
                return
            if event.key == pygame.K_s:
                self.skip_question()
                return
            if event.unicode and event.unicode in "0123456789.-/":
                if len(self.session.answer_text) < 24:
                    self.session.answer_text += event.unicode
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.answer_rect.collidepoint(event.pos):
                pass
        super().handle_event(event)

    def update(self, dt: float) -> None:
        self.session.update(dt)
        if self.hint_timer > 0:
            self.hint_timer -= dt
        if self.session.feedback_timer <= 0 and self.session.show_explanation:
            self.session.show_explanation = False
            if not self.session.finished:
                self.session.new_question()
        if self.session.finished:
            self.game.finish_session()

    def draw(self, surface: pygame.Surface) -> None:
        self.game.draw_background(surface)
        session = self.session
        question = session.question

        draw_text(surface, self.game.fonts.get(30, True), session.mode.upper(),
                  Config.COLORS["cyan"], (55, 35))
        draw_text(
            surface, self.game.fonts.get(18),
            f"DIFFICULTY: {session.difficulty_name}",
            Config.COLORS["muted"], (58, 78),
        )

        # Score and streak cards.
        self._stat_card(surface, (55, 125, 220, 92),
                        "SCORE", format_number(session.score),
                        Config.COLORS["yellow"])
        self._stat_card(surface, (295, 125, 220, 92),
                        "STREAK", str(session.streak),
                        Config.COLORS["pink"])
        self._stat_card(surface, (535, 125, 220, 92),
                        "MULTIPLIER", f"x{session.combo_multiplier}",
                        Config.COLORS["purple"])
        self._stat_card(surface, (775, 125, 220, 92),
                        "LIVES", "∞" if session.mode == "Practice"
                        else "♥ " * max(0, session.lives),
                        Config.COLORS["red"])
        self._stat_card(surface, (1015, 125, 210, 92),
                        "QUESTION", str(session.question_count),
                        Config.COLORS["cyan"])

        # Timer.
        if session.mode == "Time Attack":
            timer_value = session.remaining / 90
            timer_label = f"ROUND TIME: {session.remaining:04.1f}s"
        else:
            timer_value = 1 - session.question_elapsed / session.time_limit()
            timer_label = f"QUESTION TIME: "
            if self.game.profile.settings.get("show_timer", True):
                timer_label += f"{max(0, session.time_limit() - session.question_elapsed):04.1f}s"
        timer = ProgressBar(pygame.Rect(260, 245, 760, 22),
                            Config.COLORS["green"] if timer_value > 0.3
                            else Config.COLORS["red"])
        timer.value = timer_value
        timer.draw(surface, self.game.fonts)
        draw_text(surface, self.game.fonts.get(16, True), timer_label,
                  Config.COLORS["muted"], (640, 282), True)

        if session.boss_active:
            self._draw_boss(surface)

        # Question card.
        card = pygame.Rect(170, 315, 940, 170)
        rounded_rect(surface, (5, 8, 18), card.move(0, 8), 20)
        rounded_rect(surface, Config.COLORS["panel"], card, 20)
        rounded_rect(surface, Config.COLORS["panel_light"], card, 20, 2)

        if question:
            draw_text(surface, self.game.fonts.get(16, True),
                      question.topic.upper(), Config.COLORS["purple"],
                      (640, 345), True)
            prompt_font = self.game.fonts.get(28, True)
            lines = wrap_text(prompt_font, question.prompt, 850)
            start_y = 397 - (len(lines) - 1) * 18
            for index, line in enumerate(lines):
                draw_text(surface, prompt_font, line,
                          Config.COLORS["white"],
                          (640, start_y + index * 42), True)

        # Answer input.
        rounded_rect(surface, Config.COLORS["panel_light"],
                     self.answer_rect, 12)
        rounded_rect(surface, Config.COLORS["cyan"],
                     self.answer_rect, 12, 2)
        answer = session.answer_text or "Type your answer..."
        answer_color = (Config.COLORS["white"] if session.answer_text
                        else Config.COLORS["muted"])
        draw_text(surface, self.game.fonts.get(24, True), answer,
                  answer_color, self.answer_rect.center, True)

        self.draw_buttons(surface)

        if session.feedback_timer > 0:
            draw_text(surface, self.game.fonts.get(24, True),
                      session.feedback, session.feedback_color,
                      (640, 690), True)
            if session.show_explanation and question:
                lines = wrap_text(self.game.fonts.get(15),
                                  question.explanation, 900)
                for index, line in enumerate(lines[:2]):
                    draw_text(surface, self.game.fonts.get(15), line,
                              Config.COLORS["muted"],
                              (640, 724 + index * 20), True)

        if self.hint_timer > 0 and self.hint_message:
            rounded_rect(surface, Config.COLORS["panel_light"],
                         pygame.Rect(180, 755, 920, 34), 8)
            draw_text(surface, self.game.fonts.get(14),
                      self.hint_message[:120], Config.COLORS["yellow"],
                      (640, 772), True)

        draw_text(surface, self.game.fonts.get(13),
                  "ENTER: submit    H: hint    S: skip    ESC: pause",
                  Config.COLORS["muted"], (640, 790), True)

    def _stat_card(
        self,
        surface: pygame.Surface,
        rect: tuple[int, int, int, int],
        label: str,
        value: str,
        color: tuple[int, int, int],
    ) -> None:
        box = pygame.Rect(rect)
        rounded_rect(surface, Config.COLORS["panel"], box, 12)
        rounded_rect(surface, color, box, 12, 2)
        draw_text(surface, self.game.fonts.get(14, True), label,
                  Config.COLORS["muted"], (box.centerx, box.y + 22), True)
        draw_text(surface, self.game.fonts.get(23, True), value,
                  color, (box.centerx, box.y + 59), True)

    def _draw_boss(self, surface: pygame.Surface) -> None:
        box = pygame.Rect(380, 300, 520, 10)
        rounded_rect(surface, (75, 35, 55), box, 5)
        fill = pygame.Rect(
            box.x, box.y,
            int(box.width * self.session.boss_health /
                self.session.boss_max_health),
            box.height,
        )
        rounded_rect(surface, Config.COLORS["pink"], fill, 5)
        draw_text(surface, self.game.fonts.get(16, True),
                  "MATHS BOSS", Config.COLORS["pink"],
                  (640, 286), True)


# ============================================================================
# 15. PAUSE SCENE
# ============================================================================

class PauseScene(Scene):
    """Pause overlay with resume and exit actions."""

    def enter(self) -> None:
        super().enter()
        if self.game.session:
            self.game.session.paused = True
        self.add_button((470, 320, 340, 58), "RESUME",
                        self.resume, Config.COLORS["green"])
        self.add_button((470, 395, 340, 58), "RESTART",
                        self.restart, Config.COLORS["orange"])
        self.add_button((470, 470, 340, 58), "QUIT TO MENU",
                        self.quit_to_menu, Config.COLORS["red"])

    def resume(self) -> None:
        if self.game.session:
            self.game.session.paused = False
        self.game.change_scene("game")

    def restart(self) -> None:
        session = self.game.session
        if session:
            self.game.start_session(session.mode, session.difficulty_name)

    def quit_to_menu(self) -> None:
        if self.game.session:
            self.game.session.finish("Exited to menu")
            self.game.finish_session()
        self.game.change_scene("menu")

    def draw(self, surface: pygame.Surface) -> None:
        self.game.draw_background(surface)
        overlay = pygame.Surface((Config.WIDTH, Config.HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 170))
        surface.blit(overlay, (0, 0))
        self.draw_title(surface, "GAME PAUSED", "Take a breath.")
        self.draw_buttons(surface)


# ============================================================================
# 16. RESULTS SCENE
# ============================================================================

class ResultsScene(Scene):
    """End-of-run report and rewards."""

    def enter(self) -> None:
        super().enter()
        self.summary = self.game.last_summary or {}
        self.add_button((350, 680, 250, 58), "PLAY AGAIN",
                        self.play_again, Config.COLORS["green"])
        self.add_button((630, 680, 250, 58), "MAIN MENU",
                        lambda: self.game.change_scene("menu"),
                        Config.COLORS["blue"])

    def play_again(self) -> None:
        summary = self.game.last_summary or {}
        self.game.start_session(
            summary.get("mode", "Campaign"),
            summary.get("difficulty", "Normal"),
        )

    def draw(self, surface: pygame.Surface) -> None:
        self.game.draw_background(surface)
        self.draw_title(surface, "RUN COMPLETE",
                        self.summary.get("reason", "Well played!"))
        score = self.summary.get("score", 0)
        draw_text(surface, self.game.fonts.get(64, True),
                  format_number(score), Config.COLORS["yellow"],
                  (640, 245), True)
        draw_text(surface, self.game.fonts.get(18, True),
                  "FINAL SCORE", Config.COLORS["muted"], (640, 300), True)

        stats = [
            ("Correct answers", self.summary.get("correct", 0)),
            ("Wrong answers", self.summary.get("wrong", 0)),
            ("Accuracy", f"{self.summary.get('accuracy', 0):.1f}%"),
            ("Best streak", self.summary.get("best_streak", 0)),
            ("Bosses defeated", self.summary.get("bosses", 0)),
            ("Time played", f"{self.summary.get('elapsed', 0):.1f}s"),
        ]
        for index, (label, value) in enumerate(stats):
            col = index % 2
            row = index // 2
            x = 330 + col * 340
            y = 365 + row * 82
            rect = pygame.Rect(x, y, 300, 62)
            rounded_rect(surface, Config.COLORS["panel"], rect, 10)
            draw_text(surface, self.game.fonts.get(15),
                      label, Config.COLORS["muted"],
                      (x + 15, y + 10))
            draw_text(surface, self.game.fonts.get(23, True),
                      str(value), Config.COLORS["white"],
                      (x + 15, y + 36))
        self.draw_buttons(surface)


# ============================================================================
# 17. PROFILE SCENE
# ============================================================================

class ProfileScene(Scene):
    """Player progression and statistics."""

    def enter(self) -> None:
        super().enter()
        self.name_input = TextInput(
            pygame.Rect(470, 210, 340, 48), self.game.profile.name
        )
        self.add_button((470, 280, 340, 48), "SAVE NAME",
                        self.save_name, Config.COLORS["green"])
        self.add_button((60, 710, 180, 48), "BACK",
                        lambda: self.game.change_scene("menu"),
                        Config.COLORS["panel_light"])

    def save_name(self) -> None:
        self.game.profile.name = self.name_input.value
        self.game.save_manager.save(self.game.profile)

    def handle_event(self, event: pygame.event.Event) -> None:
        self.name_input.handle_event(event)
        super().handle_event(event)

    def draw(self, surface: pygame.Surface) -> None:
        self.game.draw_background(surface)
        self.draw_title(surface, "PLAYER PROFILE",
                        "Your progress across all game modes")
        self.name_input.draw(surface, self.game.fonts)
        profile = self.game.profile
        xp_bar = ProgressBar(pygame.Rect(390, 390, 500, 24),
                             Config.COLORS["cyan"])
        xp_bar.value = profile.xp / max(1, profile.xp_for_next_level())
        xp_bar.label = f"XP {profile.xp}/{profile.xp_for_next_level()}"
        xp_bar.draw(surface, self.game.fonts)

        stats = [
            ("LEVEL", profile.level),
            ("COINS", format_number(profile.coins)),
            ("BEST SCORE", format_number(profile.best_score)),
            ("GAMES PLAYED", profile.data["games_played"]),
            ("QUESTIONS", profile.data["questions_answered"]),
            ("ACCURACY", f"{profile.accuracy():.1f}%"),
            ("BEST STREAK", profile.data["best_streak"]),
            ("TOTAL SCORE", format_number(profile.data["total_score"])),
        ]
        for index, (label, value) in enumerate(stats):
            col = index % 4
            row = index // 4
            x = 90 + col * 280
            y = 480 + row * 100
            rect = pygame.Rect(x, y, 250, 76)
            rounded_rect(surface, Config.COLORS["panel"], rect, 12)
            draw_text(surface, self.game.fonts.get(14, True),
                      label, Config.COLORS["muted"],
                      (x + 15, y + 14))
            draw_text(surface, self.game.fonts.get(25, True),
                      str(value), Config.COLORS["cyan"],
                      (x + 15, y + 48))
        self.draw_buttons(surface)


# ============================================================================
# 18. ACHIEVEMENTS SCENE
# ============================================================================

class AchievementsScene(Scene):
    """Display unlocked and locked achievements."""

    def enter(self) -> None:
        super().enter()
        self.add_button((60, 710, 180, 48), "BACK",
                        lambda: self.game.change_scene("menu"),
                        Config.COLORS["panel_light"])

    def draw(self, surface: pygame.Surface) -> None:
        self.game.draw_background(surface)
        self.draw_title(surface, "ACHIEVEMENTS",
                        "Complete challenges to earn bonus coins")
        unlocked = self.game.profile.data["achievements"]
        achievements = build_achievements()
        for index, achievement in enumerate(achievements):
            col = index % 2
            row = index // 2
            x = 130 + col * 530
            y = 165 + row * 100
            rect = pygame.Rect(x, y, 480, 82)
            is_unlocked = achievement.key in unlocked
            color = Config.COLORS["panel_light"] if is_unlocked else Config.COLORS["panel"]
            rounded_rect(surface, color, rect, 12)
            border = Config.COLORS["yellow"] if is_unlocked else (65, 75, 100)
            rounded_rect(surface, border, rect, 12, 2)
            title_color = Config.COLORS["yellow"] if is_unlocked else Config.COLORS["muted"]
            draw_text(surface, self.game.fonts.get(18, True),
                      achievement.title, title_color, (x + 18, y + 15))
            draw_text(surface, self.game.fonts.get(14),
                      achievement.description, Config.COLORS["white"],
                      (x + 18, y + 48))
            draw_text(surface, self.game.fonts.get(14, True),
                      f"+{achievement.reward} coins",
                      Config.COLORS["green"], (x + 370, y + 17))
        self.draw_buttons(surface)


# ============================================================================
# 19. SETTINGS SCENE
# ============================================================================

class SettingsScene(Scene):
    """Change local settings."""

    def enter(self) -> None:
        super().enter()
        self.add_button((60, 710, 180, 48), "BACK",
                        self.save_and_back, Config.COLORS["panel_light"])
        self.add_button((470, 600, 340, 52), "TOGGLE PARTICLES",
                        self.toggle_particles, Config.COLORS["purple"])
        self.add_button((470, 665, 340, 52), "TOGGLE TIMER",
                        self.toggle_timer, Config.COLORS["blue"])

    def toggle_particles(self) -> None:
        settings = self.game.profile.settings
        settings["particles"] = not settings.get("particles", True)

    def toggle_timer(self) -> None:
        settings = self.game.profile.settings
        settings["show_timer"] = not settings.get("show_timer", True)

    def save_and_back(self) -> None:
        self.game.save_manager.save(self.game.profile)
        self.game.change_scene("menu")

    def draw(self, surface: pygame.Surface) -> None:
        self.game.draw_background(surface)
        self.draw_title(surface, "SETTINGS",
                        "Customize your game experience")
        settings = self.game.profile.settings
        volume = settings.get("volume", 0.7)
        draw_text(surface, self.game.fonts.get(22, True),
                  f"VOLUME: {int(volume * 100)}%",
                  Config.COLORS["white"], (640, 250), True)
        bar = pygame.Rect(440, 300, 400, 22)
        rounded_rect(surface, (50, 60, 85), bar, 8)
        fill = pygame.Rect(bar.x, bar.y, int(bar.width * volume), bar.height)
        rounded_rect(surface, Config.COLORS["cyan"], fill, 8)
        draw_text(surface, self.game.fonts.get(17),
                  f"Particles: {'ON' if settings.get('particles') else 'OFF'}",
                  Config.COLORS["muted"], (640, 390), True)
        draw_text(surface, self.game.fonts.get(17),
                  f"Timer: {'ON' if settings.get('show_timer') else 'OFF'}",
                  Config.COLORS["muted"], (640, 430), True)
        draw_text(surface, self.game.fonts.get(14),
                  "Click the volume bar to change volume.",
                  Config.COLORS["muted"], (640, 480), True)
        self.draw_buttons(surface)

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            bar = pygame.Rect(440, 300, 400, 22)
            if bar.collidepoint(event.pos):
                value = clamp((event.pos[0] - bar.x) / bar.width, 0, 1)
                self.game.profile.settings["volume"] = value
                self.game.sound.set_volume(value)
        super().handle_event(event)


# ============================================================================
# 20. HELP SCENE
# ============================================================================

class HelpScene(Scene):
    """Explain controls, scoring and topics."""

    HELP_LINES = [
        "HOW TO PLAY",
        "Read the question and type your answer in the answer box.",
        "Press ENTER or click SUBMIT to check your answer.",
        "You can type whole numbers, decimals or fractions like 3/4.",
        "",
        "SCORING",
        "Correct answers earn points. Faster answers earn a speed bonus.",
        "Every four-answer streak increases your score multiplier.",
        "The multiplier is capped at x8.",
        "",
        "TOOLS",
        "HINT reveals a worked explanation. Each run starts with two hints.",
        "SKIP moves to another question. Each run starts with one skip.",
        "A shield blocks one wrong answer. Power-ups can grant more.",
        "",
        "BOSSES",
        "Campaign and Endless modes trigger a boss every ten questions.",
        "A boss has three health points. Correct answers damage the boss.",
        "",
        "TOPICS",
        "Arithmetic, fractions, powers, roots, algebra, geometry,",
        "trigonometry, probability, logarithms and introductory calculus.",
        "",
        "Press ESC to pause during a game.",
    ]

    def enter(self) -> None:
        super().enter()
        self.add_button((60, 710, 180, 48), "BACK",
                        lambda: self.game.change_scene("menu"),
                        Config.COLORS["panel_light"])

    def draw(self, surface: pygame.Surface) -> None:
        self.game.draw_background(surface)
        self.draw_title(surface, "HOW TO PLAY")
        y = 155
        for line in self.HELP_LINES:
            if line in ("HOW TO PLAY", "SCORING", "TOOLS", "BOSSES", "TOPICS"):
                color = Config.COLORS["cyan"]
                font = self.game.fonts.get(18, True)
            else:
                color = Config.COLORS["white"]
                font = self.game.fonts.get(15)
            draw_text(surface, font, line, color, (210, y))
            y += 25
        self.draw_buttons(surface)


# ============================================================================
# 21. GAME CONTROLLER
# ============================================================================

class MathsOverload:
    """Owns Pygame, global data, scenes and the main loop."""

    def __init__(self):
        pygame.init()
        pygame.display.set_caption(Config.TITLE)
        self.screen = pygame.display.set_mode(
            (Config.WIDTH, Config.HEIGHT)
        )
        self.clock = pygame.time.Clock()
        self.running = True
        self.fonts = FontBook()
        self.save_manager = SaveManager()
        self.profile = self.save_manager.load()
        self.sound = SoundManager(self.profile.settings.get("volume", 0.7))
        self.factory = QuestionFactory()
        self.particles = ParticleSystem()
        self.starfield = Starfield(Config.WIDTH, Config.HEIGHT)
        self.session: Optional[GameSession] = None
        self.last_summary: Optional[dict[str, Any]] = None
        self.scene_names = {
            "menu": MainMenu,
            "modes": ModeSelect,
            "game": GameplayScene,
            "pause": PauseScene,
            "results": ResultsScene,
            "profile": ProfileScene,
            "achievements": AchievementsScene,
            "settings": SettingsScene,
            "help": HelpScene,
        }
        self.scenes: dict[str, Scene] = {}
        self.current_scene: Optional[Scene] = None
        self.current_scene_name = ""
        self.change_scene("menu")

    def change_scene(self, name: str) -> None:
        """Switch scenes and run the new scene's enter hook."""
        if name not in self.scene_names:
            raise ValueError(f"Unknown scene: {name}")
        if name not in self.scenes:
            self.scenes[name] = self.scene_names[name](self)
        self.current_scene_name = name
        self.current_scene = self.scenes[name]
        self.current_scene.enter()

    def start_session(self, mode: str, difficulty: str) -> None:
        self.session = GameSession(mode, difficulty, self.factory)
        self.change_scene("game")

    def finish_session(self) -> None:
        """Award rewards once and show the results screen."""
        if not self.session:
            return
        if self.current_scene_name == "results":
            return
        session = self.session
        self.last_summary = session.summary()

        reward_xp = max(20, session.score // 10)
        reward_coins = max(5, session.score // 100)
        self.profile.add_xp(reward_xp)
        self.profile.add_coins(reward_coins)
        self.profile.record_game(session.score, session.mode)
        self.profile.data["bosses_defeated"] = (
            self.profile.data.get("bosses_defeated", 0)
            + session.bosses_defeated
        )

        achievement_manager = AchievementManager(self.profile)
        unlocked = achievement_manager.check()
        if unlocked:
            for achievement in unlocked:
                print("Achievement unlocked:", achievement.title)

        self.save_manager.save(self.profile)
        self.change_scene("results")

    def draw_background(self, surface: pygame.Surface) -> None:
        surface.fill(Config.COLORS["background"])
        self.starfield.draw(surface)
        # Soft decorative corner glows.
        pygame.draw.circle(surface, (20, 35, 70), (0, 0), 260)
        pygame.draw.circle(surface, (34, 20, 66),
                           (Config.WIDTH, Config.HEIGHT), 300)

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.QUIT:
            self.quit()
            return
        if event.type == pygame.KEYDOWN and event.key == pygame.K_F1:
            self.change_scene("help")
            return
        if self.current_scene:
            self.current_scene.handle_event(event)

    def update(self, dt: float) -> None:
        self.starfield.update(dt)
        self.particles.update(dt)
        if self.current_scene:
            self.current_scene.update(dt)

    def draw(self) -> None:
        if self.current_scene:
            self.current_scene.draw(self.screen)
        if self.profile.settings.get("particles", True):
            self.particles.draw(self.screen, self.fonts)
        pygame.display.flip()

    def run(self) -> None:
        while self.running:
            dt = min(self.clock.tick(Config.FPS) / 1000.0, 0.05)
            for event in pygame.event.get():
                self.handle_event(event)
            self.update(dt)
            self.draw()
        self.save_manager.save(self.profile)
        pygame.quit()

    def quit(self) -> None:
        self.running = False


# ============================================================================
# 22. EXTRA GAMEPLAY UTILITIES
# ============================================================================

class PowerUpShop:
    """A small data-driven shop for future menu integration."""

    ITEMS = {
        "hint_pack": {
            "name": "Hint Pack",
            "description": "Adds three hints to your next run.",
            "price": 100,
            "effect": "hints",
            "amount": 3,
        },
        "skip_pack": {
            "name": "Skip Pack",
            "description": "Adds two skips to your next run.",
            "price": 120,
            "effect": "skips",
            "amount": 2,
        },
        "shield": {
            "name": "Shield",
            "description": "Blocks one incorrect answer.",
            "price": 150,
            "effect": "shields",
            "amount": 1,
        },
        "double_points": {
            "name": "Double Points",
            "description": "Doubles points for three answers.",
            "price": 200,
            "effect": "double_score",
            "amount": 3,
        },
    }

    def __init__(self, profile: Profile):
        self.profile = profile

    def can_buy(self, item_key: str) -> bool:
        item = self.ITEMS.get(item_key)
        return bool(item and self.profile.coins >= item["price"])

    def buy(self, item_key: str) -> bool:
        item = self.ITEMS.get(item_key)
        if not item or not self.can_buy(item_key):
            return False
        self.profile.add_coins(-item["price"])
        return True

    def describe(self) -> list[str]:
        lines = []
        for key, item in self.ITEMS.items():
            lines.append(
                f"{key}: {item['name']} - {item['price']} coins"
            )
        return lines


class DailyChallenge:
    """Deterministic daily challenge seed."""

    def __init__(self, date_string: Optional[str] = None):
        self.date_string = date_string or time.strftime("%Y-%m-%d")
        self.seed = sum(
            (index + 1) * ord(character)
            for index, character in enumerate(self.date_string)
        )

    def create_factory(self) -> QuestionFactory:
        factory = QuestionFactory()
        factory.random.seed(self.seed)
        return factory

    def description(self) -> str:
        return f"Daily challenge for {self.date_string}"


class CampaignProgress:
    """Simple campaign stage progression model."""

    STAGES = [
        ("The Basics", "Arithmetic", 10),
        ("Fraction Forest", "Fractions", 10),
        ("Power Plant", "Powers", 10),
        ("Root Cavern", "Roots", 10),
        ("Algebra Academy", "Algebra", 12),
        ("Geometry Grid", "Geometry", 12),
        ("Trig Tower", "Trigonometry", 12),
        ("Probability Port", "Probability", 12),
        ("Logarithm Lab", "Logarithms", 15),
        ("Calculus Core", "Calculus", 15),
    ]

    def __init__(self, completed: Optional[list[int]] = None):
        self.completed = set(completed or [])

    def is_unlocked(self, index: int) -> bool:
        return index == 0 or (index - 1) in self.completed

    def complete(self, index: int) -> None:
        if 0 <= index < len(self.STAGES):
            self.completed.add(index)

    def progress(self) -> tuple[int, int]:
        return len(self.completed), len(self.STAGES)

    def next_stage(self) -> Optional[int]:
        for index in range(len(self.STAGES)):
            if self.is_unlocked(index) and index not in self.completed:
                return index
        return None


class Statistics:
    """Convenience calculations for the profile screen."""

    def __init__(self, profile: Profile):
        self.profile = profile

    def average_score(self) -> float:
        games = self.profile.data["games_played"]
        if games <= 0:
            return 0.0
        return self.profile.data["total_score"] / games

    def average_questions_per_game(self) -> float:
        games = self.profile.data["games_played"]
        if games <= 0:
            return 0.0
        return self.profile.data["questions_answered"] / games

    def rank_name(self) -> str:
        level = self.profile.level
        if level >= 50:
            return "Maths Legend"
        if level >= 30:
            return "Grandmaster"
        if level >= 20:
            return "Professor"
        if level >= 10:
            return "Scholar"
        if level >= 5:
            return "Apprentice"
        return "Rookie"

    def report(self) -> dict[str, Any]:
        return {
            "rank": self.rank_name(),
            "average_score": self.average_score(),
            "average_questions": self.average_questions_per_game(),
            "accuracy": self.profile.accuracy(),
            "best_score": self.profile.best_score,
        }


# ============================================================================
# 23. QUESTION VALIDATION AND TEST HELPERS
# ============================================================================

def validate_question(question: Question) -> bool:
    """Basic sanity check used during development."""
    if not question.prompt:
        return False
    if not isinstance(question.answer, (int, float)):
        return False
    if not math.isfinite(float(question.answer)):
        return False
    return True


def question_smoke_test(rounds: int = 100) -> dict[str, int]:
    """Generate many questions to catch malformed question templates."""
    factory = QuestionFactory()
    counts = {topic: 0 for topic in factory.TOPICS}
    for _ in range(rounds):
        question = factory.generate(random.randint(1, 8))
        if not validate_question(question):
            raise AssertionError(f"Invalid question: {question}")
        counts[question.topic] += 1
    return counts


def profile_smoke_test() -> bool:
    """Test level progression without touching the save file."""
    profile = Profile()
    profile.add_xp(1200)
    assert profile.level >= 2
    assert profile.coins >= 100
    profile.record_answer(True, 1)
    assert profile.accuracy() == 100
    return True


def run_development_tests() -> None:
    """Optional development tests; not run during normal gameplay."""
    print("Question generation test:", question_smoke_test())
    print("Profile test:", profile_smoke_test())


# ============================================================================
# 24. EXTENDED TOPIC REFERENCE
# ============================================================================

TOPIC_REFERENCE = {
    "Arithmetic": [
        "addition", "subtraction", "multiplication", "division",
        "order of operations", "integer arithmetic",
    ],
    "Fractions": [
        "simplifying fractions", "adding fractions",
        "subtracting fractions", "multiplying fractions",
        "decimal conversion", "fraction comparison",
    ],
    "Powers": [
        "integer exponents", "power of a power",
        "squared numbers", "cubed numbers",
    ],
    "Roots": [
        "square roots", "cube roots", "perfect squares",
    ],
    "Algebra": [
        "one-step equations", "two-step equations",
        "linear equations", "substitution",
    ],
    "Geometry": [
        "rectangle area", "triangle area", "circle area",
        "perimeter", "radius and diameter",
    ],
    "Trigonometry": [
        "sine", "cosine", "special angles",
    ],
    "Probability": [
        "simple probability", "percentage probability",
    ],
    "Logarithms": [
        "integer logarithms", "powers and logarithms",
    ],
    "Calculus": [
        "power rule", "derivative at a point",
    ],
}


def get_topic_reference(topic: str) -> list[str]:
    """Return the concepts represented by a topic."""
    return TOPIC_REFERENCE.get(topic, [])


def describe_all_topics() -> str:
    """Create a readable topic list for help or documentation."""
    output = []
    for topic, concepts in TOPIC_REFERENCE.items():
        output.append(topic + ": " + ", ".join(concepts))
    return "\n".join(output)


# ============================================================================
# 25. OPTIONAL COMMAND-LINE UTILITIES
# ============================================================================

def print_profile_report(profile: Profile) -> None:
    """Print profile details for debugging or command-line inspection."""
    stats = Statistics(profile).report()
    print("=" * 45)
    print("MATHS OVERLOAD PROFILE")
    print("=" * 45)
    print("Name:", profile.name)
    print("Rank:", stats["rank"])
    print("Level:", profile.level)
    print("Coins:", profile.coins)
    print("Games:", profile.data["games_played"])
    print("Questions:", profile.data["questions_answered"])
    print("Accuracy:", f"{stats['accuracy']:.2f}%")
    print("Average score:", f"{stats['average_score']:.1f}")
    print("Best score:", profile.best_score)
    print("=" * 45)


def reset_profile_confirmation() -> bool:
    """Ask for confirmation before deleting a local profile."""
    answer = input("Type RESET to erase the profile: ")
    return answer.strip() == "RESET"


def reset_profile() -> None:
    """Remove profile files after explicit confirmation."""
    if not reset_profile_confirmation():
        print("Reset cancelled.")
        return
    for path in (Config.SAVE_FILE, Config.BACKUP_FILE):
        try:
            if path.exists():
                path.unlink()
        except OSError as error:
            print("Could not remove", path, error)
    print("Profile reset.")


# ============================================================================
# 26. STARTUP
# ============================================================================

def main() -> None:
    """Launch the game."""
    try:
        game = MathsOverload()
        game.run()
    except pygame.error as error:
        print("Pygame could not start:", error)
        print("Try installing or updating Pygame:")
        print("python -m pip install --upgrade pygame")
    except KeyboardInterrupt:
        print("\nGame interrupted by user.")
    finally:
        if pygame.get_init():
            pygame.quit()


if __name__ == "__main__":
    main()


# ============================================================================
# 27. DEVELOPER REFERENCE: PUBLIC INTERFACES
# ============================================================================
#
# The following notes are kept in the source file so that someone learning
# Python can understand where to add new features. They are not required at
# runtime; they document the intended extension points.
#
# Adding a new mathematical topic:
#   1. Add the topic name to QuestionFactory.TOPICS.
#   2. Add a method to QuestionFactory that returns a Question.
#   3. Add the method to the makers dictionary in QuestionFactory.generate.
#   4. Add a description to TOPIC_REFERENCE.
#   5. Add the topic to any campaign stage that should use it.
#
# A question generator should always return a Question object. The answer
# should be a finite integer or float. The explanation should describe a
# reliable route to the answer, not merely repeat the answer.
#
# Adding a new scene:
#   1. Subclass Scene.
#   2. Implement enter() to create the screen's buttons.
#   3. Implement draw() to render the scene.
#   4. Implement handle_event() if the scene has custom input.
#   5. Register the class in MathsOverload.scene_names.
#   6. Navigate to it with game.change_scene("your_scene_key").
#
# Adding a power-up:
#   1. Add a data entry to PowerUpShop.ITEMS.
#   2. Add a method to GameSession if the effect needs new state.
#   3. Add a button to the shop scene.
#   4. Save any permanent ownership in Profile.data.
#
# Adding an achievement:
#   Add an Achievement to build_achievements(). Its condition receives the
#   current Profile object. The achievement key must remain stable after
#   release so existing save files continue to recognize it.
#
# Save-file compatibility:
#   Profile.DEFAULTS is merged with saved values when a profile loads. When
#   adding a new setting or statistic, add its default here. Avoid renaming
#   keys that may already exist in players' profile.json files.
#
# Timing:
#   Pygame reports frame duration in seconds. Scene.update(dt) and
#   GameSession.update(dt) use seconds, not milliseconds. Keep animations
#   frame-rate independent by multiplying movement by dt.
#
# Rendering:
#   Draw functions should not change gameplay state. State changes belong
#   in event handlers or update methods. This keeps redraws deterministic.
#
# Input:
#   Keyboard events arrive through pygame.KEYDOWN. Mouse coordinates use
#   the same coordinate system as the screen surface. Always check a button
#   with its rect before invoking its callback.
#
# Testing:
#   question_smoke_test() generates many questions and checks their shape.
#   profile_smoke_test() checks basic XP and accuracy behavior.
#   These can be called manually from a Python console:
#
#       import maths_overload_ultimate as game
#       game.run_development_tests()
#
# Suggested future modules if the project grows:
#   audio.py       music and sound effects
#   content.py     question banks and campaign data
#   entities.py    bosses, power-ups and particles
#   interface.py   reusable widgets and layout
#   persistence.py save files, backups and migrations
#   scenes.py      title, gameplay, pause and results screens
#   settings.py    configuration and user preferences
#
# Suggested art asset folders:
#   assets/fonts/
#   assets/images/backgrounds/
#   assets/images/icons/
#   assets/images/bosses/
#   assets/sounds/
#   assets/music/
#
# Suggested quality improvements:
#   - Add unit tests for every question generator.
#   - Add a proper answer-choice mode for younger players.
#   - Add keyboard navigation to every menu.
#   - Add a pause-safe timer and focus-loss handling.
#   - Add accessibility settings for text size and contrast.
#   - Add localization dictionaries for multiple languages.
#   - Add campaign save data and stage unlocks.
#   - Add a proper shop interface and inventory.
#   - Add a daily challenge result record.
#   - Add replay export as JSON.
#   - Add optional controller support.
#   - Add configurable key bindings.
#   - Add a tutorial that introduces one mechanic at a time.
#
# Mathematical accuracy notes:
#   - Geometry uses pi approximated to Python's math.pi.
#   - Trigonometry rounds the requested percentage to an integer.
#   - Probability rounds a percentage to the nearest integer.
#   - Calculus questions use the power rule for monomials.
#   - Fraction answers are checked numerically with a small tolerance.
#
# This game is an educational project, not a formal assessment tool.
# It is designed to be extended by adding more question types, scenes,
# content and visual effects.
#
# End of developer reference.
