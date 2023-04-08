from enum import Enum
from fractions import Fraction
from operator import add, mul, sub, truediv
from typing import Callable, Final, TypeAlias, Literal, Sequence

number_T: TypeAlias = (int | Fraction)


class Operator(Enum):
    ADD: Final = add
    SUB: Final = sub
    MUL: Final = mul
    DIV: Final = truediv
    LEFT_BRACKET: Final = '('
    RIGHT_BRACKET: Final = ')'

    def __str__(self) -> str:
        return OPERATOR_CHARS[self]


ADD: Final[Operator] = Operator.ADD
SUB: Final[Operator] = Operator.SUB
MUL: Final[Operator] = Operator.MUL
DIV: Final[Operator] = Operator.DIV
LEFT_BRACKET: Final[Operator] = Operator.LEFT_BRACKET
RIGHT_BRACKET: Final[Operator] = Operator.RIGHT_BRACKET
# ASMD: TypeAlias = Literal[ADD, SUB, MUL, DIV]

OPERATOR_CHARS: dict[Operator, str] = {
    ADD: '+',
    SUB: '-',
    MUL: '×',
    DIV: '÷',
    LEFT_BRACKET: '(',
    RIGHT_BRACKET: ')'
}

CHAR_TO_OPERATOR: dict[str, Operator] = {
    '+': ADD,
    '-': SUB,
    '*': MUL,
    '/': DIV,
    '(': LEFT_BRACKET,
    ')': RIGHT_BRACKET
}

# PRIORITY: dict[Operator, int] = {
#     LEFT_BRACKET: 0,
#     MUL: 1,
#     DIV: 1,
#     ADD: 2,
#     SUB: 2,
#     RIGHT_BRACKET: 3
# }

replace_dict: dict[str, str] = {
    ' ': '',
    '＋': '+',
    '－': '-',
    '＊': '*',
    '×': '*',
    'x': '*',
    '／': '/',
    '÷': '/',
    '[': '(',
    ']': ')',
    '{': '(',
    '}': ')',
    '（': '(',
    '）': ')',
    '【': '(',
    '】': ')',
}


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
        if (self.__op in (MUL, DIV)) and (self.__expr0.__op in (ADD, SUB)):  # (x ± y) * z or (x ± y) / z
            str_expr0 = f'({str_expr0})'
        if (self.__op in (MUL, DIV)) and (self.__expr1.__op in (ADD, SUB)):  # x * (y ± z) or x / (y ± z)
            str_expr1 = f'({str_expr1})'
        if (self.__op == SUB) and (self.__expr1.__op in (ADD, SUB)):  # x - (y ± z)
            str_expr1 = f'({str_expr1})'
        if (self.__op == DIV) and (self.__expr1.__op in (MUL, DIV)):  # x / (y * z) or x / (y / z)
            str_expr1 = f'({str_expr1})'
        return f'{str_expr0} {str_op} {str_expr1}'

    @staticmethod
    def operator_fallbacks(operator: Callable) -> tuple[Callable, Callable]:
        def forward(a, b):
            if not isinstance(b, (int, Fraction, Expression)):
                return NotImplemented
            return operator(a, b)
        forward.__doc__ = operator.__doc__

        def reverse(b, a):
            if not isinstance(a, (int, Fraction, Expression)):
                return NotImplemented
            return operator(a, b)
        reverse.__doc__ = operator.__doc__

        return forward, reverse

    @staticmethod
    def __add(a: 'Expression', b: 'Expression') -> 'Expression':
        '''Expression(a, b, ADD)'''
        return Expression(a, b, ADD)

    @staticmethod
    def __sub(a: 'Expression', b: 'Expression') -> 'Expression':
        '''Expression(a, b, SUB)'''
        return Expression(a, b, SUB)

    @staticmethod
    def __mul(a: 'Expression', b: 'Expression') -> 'Expression':
        '''Expression(a, b, MUL)'''
        return Expression(a, b, MUL)

    @staticmethod
    def __div(a: 'Expression', b: 'Expression') -> 'Expression':
        '''Expression(a, b, DIV)'''
        return Expression(a, b, DIV)

    @staticmethod
    def __gt(a: 'Expression', b: 'Expression') -> bool:
        '''比较值的大小'''
        return a.value > b.value

    @staticmethod
    def __ge(a: 'Expression', b: 'Expression') -> bool:
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
        return (self.__expr0 == other.__expr0
                and self.__expr1 == other.__expr1
                and self.__op == other.__op)

    def __bool__(self) -> bool:
        return bool(self.value)


