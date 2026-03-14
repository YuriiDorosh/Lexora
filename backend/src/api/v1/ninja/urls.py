from ninja_extra import NinjaExtraAPI
from ninja_jwt.controller import NinjaJWTDefaultController
from src.api.v1.ninja.establishment.handlers import EstablishmentController
from src.api.v1.ninja.auth.handlers import AuthController

api = NinjaExtraAPI()

api.register_controllers(
    NinjaJWTDefaultController,
    EstablishmentController,
    AuthController,
)
