from dataclasses import dataclass


@dataclass
class Variable:
    uid: str
    parameter_uid: str
    nominal_value: float
    minimal_value: float
    maximal_value: float

