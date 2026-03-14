from django.contrib.auth import get_user_model
from django.db import IntegrityError
from ninja.errors import HttpError
from ninja_extra import api_controller, route

from .schemas import RegisterSchema, RegisterResponseSchema

User = get_user_model()


@api_controller("/auth", tags=["Auth"])
class AuthController:
    @route.post("/register", response=RegisterResponseSchema)
    def register(self, payload: RegisterSchema):
        if payload.password != payload.password_confirm:
            raise HttpError(400, "Passwords do not match.")

        if User.objects.filter(username=payload.username).exists():
            raise HttpError(400, "Username already exists.")

        if User.objects.filter(email=payload.email).exists():
            raise HttpError(400, "Email already exists.")

        try:
            user = User.objects.create_user(
                username=payload.username,
                email=payload.email,
                password=payload.password,
            )
        except IntegrityError:
            raise HttpError(400, "User could not be created.")

        return RegisterResponseSchema(
            id=user.id,
            username=user.username,
            email=user.email,
        )