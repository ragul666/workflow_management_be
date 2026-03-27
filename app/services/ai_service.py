import uuid

from groq import AsyncGroq
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import settings
from app.models.ai_summary import AISummary


class AIService:
    def __init__(self):
        self._client = None

    @property
    def client(self) -> AsyncGroq:
        if self._client is None:
            self._client = AsyncGroq(api_key=settings.GROQ_API_KEY)
        return self._client

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def _call_llm(self, prompt: str) -> str:
        response = await self.client.chat.completions.create(
            model="llama-3.1-70b-versatile",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an expert compliance analyst. Generate a concise root cause analysis "
                        "summary for the given issue. Include: potential root causes, contributing factors, "
                        "recommended corrective actions, and preventive measures."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            max_tokens=1000,
        )
        return response.choices[0].message.content

    async def generate_summary(
        self,
        db: AsyncSession,
        issue_id: uuid.UUID,
        issue_title: str,
        issue_description: str,
        user_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> AISummary:
        prompt = f"Issue Title: {issue_title}\n\nDescription: {issue_description}"

        try:
            content = await self._call_llm(prompt)
        except Exception as e:
            content = f"AI summary generation failed: {str(e)}. Please try again later."

        version_result = await db.execute(
            select(func.coalesce(func.max(AISummary.version), 0))
            .where(AISummary.issue_id == issue_id)
        )
        current_max = version_result.scalar()

        summary = AISummary(
            issue_id=issue_id,
            version=current_max + 1,
            content=content,
            model_used="llama-3.1-70b-versatile",
            generated_by=user_id,
            tenant_id=tenant_id,
        )
        db.add(summary)
        await db.flush()
        return summary


ai_service = AIService()