class Infix(list[Fraction | Operator]):
    def __init__(self, expr: str | Sequence) -> None:
        if isinstance(expr, str):
            for k, v in replace_dict.items():
                expr = expr.replace(k, v)
            pt: int = 0
            for i, char in enumerate(expr):
                if char in CHAR_TO_OPERATOR:
                    if pt < i:
                        self.append(Fraction(expr[pt:i]))
                    self.append(CHAR_TO_OPERATOR[char])
                    pt = i + 1
            if pt < len(expr):
                self.append(Fraction(expr[pt:]))
        else:
            ...

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}({super().__repr__()})'

    def __str__(self) -> str:
        # l: list[str] = []
        # for x in self:
        #     if isinstance(x, Operator):
        #         l.append(OPERATOR_CHARS)
        return ' '.join(str(x) for x in self)

    def to_suffix(self) -> 'Suffix':
        return Suffix(self)


class Suffix(list[Fraction | Operator]):
    '''有bug'''

    def __init__(self, expr: str | Infix) -> None:
        if isinstance(expr, str):
            expr = Infix(expr)
        self.data: list[Fraction | Operator] = []
        self.load_from_infix(expr)

    _should_push_to_stack_dict: dict[Operator, dict[Operator, bool]] = {
        ADD:           {ADD: False, SUB: False, MUL: False, DIV: False, LEFT_BRACKET: True},
        SUB:           {ADD: False, SUB: False, MUL: False, DIV: False, LEFT_BRACKET: True},
        MUL:           {ADD: True,  SUB: True,  MUL: False, DIV: False, LEFT_BRACKET: True},
        DIV:           {ADD: True,  SUB: True,  MUL: False, DIV: False, LEFT_BRACKET: True},
        LEFT_BRACKET:  {ADD: True,  SUB: True,  MUL: True,  DIV: True,  LEFT_BRACKET: True},
        RIGHT_BRACKET: {ADD: False, SUB: False, MUL: False, DIV: False, LEFT_BRACKET: False},
    }

    @staticmethod
    def should_push_to_stack(next_operator: Operator, stack_top_operator: Operator) -> bool:
        '''`True`代表应该进栈'''
        return Suffix._should_push_to_stack_dict[next_operator][stack_top_operator]

    def load_from_infix(self, infix: Infix) -> None:
        stack: list[Operator] = []
        for x in infix:
            if not isinstance(x, Operator):  # 如果x是数
                self.append(x)
            else:
                while stack and not Suffix.should_push_to_stack(x, stack[-1]):
                    top_item: Operator = stack.pop()
                    if top_item != LEFT_BRACKET:
                        self.append(top_item)
                if x != RIGHT_BRACKET:
                    stack.append(x)
        if LEFT_BRACKET in stack:
            raise ValueError('Brackets not paired.')
        self.extend(reversed(stack))

    def calculate(self) -> Fraction:
        # result = 0
        stack: list[Fraction] = []
        for x in self:
            if not isinstance(x, Operator):
                stack.append(x)
            else:
                a: Fraction = stack.pop()
                b: Fraction = stack.pop()
                stack.append(x.value(b, a))
        return stack.pop()

    def __str__(self) -> str:
        return ' '.join(str(x) for x in self)


if __name__ == '__main__':
    print(Suffix('11+((1+2)*(345/2345))'))
