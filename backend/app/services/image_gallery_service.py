"""图片画廊 Service"""
import os
import random
import logging
import httpx
from typing import List, Optional, Tuple
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from app.repository.image_gallery_repo import ImageGalleryRepository
from app.schemas.image_gallery import (
    ImageGalleryCreate, ImageGalleryUpdate, ImageGalleryOut,
    ImageGenerateRequest,
)
from app.schemas.expert_team import PolishPromptRequest
from app.services.expert_team_service import _call_llm
from app.core.exceptions import RecordNotFoundError

logger = logging.getLogger(__name__)

# 古风名字元素 — 侠风 / 温婉 / 诗意
侠风 = ["剑", "刀", "影", "魂", "魄", "刃", "锋", "啸", "吟", "诀", "令", "引"]
温婉 = ["烟", "雨", "雪", "露", "霜", "霞", "云", "月", "风", "花", "梦", "影"]
诗意 = ["吟", "赋", "颂", "谣", "曲", "词", "章", "句", "韵", "律", "调", "声"]
意境 = ["山", "水", "林", "溪", "谷", "崖", "泉", "湖", "海", "江", "河", "涧", "潭", "汀", "洲"]
后缀_侠 = ["阁", "庐", "轩", "居", "舍", "堂", "院", "馆", "亭", "楼", "台", "榭"]
后缀_温 = ["斋", "苑", "圃", "居", "轩", "阁", "庐", "舍", "堂", "院", "馆", "亭"]

# 图片存储目录
IMAGE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "uploads", "images")


def _generate_ancient_name(prompt: str = "") -> str:
    """根据提示词摘取意境词，生成古风名字"""
    意境映射 = {
        "海": ["沧海", "碧海", "海潮", "海风", "浪花", "潮生", "海天", "碧波"],
        "山": ["青山", "云山", "山岚", "山色", "峰峦", "山间", "远山", "翠峰"],
        "林": ["林深", "翠林", "幽林", "林间", "林海", "绿林", "密林", "松林"],
        "雪": ["飞雪", "雪落", "霜雪", "雪霁", "寒雪", "初雪", "雪影", "白雪"],
        "月": ["月明", "月华", "月色", "月影", "月光", "明月", "月夜", "皓月"],
        "花": ["花落", "花开", "花影", "花间", "落花", "花雨", "花期", "繁花"],
        "雨": ["烟雨", "听雨", "雨落", "细雨", "雨声", "暮雨", "雨后", "春雨"],
        "风": ["清风", "风吟", "风起", "风动", "微风", "风过", "长风", "风华"],
        "夜": ["夜色", "夜阑", "夜深", "星夜", "月夜", "夜静", "长夜", "夜幕"],
        "春": ["春晓", "春意", "春色", "春暖", "春雨", "春山", "春水", "春归"],
        "夏": ["盛夏", "夏夜", "夏风", "夏日", "夏雨", "夏荷", "夏蝉", "夏至"],
        "秋": ["秋水", "秋色", "秋意", "秋风", "秋月", "秋叶", "秋韵", "深秋"],
        "冬": ["寒冬", "冬雪", "冬日", "冬梅", "冬夜", "冬至", "严冬", "初冬"],
        "星": ["星河", "星辰", "星空", "星辉", "繁星", "星夜", "流星", "星光"],
        "云": ["云卷", "云舒", "云间", "白云", "云影", "云深", "云海", "浮云"],
        "竹": ["竹影", "竹林", "竹韵", "翠竹", "竹间", "修竹", "竹风", "竹露"],
        "松": ["松风", "松涛", "青松", "松间", "古松", "松影", "松韵", "松下"],
        "梅": ["梅影", "梅开", "寒梅", "梅香", "梅花", "梅间", "红梅", "梅雪"],
        "湖": ["湖光", "湖畔", "湖影", "碧湖", "湖心", "平湖", "湖色", "湖面"],
        "剑": ["剑影", "剑吟", "剑气", "剑意", "剑魄", "剑魂", "剑锋", "剑啸"],
        "龙": ["龙吟", "龙影", "龙魂", "龙腾", "龙渊", "龙啸", "游龙", "龙息"],
        "仙": ["仙踪", "仙气", "仙影", "仙居", "仙境", "仙鹤", "仙山", "仙露"],
        "城": ["古城", "城楼", "城郭", "城外", "城墙", "城影", "城门", "都城"],
        "酒": ["酒香", "酒意", "酒醉", "酒壶", "酒楼", "酒旗", "酒肆", "醉酒"],
        "琴": ["琴音", "琴声", "琴韵", "琴弦", "琴心", "琴瑟", "听琴", "抚琴"],
        "书": ["书香", "书卷", "书斋", "书阁", "书生", "书墨", "读书", "古书"],
        "画": ["画意", "画境", "画中", "画卷", "画师", "画笔", "画屏", "丹青"],
        "猫": ["狸奴", "猫影", "猫步", "猫眼", "猫耳", "猫爪", "猫眠", "猫步"],
        "人": ["佳人", "故人", "行人", "丽人", "伊人", "良人", "人间", "红尘"],
        "女": ["少女", "女侠", "仙子", "佳人", "伊人", "丽人", "红颜", "娇娘"],
        "男": ["少年", "公子", "侠客", "书生", "将军", "隐士", "行者", "游侠"],
        "美": ["美景", "美好", "美妙", "美色", "美意", "美境", "美轮", "美奂"],
        "森": ["森然", "森林", "森罗", "森森", "幽森", "森木", "森绿", "森野"],
        "火": ["火焰", "火光", "火舞", "火花", "烈火", "火凤", "火莲", "火龙"],
        "光": ["光芒", "光影", "光华", "光辉", "光耀", "流光", "曙光", "晨光"],
        "暗": ["暗影", "暗夜", "暗香", "暗流", "暗涌", "暗光", "暗色", "暗幕"],
        "天": ["天际", "天边", "天色", "天空", "天涯", "天穹", "天幕", "天光"],
        "地": ["大地", "地平", "地阔", "地远", "地广", "地宽", "地深", "地厚"],
        "古": ["古道", "古风", "古意", "古韵", "古朴", "古色", "古香", "古雅"],
        "今": ["今朝", "今日", "今夕", "今夜", "今时", "今宵", "今晨", "今夏"],
    }
    后缀池 = ["居", "轩", "阁", "斋", "庐", "舍", "堂", "院", "馆", "亭", "台", "楼", "榭", "苑", "圃", "坞", "筑", "坊"]

    prompt_lower = prompt.lower()
    matched = []
    for keyword, options in 意境映射.items():
        if keyword in prompt_lower:
            matched.extend(options)

    if matched:
        chosen = random.sample(matched, min(2, len(matched)))
        return "".join(chosen) + random.choice(后缀池)
    else:
        随机词 = ["清风", "明月", "流水", "白云", "青山", "碧水", "幽兰", "翠竹", "飞花", "落雪"]
        return random.choice(随机词) + random.choice(后缀池)


