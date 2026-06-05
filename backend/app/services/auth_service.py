"""认证 Service — 登录 / 注册 / 修改密码 / 个人信息"""
from sqlalchemy.ext.asyncio import AsyncSession

from app.repository.user_repo import UserRepository
from app.schemas.auth import (
    LoginRequest, RegisterRequest, ChangePasswordRequest,
    UpdateProfileRequest, UserInfoOut, LoginResponse,
)
from app.core.security import (
    hash_password, verify_password, create_access_token,
)
from app.core.exceptions import RecordNotFoundError, DuplicateEntryError, SkillError


class AuthService:
    def __init__(self):
        self.repo = UserRepository()

    @staticmethod
    def _to_user_info(user) -> UserInfoOut:
        return UserInfoOut(
            id=user.id,
            username=user.username,
            nickname=user.nickname,
            avatar=user.avatar,
            role=user.role,
            status=user.status,
        )

    async def register(self, db: AsyncSession, data: RegisterRequest) -> UserInfoOut:
        """注册新用户"""
        existing = await self.repo.find_by_username(db, data.username)
        if existing:
            raise DuplicateEntryError(f"用户名 '{data.username}' 已存在")

        user = await self.repo.create(db, {
            "username": data.username,
            "password_hash": hash_password(data.password),
            "nickname": data.nickname or data.username,
            "role": "user",
            "status": 1,
        })
        return self._to_user_info(user)

    async def login(self, db: AsyncSession, data: LoginRequest) -> LoginResponse:
        """登录，返回 JWT token + 用户信息"""
        user = await self.repo.find_by_username(db, data.username)
        if not user:
            raise SkillError("用户名或密码错误")

        if not verify_password(data.password, user.password_hash):
            raise SkillError("用户名或密码错误")

        if user.status != 1:
            raise SkillError("账号已被禁用")

        token = create_access_token(data={"user_id": user.id, "sub": str(user.id)})
        return LoginResponse(token=token, user=self._to_user_info(user))

    async def get_current_user(self, db: AsyncSession, user_id: int) -> UserInfoOut:
        """获取当前登录用户信息"""
        user = await self.repo.find_by_id(db, user_id)
        if not user:
            raise RecordNotFoundError("用户不存在")
        return self._to_user_info(user)

    async def change_password(
        self, db: AsyncSession, user_id: int, data: ChangePasswordRequest,
    ) -> bool:
        """修改密码"""
        user = await self.repo.find_by_id(db, user_id)
        if not user:
            raise RecordNotFoundError("用户不存在")

        if not verify_password(data.old_password, user.password_hash):
            raise SkillError("旧密码错误")

        await self.repo.update(db, user_id, {
            "password_hash": hash_password(data.new_password),
        })
        return True

    async def update_profile(
        self, db: AsyncSession, user_id: int, data: UpdateProfileRequest,
    ) -> UserInfoOut:
        """更新个人信息"""
        user = await self.repo.find_by_id(db, user_id)
        if not user:
            raise RecordNotFoundError("用户不存在")

        update_data = data.model_dump(exclude_unset=True)
        if update_data:
            await self.repo.update(db, user_id, update_data)
            user = await self.repo.find_by_id(db, user_id)

        return self._to_user_info(user)


# 单例
auth_service = AuthService()
