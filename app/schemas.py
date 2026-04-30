from pydantic import BaseModel


class TechnicalResponse(BaseModel):
    ticker: str
    as_of: str
    price: float | None
    trend: dict
    moving_averages: dict
    volume: dict
    momentum: dict
    levels: dict
    candles_tail: list[dict]