def _ensure_image_dir():
    """确保图片目录存在"""
    os.makedirs(IMAGE_DIR, exist_ok=True)


class ImageGalleryService:
    """图片画廊 Service"""

    def __init__(self):
        self.repo = ImageGalleryRepository()

    async def list_images(
        self, db: AsyncSession, page: int = 1, page_size: int = 20,
        tag: Optional[str] = None, enabled: Optional[int] = None,
    ) -> Tuple[List[ImageGalleryOut], int]:
        """获取图片列表"""
        offset = (page - 1) * page_size
        items = await self.repo.find_all(db, offset=offset, limit=page_size, tag=tag, enabled=enabled)
        total = await self.repo.count(db, tag=tag, enabled=enabled)
        return [ImageGalleryOut.model_validate(i) for i in items], total

    async def get_image(self, db: AsyncSession, image_id: int) -> ImageGalleryOut:
        """获取图片详情"""
        image = await self.repo.find_by_id(db, image_id)
        if not image:
            raise RecordNotFoundError("图片不存在")
        return ImageGalleryOut.model_validate(image)

    async def list_tags(self, db: AsyncSession) -> List[str]:
        """获取所有标签"""
        return await self.repo.find_all_tags(db)

    async def create_image(self, db: AsyncSession, data: ImageGalleryCreate) -> ImageGalleryOut:
        """创建图片记录"""
        name = data.name or _generate_ancient_name(data.prompt)
        image_data = data.model_dump()
        image_data["name"] = name
        image = await self.repo.create(db, image_data)
        return ImageGalleryOut.model_validate(image)

    async def update_image(self, db: AsyncSession, image_id: int, data: ImageGalleryUpdate) -> ImageGalleryOut:
        """更新图片"""
        image = await self.repo.find_by_id(db, image_id)
        if not image:
            raise RecordNotFoundError("图片不存在")
        update_data = data.model_dump(exclude_unset=True)
        if update_data:
            image = await self.repo.update(db, image_id, update_data)
        return ImageGalleryOut.model_validate(image)

    async def delete_image(self, db: AsyncSession, image_id: int) -> bool:
        """删除图片（仅软删除数据库记录，保留文件）"""
        image = await self.repo.find_by_id(db, image_id)
        if not image:
            raise RecordNotFoundError("图片不存在")
        return await self.repo.soft_delete(db, image_id)

    async def generate_prompt(self, db: AsyncSession, data: PolishPromptRequest) -> str:
        """根据用户简短描述，联网搜索参考资料，生成中文图片生成提示词"""
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

        # 联网搜索参考资料
        search_context = ""
        try:
            from duckduckgo_search import DDGS
            with DDGS() as ddgs:
                results = list(ddgs.text(data.content, max_results=5))
                if results:
                    search_context = "\n".join([f"- {r.get('title', '')}: {r.get('body', '')}" for r in results[:3]])
        except Exception as e:
            logger.warning(f"联网搜索失败（不影响生成）: {e}")

        polish_system = (
            "你是 AI 绘图提示词专家。根据用户简短描述和联网搜索到的参考资料，生成高质量的中文图片生成提示词。\n"
            "要求：\n"
            "- 用中文输出\n"
            "- 包含主体特征、环境背景、光影氛围、镜头语言、画质修饰等细节描述\n"
            "- 描述要具体、生动、有画面感\n"
            "- 不要输出任何标题、解释或前缀，直接返回提示词正文\n"
            "- 200-400 字为宜"
        )
        search_block = f"\n\n联网搜索参考资料：\n{search_context}" if search_context else ""
        prompt = f"{polish_system}\n\n用户描述：\n{data.content}{search_block}"
        content, _ = await _call_llm(db, provider.id, model_name, prompt, temperature=0.5)
        return content.strip()

    async def generate_image(self, db: AsyncSession, data: ImageGenerateRequest) -> dict:
        """生成图片 — 调用大模型 API"""
        from app.services.llm_provider_service import LLMProviderService
        provider_service = LLMProviderService()

        # 始终使用默认供应商（重新生成时存储的 provider 可能已变更）
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

        _ensure_image_dir()
        image_name = _generate_ancient_name(data.prompt)
        file_name = f"{image_name}_{int(datetime.now().timestamp() * 1000)}.png"
        file_path = os.path.join(IMAGE_DIR, file_name)

        # 调用图片生成 API
        try:
            image_data = await self._call_image_api(
                provider=provider,
                model_name=model_name,
                prompt=data.prompt,
                negative_prompt=data.negative_prompt,
                width=data.width,
                height=data.height,
            )
            # 保存图片
            with open(file_path, "wb") as f:
                f.write(image_data)
        except Exception as e:
            logger.error(f"图片生成失败: {e}")
            raise ValueError(f"图片生成失败: {e}")

        return {
            "name": image_name,
            "file_path": file_path,
            "thumbnail_path": file_path,
            "width": data.width,
            "height": data.height,
        }

    async def _call_image_api(
        self, provider, model_name: str, prompt: str,
        negative_prompt: str = "", width: int = 1024, height: int = 1024,
    ) -> bytes:
        """调用图片生成 API"""
        import base64
        api_key = provider.api_key or ""
        base_url = (provider.base_url or "https://api.openai.com/v1").rstrip("/")

        # SD WebUI 专用接口
        if "/sdapi" in base_url:
            url = f"{base_url}/txt2img"
            headers = {}
            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"
            payload = {
                "prompt": prompt,
                "negative_prompt": negative_prompt,
                "width": width,
                "height": height,
                "steps": 30,
                "cfg_scale": 7,
            }
            async with httpx.AsyncClient(timeout=120) as client:
                resp = await client.post(url, json=payload, headers=headers)
                resp.raise_for_status()
                result = resp.json()
                images = result.get("images", [])
                if not images:
                    raise ValueError("API 未返回图片数据")
                return base64.b64decode(images[0])

        # 默认走 OpenAI DALL-E 兼容接口（绝大多数供应商兼容）
        url = f"{base_url}/images/generations"
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        payload = {
            "model": model_name,
            "prompt": prompt,
            "size": f"{width}x{height}",
            "return_base64": True,
        }
        if negative_prompt:
            payload["negative_prompt"] = negative_prompt

        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(url, json=payload, headers=headers)
            if resp.status_code != 200:
                try:
                    err = resp.json()
                    msg = err.get("error", {}).get("message", str(err))
                except Exception:
                    msg = resp.text
                raise ValueError(f"图片生成失败: {msg}")
            result = resp.json()
            return base64.b64decode(result["data"][0]["b64_json"])
