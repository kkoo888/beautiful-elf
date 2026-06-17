"""视频画廊 Service"""
import os
import random
import logging
import httpx
from typing import List, Optional, Tuple
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from app.repository.video_gallery_repo import VideoGalleryRepository
from app.schemas.video_gallery import (
    VideoGalleryCreate, VideoGalleryUpdate, VideoGalleryOut,
    VideoGenerateRequest,
)
from app.core.exceptions import RecordNotFoundError
from app.services.expert_team_service import _call_llm

logger = logging.getLogger(__name__)

# 视频存储目录
VIDEO_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "uploads", "videos")


def _generate_video_name(prompt: str = "") -> str:
    """根据提示词生成视频名称"""
    adjectives = ["璀璨", "梦幻", "流光", "星河", "晨曦", "暮色", "清风", "烟雨", "流云", "飞雪"]
    nouns = ["影像", "短片", "视界", "画面", "光影", "瞬间", "印象", "片段", "场景", "记录"]
    return random.choice(adjectives) + random.choice(nouns)


def _ensure_video_dir():
    """确保视频目录存在"""
    os.makedirs(VIDEO_DIR, exist_ok=True)


class VideoGalleryService:
    """视频画廊 Service"""

    def __init__(self):
        self.repo = VideoGalleryRepository()

    async def list_videos(
        self, db: AsyncSession, page: int = 1, page_size: int = 20,
        tag: Optional[str] = None, enabled: Optional[int] = None,
    ) -> Tuple[List[VideoGalleryOut], int]:
        """获取视频列表"""
        offset = (page - 1) * page_size
        items = await self.repo.find_all(db, offset=offset, limit=page_size, tag=tag, enabled=enabled)
        total = await self.repo.count(db, tag=tag, enabled=enabled)
        return [VideoGalleryOut.model_validate(i) for i in items], total

    async def get_video(self, db: AsyncSession, video_id: int) -> VideoGalleryOut:
        """获取视频详情"""
        video = await self.repo.find_by_id(db, video_id)
        if not video:
            raise RecordNotFoundError("视频不存在")
        return VideoGalleryOut.model_validate(video)

    async def list_tags(self, db: AsyncSession) -> List[str]:
        """获取所有标签"""
        return await self.repo.find_all_tags(db)

    async def create_video(self, db: AsyncSession, data: VideoGalleryCreate) -> VideoGalleryOut:
        """创建视频记录"""
        name = data.name or _generate_video_name(data.prompt)
        video_data = data.model_dump()
        video_data["name"] = name
        video = await self.repo.create(db, video_data)
        return VideoGalleryOut.model_validate(video)

    async def update_video(self, db: AsyncSession, video_id: int, data: VideoGalleryUpdate) -> VideoGalleryOut:
        """更新视频"""
        video = await self.repo.find_by_id(db, video_id)
        if not video:
            raise RecordNotFoundError("视频不存在")
        update_data = data.model_dump(exclude_unset=True)
        if update_data:
            video = await self.repo.update(db, video_id, update_data)
        return VideoGalleryOut.model_validate(video)

    async def delete_video(self, db: AsyncSession, video_id: int) -> bool:
        """删除视频（软删除）"""
        video = await self.repo.find_by_id(db, video_id)
        if not video:
            raise RecordNotFoundError("视频不存在")
        return await self.repo.soft_delete(db, video_id)

    async def generate_video_prompt(self, db: AsyncSession, data) -> str:
        """根据用户简短描述，生成视频生成提示词（英文，符合 Agnes Video V2.0 最佳实践）"""
        from app.services.llm_provider_service import LLMProviderService
        provider_service = LLMProviderService()
        provider = await provider_service.get_default_provider(db)
        if not provider:
            raise ValueError("请先在设置中配置默认 AI 供应商")
        model_name = ""
        if provider.models:
            enabled_models = [m for m in provider.models if m.is_enabled == 1]
            if enabled_models:
                model_name = enabled_models[0].model_name
        if not model_name:
            raise ValueError("没有可用的模型")

        polish_system = (
            "You are an expert video generation prompt engineer for Agnes Video V2.0.\n"
            "Based on the user's short description, generate a high-quality English video generation prompt.\n\n"
            "IMPORTANT: Output MUST be in English. The model works best with English prompts.\n\n"
            "Recommended structure:\n"
            "[Subject] + [Action] + [Scene] + [Camera Movement] + [Lighting] + [Style]\n\n"
            "Examples by use case:\n"
            "- Text-to-video: 'A young astronaut walking across a red desert planet, dust blowing in the wind, slow cinematic tracking shot, dramatic sunset lighting, realistic sci-fi style'\n"
            "- Image-to-video: 'Animate the character with subtle breathing motion, hair moving gently in the wind, background lights flickering softly, while keeping the face and outfit consistent'\n"
            "- Multi-image: 'Use the first image as the starting scene and the second image as the target scene. Create a smooth transformation with consistent lighting, natural motion, and cinematic pacing'\n"
            "- Keyframes: 'Create a smooth transition from the first keyframe to the second keyframe, maintaining character identity, consistent camera angle, and natural motion between scenes'\n\n"
            "Requirements:\n"
            "- Output in English only\n"
            "- Include specific details about motion, camera movement, and visual style\n"
            "- 50-150 words, concise and vivid\n"
            "- Do NOT include any titles, explanations, or prefixes — return only the prompt text\n"
            "- For video, emphasize MOTION and TEMPORAL changes (what moves, how it changes over time)\n"
        )

        prompt = f"{polish_system}\n\nUser description:\n{data.content}"
        content, _ = await _call_llm(db, provider.id, model_name, prompt, temperature=0.5)
        return content.strip()

    async def generate_video(self, db: AsyncSession, data: VideoGenerateRequest) -> dict:
        """生成视频 — 调用 Agnes Video API"""
        from app.services.llm_provider_service import LLMProviderService
        provider_service = LLMProviderService()

        provider = await provider_service.get_default_provider(db)
        if not provider:
            raise ValueError("请先在设置中配置默认 AI 供应商")

        model_name = data.model_name
        if not model_name and provider.models:
            enabled_models = [m for m in provider.models if m.is_enabled == 1]
            if enabled_models:
                model_name = enabled_models[0].model_name
        if not model_name:
            raise ValueError("没有可用的模型")

        _ensure_video_dir()
        video_name = _generate_video_name(data.prompt)
        file_name = f"{video_name}_{int(datetime.now().timestamp() * 1000)}.mp4"
        file_path = os.path.join(VIDEO_DIR, file_name)

        try:
            video_url, api_duration, size_str = await self._call_video_api(
                provider=provider,
                model_name=model_name,
                prompt=data.prompt,
                negative_prompt=data.negative_prompt,
                image=data.image,
                images=data.images,
                mode=data.mode,
                width=data.width,
                height=data.height,
                num_frames=data.num_frames,
                frame_rate=data.frame_rate,
                num_inference_steps=data.num_inference_steps,
                seed=data.seed,
            )
            # 下载视频文件
            # CDN 返回的 URL 不需要鉴权（预签名 URL 或公开 CDN），带 Bearer token 反而 401
            async with httpx.AsyncClient(timeout=300, follow_redirects=True) as client:
                resp = await client.get(video_url)
                resp.raise_for_status()
                content = resp.content
                # 校验下载内容是否为视频（不是 JSON 错误）
                if content[:1] in (b'{', b'['):
                    try:
                        err = __import__('json').loads(content)
                        raise ValueError(f"下载的不是视频文件，API 返回: {err.get('error', {}).get('message', str(err))[:200]}")
                    except (ValueError, KeyError):
                        pass
                if len(content) < 1024:
                    raise ValueError(f"下载的视频文件过小（{len(content)} bytes），可能不是有效视频")
                # 根据 Content-Type 修正文件扩展名
                content_type = resp.headers.get("content-type", "")
                ext = os.path.splitext(file_path)[1]
                if "webm" in content_type:
                    ext = ".webm"
                elif "mov" in content_type or "quicktime" in content_type:
                    ext = ".mov"
                elif "mp4" in content_type:
                    ext = ".mp4"
                if ext != os.path.splitext(file_path)[1]:
                    file_path = file_path.rsplit(".", 1)[0] + ext
                    file_name = file_name.rsplit(".", 1)[0] + ext
                with open(file_path, "wb") as f:
                    f.write(content)
        except Exception as e:
            logger.error(f"视频生成失败: {e}")
            raise ValueError(f"视频生成失败: {e}")

        # 优先使用 API 返回的时长，否则自行计算
        duration = api_duration if api_duration > 0 else (data.num_frames / data.frame_rate if data.frame_rate > 0 else 0)

        return {
            "name": video_name,
            "file_path": file_name,
            "thumbnail_path": "",
            "width": data.width,
            "height": data.height,
            "num_frames": data.num_frames,
            "frame_rate": data.frame_rate,
            "duration": round(duration, 2),
        }

    async def _call_video_api(
        self, provider, model_name: str, prompt: str,
        negative_prompt: str = "", image: Optional[str] = None,
        images: Optional[List[str]] = None, mode: Optional[str] = None,
        width: int = 1152, height: int = 768,
        num_frames: int = 121, frame_rate: float = 24,
        num_inference_steps: Optional[int] = None,
        seed: Optional[int] = None,
    ) -> tuple:
        """调用视频生成 API，返回 (video_url, duration, size_str)"""
        api_key = provider.api_key or ""
        base_url = (provider.base_url or "https://apihub.agnes-ai.com/v1").rstrip("/")

        # 构建请求体
        payload = {
            "model": model_name,
            "prompt": prompt,
            "height": height,
            "width": width,
            "num_frames": num_frames,
            "frame_rate": int(frame_rate) if frame_rate == int(frame_rate) else frame_rate,
        }
        if negative_prompt:
            payload["negative_prompt"] = negative_prompt
        if num_inference_steps is not None:
            payload["num_inference_steps"] = num_inference_steps
        if seed is not None:
            payload["seed"] = seed

        # 图生视频：单图
        if image:
            payload["image"] = image
            if mode:
                payload["mode"] = mode

        # 多图/关键帧模式
        if images:
            payload["extra_body"] = {
                "image": images,
            }
            if mode:
                payload["extra_body"]["mode"] = mode

        url = f"{base_url}/videos"
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

        async with httpx.AsyncClient(timeout=300) as client:
            resp = await client.post(url, json=payload, headers=headers)
            if resp.status_code != 200:
                try:
                    err = resp.json()
                    msg = err.get("error", {}).get("message", str(err))
                except Exception:
                    msg = resp.text[:500]
                raise ValueError(f"视频生成失败: {msg}")

            result = resp.json()

        # 轮询获取结果（异步任务模式）
        task_id = result.get("id") or result.get("task_id")
        if task_id:
            video_url, duration, size = await self._poll_video_task(base_url, api_key, task_id)
            return video_url, duration, size

        # 直接返回 URL
        data_item = result.get("data", result)
        if isinstance(data_item, list) and data_item:
            data_item = data_item[0]
        video_url = data_item.get("remixed_from_video_id") or data_item.get("url") or data_item.get("video_url") or ""
        if not video_url:
            raise ValueError("API 未返回视频 URL")
        duration = float(data_item.get("seconds", 0) or 0)
        size_str = data_item.get("size", "")
        return video_url, duration, size_str

    async def _poll_video_task(self, base_url: str, api_key: str, task_id: str) -> tuple:
        """轮询视频生成任务状态，返回 (video_url, duration, size_str)"""
        url = f"{base_url}/videos/{task_id}"
        headers = {"Authorization": f"Bearer {api_key}"}

        import asyncio
        for _ in range(120):  # 最多等待 10 分钟
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(url, headers=headers)
                if resp.status_code != 200:
                    await asyncio.sleep(5)
                    continue
                result = resp.json()
                status = result.get("status", "")
                if status == "completed":
                    video_url = result.get("remixed_from_video_id") or ""
                    if not video_url:
                        raise ValueError("任务完成但未返回视频 URL")
                    duration = float(result.get("seconds", 0) or 0)
                    size_str = result.get("size", "")
                    return video_url, duration, size_str
                elif status == "failed":
                    error_msg = result.get("error", {})
                    if isinstance(error_msg, dict):
                        error_msg = error_msg.get("message", "未知错误")
                    raise ValueError(f"视频生成失败: {error_msg}")
            await asyncio.sleep(5)

        raise ValueError("视频生成超时")
