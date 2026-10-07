from supabase import Client
from typing import Optional, Dict, Any
from datetime import datetime


class ScoringService:
    def __init__(self, supabase: Client):
        self.supabase = supabase

    async def calculate_points(self, question_id: str, response_time_ms: int, is_correct: bool) -> float:
        """Calculate points for a submission based on scoring config."""
        # Get question with scoring config
        question_result = self.supabase.from_('questions').select('*, rounds(game_id)').eq('id', question_id).single().execute()
        question = question_result.data

        if not is_correct:
            return 0.0

        # Get scoring config
        scoring_config = question.get('scoring_config', {})
        mode = scoring_config.get('mode', 'speed')

        if mode == 'speed':
            return await self._calculate_speed_points(scoring_config, response_time_ms)
        elif mode == 'fixed':
            return scoring_config.get('fixed_points', 100.0)
        elif mode == 'accuracy':
            return 100.0 if is_correct else 0.0
        elif mode == 'manual':
            return scoring_config.get('manual_points', 100.0)
        else:
            # Default speed scoring
            return await self._calculate_speed_points(scoring_config, response_time_ms)

    async def _calculate_speed_points(self, scoring_config: dict, response_time_ms: int) -> float:
        """Calculate points based on speed tiers."""
        tiers = scoring_config.get('tiers', [])

        if not tiers:
            # Default tiers
            tiers = [
                {"maxMs": 3000, "points": 100},
                {"maxMs": 6000, "points": 80},
                {"maxMs": 10000, "points": 60},
                {"maxMs": 20000, "points": 40},
            ]

        # Find the appropriate tier
        points = 0
        for tier in tiers:
            if response_time_ms <= tier['maxMs']:
                points = tier['points']
                break
        else:
            # If time exceeds all tiers, give minimum points
            points = tiers[-1]['points'] if tiers else 0

        return float(points)

    async def get_scoring_config(self, question_id: str) -> dict:
        """Get scoring config for a question."""
        question_result = self.supabase.from_('questions').select('scoring_config').eq('id', question_id).single().execute()
        return question_result.data.get('scoring_config', {}) if question_result.data else {}