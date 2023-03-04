from enum import Enum
from fractions import Fraction
from operator import add, mul, sub, truediv
from typing import Callable, Final, TypeAlias

number_T: TypeAlias = (int | Fraction)


class Operator(Enum):
    ADD: Final = add
    SUB: Final = sub
    MUL: Final = mul
    DIV: Final = truediv


ADD: Final[Operator] = Operator.ADD
SUB: Final[Operator] = Operator.SUB
MUL: Final[Operator] = Operator.MUL
DIV: Final[Operator] = Operator.DIV

OPERATOR_CHARS: dict[Operator, str] = {
    ADD: '+',
    SUB: '-',
    MUL: '×',
    DIV: '÷',
}


# class _Fraction(Fraction_):
#     def __new__(cls, /, *args, **kwargs) -> Fraction_:
#         if len(args) == 1:
#             expr = args[0]
#             if isinstance(expr, Expression):
#                 return expr.value
#         return super().__new__(cls, *args, **kwargs)


# Fraction = _Fraction


class Expression:
    def __init__(self,
                 expr0: 'Expression | number_T',
                 expr1: 'Expression | number_T | None' = None,
                 op: Operator | None = None
                 ) -> None:
        self.__expr0: Expression | Fraction
        self.__expr1: Expression | None
        self.__op: Operator | None
        self.value: Fraction

        if (expr1 is None) or (op is None):
            if (expr1 is not None) or (op is not None):
                raise TypeError
            if isinstance(expr0, Expression):
                self.__expr0 = expr0.__expr0
                self.__expr1 = expr0.__expr1
                self.__op = expr0.__op
                self.value = expr0.value
            else:
                self.__expr0 = Fraction(expr0)
                self.__expr1 = self.__op = None
                self.value = Fraction(expr0)
        else:
            self.__expr0 = Expression(expr0)
            self.__expr1 = Expression(expr1)
            self.__op = op
            self.value = op.value(self.__expr0.value, self.__expr1.value)

    # @property
    # def value(self) -> Fraction:
    #     if not isinstance(self.expr0, Expression):
    #         return self.expr0

    #     assert isinstance(self.expr1, Expression) and isinstance(self.op, Operator)
    #     return self.op.value(self.expr0.value, self.expr1.value)

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}({repr(self.__expr0)}, {repr(self.__expr1)}, {self.__op})'

    def __str__(self) -> str:
        if not isinstance(self.__expr0, Expression):
            return str(self.__expr0)

        assert isinstance(self.__expr1, Expression) and isinstance(self.__op, Operator)
        str_expr0: str = str(self.__expr0)
        str_expr1: str = str(self.__expr1)
        str_op: str = OPERATOR_CHARS[self.__op]
        if (self.__op in (MUL, DIV)) and (self.__expr0.__op in [ADD, SUB]):  # (x ± y) */ z
            str_expr0 = f'({str_expr0})'
        if (self.__op in (MUL, DIV)) and (self.__expr1.__op in [ADD, SUB]):  # x * (y ± z) or x / (y ± z)
            str_expr1 = f'({str_expr1})'
        if (self.__op == SUB) and (self.__expr1.__op in (ADD, SUB)):  # x - (y ± z)
            str_expr1 = f'({str_expr1})'
        if (self.__op == DIV) and (self.__expr1.__op in (MUL, DIV)):  # x / (y * z) or x / (y / z)
            str_expr1 = f'({str_expr1})'
        return f'{str_expr0} {str_op} {str_expr1}'

    @staticmethod
    def operator_fallbacks(operator: Callable) -> tuple[Callable, Callable]:
        def forward(a, b):
            if isinstance(b, (int, Fraction, Expression)):
                return operator(a, b)
            else:
                return NotImplemented
        forward.__doc__ = operator.__doc__

        def reverse(b, a):
            if isinstance(a, (int, Fraction, Expression)):
                return operator(a, b)
            else:
                return NotImplemented
        reverse.__doc__ = operator.__doc__

        return forward, reverse

    @staticmethod
    def __add(a, b) -> 'Expression':
        '''Expression(a, b, ADD)'''
        return Expression(a, b, ADD)

    @staticmethod
    def __sub(a, b) -> 'Expression':
        '''Expression(a, b, SUB)'''
        return Expression(a, b, SUB)

    @staticmethod
    def __mul(a, b) -> 'Expression':
        '''Expression(a, b, MUL)'''
        return Expression(a, b, MUL)

    @staticmethod
    def __div(a, b) -> 'Expression':
        '''Expression(a, b, DIV)'''
        return Expression(a, b, DIV)

    @staticmethod
    def __gt(a, b) -> bool:
        '''比较值的大小'''
        return a.value > b.value

    @staticmethod
    def __ge(a, b) -> bool:
        '''比较值的大小'''
        return a.value >= b.value

    __add__, __radd__ = operator_fallbacks(__add)
    __sub__, __rsub__ = operator_fallbacks(__sub)
    __mul__, __rmul__ = operator_fallbacks(__mul)
    __truediv__, __rtruediv__ = operator_fallbacks(__div)
    __gt__, __lt__ = operator_fallbacks(__gt)
    __ge__, __le__ = operator_fallbacks(__ge)

    # def __add__(self, other) -> 'Expression':
    #     return Expression(self, other, ADD)

    # def __radd__(self, other) -> 'Expression':
    #     return Expression(other, self, ADD)

    # def __sub__(self, other) -> 'Expression':
    #     return Expression(self, other, SUB)

    # def __rsub__(self, other) -> 'Expression':
    #     return Expression(other, self, SUB)

    # def __mul__(self, other) -> 'Expression':
    #     return Expression(self, other, MUL)

    # def __rmul__(self, other) -> 'Expression':
    #     return Expression(other, self, MUL)

    # def __truediv__(self, other) -> 'Expression':
    #     return Expression(self, other, DIV)

    # def __rtruediv__(self, other) -> 'Expression':
    #     return Expression(other, self, DIV)

    def __eq__(self, other) -> bool:
        '''比较两个表达式是否完全相同。

        如果想比较两个表达式的值是否相同，请使用`self.value == other.value`'''
        if not isinstance(other, Expression):
            return False
        if not isinstance(self.__expr0, Expression):
            return (not isinstance(other.__expr0, Expression)) and (self.__expr0 == other.__expr0)
        return (self.__expr0 == other.__expr0
                and self.__expr1 == other.__expr1
                and self.__op == other.__op)

    def __bool__(self) -> bool:
        return bool(self.value)


if __name__ == '__main__':
    pass
